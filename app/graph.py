from collections import defaultdict
from typing import Any

from neo4j import AsyncDriver, AsyncGraphDatabase, RoutingControl

from app.config import Settings
from app.models import EntityCandidate, EntityView
from app.utils import safe_fulltext_query, stable_id


class GraphRepository:
    def __init__(self, settings: Settings) -> None:
        self._database = settings.neo4j_database
        self._dimensions = settings.embedding_dimensions
        self._driver: AsyncDriver = AsyncGraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_username, settings.neo4j_password),
        )

    async def close(self) -> None:
        await self._driver.close()

    async def initialize(self) -> None:
        await self._driver.verify_connectivity()
        statements = [
            "CREATE CONSTRAINT knowledge_id IF NOT EXISTS "
            "FOR (k:KnowledgeBase) REQUIRE k.id IS UNIQUE",
            "CREATE CONSTRAINT entity_id IF NOT EXISTS "
            "FOR (e:Entity) REQUIRE e.id IS UNIQUE",
            "CREATE CONSTRAINT alias_id IF NOT EXISTS "
            "FOR (a:Alias) REQUIRE a.id IS UNIQUE",
            "CREATE CONSTRAINT evidence_id IF NOT EXISTS "
            "FOR (e:Evidence) REQUIRE e.id IS UNIQUE",
            "CREATE CONSTRAINT claim_id IF NOT EXISTS "
            "FOR (c:Claim) REQUIRE c.id IS UNIQUE",
            "CREATE INDEX entity_scope_name IF NOT EXISTS "
            "FOR (e:Entity) ON (e.knowledge_id, e.canonical_norm)",
            "CREATE INDEX alias_scope_name IF NOT EXISTS "
            "FOR (a:Alias) ON (a.knowledge_id, a.normalized)",
            "CREATE INDEX claim_scope_predicate IF NOT EXISTS "
            "FOR (c:Claim) ON (c.knowledge_id, c.predicate, c.status)",
            "CREATE FULLTEXT INDEX alias_search IF NOT EXISTS "
            "FOR (a:Alias) ON EACH [a.display, a.normalized]",
            "CREATE FULLTEXT INDEX evidence_search IF NOT EXISTS "
            "FOR (e:Evidence) ON EACH [e.text, e.source]",
            f"CREATE VECTOR INDEX entity_embedding IF NOT EXISTS "
            f"FOR (e:Entity) ON e.embedding OPTIONS {{indexConfig: {{"
            f"`vector.dimensions`: {self._dimensions}, "
            f"`vector.similarity_function`: 'cosine'}}}}",
            f"CREATE VECTOR INDEX evidence_embedding IF NOT EXISTS "
            f"FOR (e:Evidence) ON e.embedding OPTIONS {{indexConfig: {{"
            f"`vector.dimensions`: {self._dimensions}, "
            f"`vector.similarity_function`: 'cosine'}}}}",
        ]
        for statement in statements:
            await self._execute(statement)
        await self._execute("CALL db.awaitIndexes(300)")

    async def _execute(
        self,
        query: str,
        parameters: dict[str, Any] | None = None,
        *,
        read: bool = False,
    ) -> list[dict[str, Any]]:
        records, _, _ = await self._driver.execute_query(
            query,
            parameters_=parameters or {},
            database_=self._database,
            routing_=RoutingControl.READ if read else RoutingControl.WRITE,
        )
        return [record.data() for record in records]

    async def ensure_knowledge_base(self, knowledge_id: str) -> None:
        await self._execute(
            """
            MERGE (k:KnowledgeBase {id: $knowledge_id})
            ON CREATE SET k.created_at = datetime()
            """,
            {"knowledge_id": knowledge_id},
        )

    async def find_candidates(
        self,
        knowledge_id: str,
        name: str,
        normalized: str,
        embedding: list[float],
        limit: int = 8,
    ) -> list[EntityCandidate]:
        scores: defaultdict[str, float] = defaultdict(float)

        exact = await self._execute(
            """
            MATCH (a:Alias {knowledge_id: $knowledge_id, normalized: $normalized})
                  -[:ALIAS_OF]->(e:Entity {knowledge_id: $knowledge_id})
            RETURN e.id AS id
            UNION
            MATCH (e:Entity {
                knowledge_id: $knowledge_id,
                canonical_norm: $normalized
            })
            RETURN e.id AS id
            """,
            {"knowledge_id": knowledge_id, "normalized": normalized},
            read=True,
        )
        for row in exact:
            scores[row["id"]] += 10

        fulltext_query = safe_fulltext_query(name)
        if fulltext_query:
            lexical = await self._execute(
                """
                CALL db.index.fulltext.queryNodes(
                    'alias_search', $query, {limit: $limit}
                )
                YIELD node, score
                WHERE node.knowledge_id = $knowledge_id
                MATCH (node)-[:ALIAS_OF]->(e:Entity {knowledge_id: $knowledge_id})
                RETURN e.id AS id, max(score) AS score
                ORDER BY score DESC
                """,
                {
                    "knowledge_id": knowledge_id,
                    "query": fulltext_query,
                    "limit": limit,
                },
                read=True,
            )
            for rank, row in enumerate(lexical, 1):
                scores[row["id"]] += 1 / (60 + rank)

        semantic = await self._execute(
            """
            CALL db.index.vector.queryNodes('entity_embedding', $limit, $embedding)
            YIELD node, score
            WHERE node.knowledge_id = $knowledge_id
            RETURN node.id AS id, score
            ORDER BY score DESC
            """,
            {
                "knowledge_id": knowledge_id,
                "limit": limit,
                "embedding": embedding,
            },
            read=True,
        )
        for rank, row in enumerate(semantic, 1):
            scores[row["id"]] += 1 / (60 + rank)

        ids = sorted(scores, key=scores.get, reverse=True)[:limit]
        return await self.get_candidate_details(knowledge_id, ids)

    async def get_candidate_details(
        self,
        knowledge_id: str,
        entity_ids: list[str],
    ) -> list[EntityCandidate]:
        if not entity_ids:
            return []
        rows = await self._execute(
            """
            UNWIND $entity_ids AS entity_id
            MATCH (e:Entity {knowledge_id: $knowledge_id, id: entity_id})
            OPTIONAL MATCH (a:Alias {knowledge_id: $knowledge_id})-[:ALIAS_OF]->(e)
            RETURN e.id AS id, e.canonical_name AS name, e.kind AS kind,
                   e.summary AS summary, collect(DISTINCT a.display) AS aliases
            """,
            {"knowledge_id": knowledge_id, "entity_ids": entity_ids},
            read=True,
        )
        by_id = {
            row["id"]: EntityCandidate(
                id=row["id"],
                name=row["name"],
                kind=row["kind"],
                summary=row.get("summary") or "",
                aliases=[alias for alias in row["aliases"] if alias],
            )
            for row in rows
        }
        return [by_id[entity_id] for entity_id in entity_ids if entity_id in by_id]

    async def create_entity(
        self,
        knowledge_id: str,
        entity_id: str,
        name: str,
        normalized: str,
        kind: str,
        summary: str,
        aliases: list[tuple[str, str]],
        embedding: list[float],
    ) -> EntityView:
        await self._execute(
            """
            MATCH (k:KnowledgeBase {id: $knowledge_id})
            CREATE (e:Entity {
                id: $entity_id,
                knowledge_id: $knowledge_id,
                canonical_name: $name,
                canonical_norm: $normalized,
                kind: $kind,
                summary: $summary,
                embedding: $embedding,
                created_at: datetime()
            })
            MERGE (k)-[:CONTAINS]->(e)
            """,
            {
                "knowledge_id": knowledge_id,
                "entity_id": entity_id,
                "name": name,
                "normalized": normalized,
                "kind": kind,
                "summary": summary,
                "embedding": embedding,
            },
        )
        for display, alias_norm in aliases:
            alias_id = stable_id("alias", knowledge_id, entity_id, alias_norm)
            await self._execute(
                """
                MATCH (e:Entity {knowledge_id: $knowledge_id, id: $entity_id})
                MERGE (a:Alias {id: $alias_id})
                ON CREATE SET a.knowledge_id = $knowledge_id,
                              a.display = $display,
                              a.normalized = $normalized,
                              a.created_at = datetime()
                MERGE (a)-[:ALIAS_OF]->(e)
                """,
                {
                    "knowledge_id": knowledge_id,
                    "entity_id": entity_id,
                    "alias_id": alias_id,
                    "display": display,
                    "normalized": alias_norm,
                },
            )
        return EntityView(
            id=entity_id,
            name=name,
            kind=kind,
            summary=summary,
            aliases=[display for display, _ in aliases],
        )

    async def add_aliases(
        self,
        knowledge_id: str,
        entity_id: str,
        aliases: list[tuple[str, str]],
    ) -> None:
        for display, alias_norm in aliases:
            alias_id = stable_id("alias", knowledge_id, entity_id, alias_norm)
            await self._execute(
                """
                MATCH (e:Entity {knowledge_id: $knowledge_id, id: $entity_id})
                MERGE (a:Alias {id: $alias_id})
                ON CREATE SET a.knowledge_id = $knowledge_id,
                              a.display = $display,
                              a.normalized = $normalized,
                              a.created_at = datetime()
                MERGE (a)-[:ALIAS_OF]->(e)
                """,
                {
                    "knowledge_id": knowledge_id,
                    "entity_id": entity_id,
                    "alias_id": alias_id,
                    "display": display,
                    "normalized": alias_norm,
                },
            )

    async def create_evidence(
        self,
        knowledge_id: str,
        evidence_id: str,
        text: str,
        source: str,
        embedding: list[float],
    ) -> bool:
        rows = await self._execute(
            """
            MATCH (k:KnowledgeBase {id: $knowledge_id})
            OPTIONAL MATCH (existing:Evidence {
                knowledge_id: $knowledge_id,
                id: $evidence_id
            })
            WITH k, existing, existing IS NULL AS created
            MERGE (e:Evidence {id: $evidence_id})
            ON CREATE SET e.knowledge_id = $knowledge_id,
                          e.text = $text,
                          e.source = $source,
                          e.embedding = $embedding,
                          e.ingested_at = datetime()
            MERGE (k)-[:CONTAINS]->(e)
            RETURN created
            """,
            {
                "knowledge_id": knowledge_id,
                "evidence_id": evidence_id,
                "text": text,
                "source": source,
                "embedding": embedding,
            },
        )
        return bool(rows[0]["created"])

    async def upsert_claim(
        self,
        knowledge_id: str,
        claim_id: str,
        subject_id: str,
        predicate: str,
        object_entity_id: str | None,
        object_literal: str | None,
        polarity: str,
        confidence: float,
        valid_from: str | None,
        valid_to: str | None,
        evidence_id: str,
        supersedes_existing: bool,
    ) -> bool:
        rows = await self._execute(
            """
            MATCH (k:KnowledgeBase {id: $knowledge_id})
            MATCH (subject:Entity {knowledge_id: $knowledge_id, id: $subject_id})
            MATCH (evidence:Evidence {
                knowledge_id: $knowledge_id,
                id: $evidence_id
            })
            OPTIONAL MATCH (existing:Claim {
                knowledge_id: $knowledge_id,
                id: $claim_id
            })
            WITH k, subject, evidence, existing, existing IS NULL AS created
            MERGE (claim:Claim {id: $claim_id})
            ON CREATE SET claim.knowledge_id = $knowledge_id,
                          claim.predicate = $predicate,
                          claim.object_literal = $object_literal,
                          claim.polarity = $polarity,
                          claim.confidence = $confidence,
                          claim.status = 'active',
                          claim.valid_from = $valid_from,
                          claim.valid_to = $valid_to,
                          claim.created_at = datetime()
            MERGE (k)-[:CONTAINS]->(claim)
            MERGE (claim)-[:SUBJECT]->(subject)
            MERGE (claim)-[:SUPPORTED_BY]->(evidence)
            WITH claim, created
            OPTIONAL MATCH (object:Entity {
                knowledge_id: $knowledge_id,
                id: $object_entity_id
            })
            FOREACH (_ IN CASE WHEN object IS NULL THEN [] ELSE [1] END |
                MERGE (claim)-[:OBJECT]->(object)
            )
            RETURN created
            """,
            {
                "knowledge_id": knowledge_id,
                "claim_id": claim_id,
                "subject_id": subject_id,
                "predicate": predicate,
                "object_entity_id": object_entity_id,
                "object_literal": object_literal,
                "polarity": polarity,
                "confidence": confidence,
                "valid_from": valid_from,
                "valid_to": valid_to,
                "evidence_id": evidence_id,
            },
        )
        created = bool(rows[0]["created"])
        if created and supersedes_existing:
            await self._execute(
                """
                MATCH (new:Claim {
                    knowledge_id: $knowledge_id,
                    id: $claim_id
                })-[:SUBJECT]->(subject:Entity)
                MATCH (old:Claim {
                    knowledge_id: $knowledge_id,
                    predicate: $predicate,
                    status: 'active'
                })-[:SUBJECT]->(subject)
                WHERE old.id <> new.id
                OPTIONAL MATCH (new)-[:OBJECT]->(new_object:Entity)
                OPTIONAL MATCH (old)-[:OBJECT]->(old_object:Entity)
                WITH new, old, new_object, old_object
                WHERE coalesce(new_object.id, new.object_literal, '') <>
                      coalesce(old_object.id, old.object_literal, '')
                SET old.status = 'superseded',
                    old.recorded_to = datetime()
                MERGE (new)-[:SUPERSEDES]->(old)
                """,
                {
                    "knowledge_id": knowledge_id,
                    "claim_id": claim_id,
                    "predicate": predicate,
                },
            )
        return created

    async def search_seed_entity_ids(
        self,
        knowledge_id: str,
        query: str,
        embedding: list[float],
        limit: int,
    ) -> list[tuple[str, float]]:
        rankings: list[list[str]] = []
        fulltext_query = safe_fulltext_query(query)
        if fulltext_query:
            lexical = await self._execute(
                """
                CALL db.index.fulltext.queryNodes(
                    'alias_search', $query, {limit: $candidate_limit}
                )
                YIELD node, score
                WHERE node.knowledge_id = $knowledge_id
                MATCH (node)-[:ALIAS_OF]->(entity:Entity)
                RETURN entity.id AS id, max(score) AS score
                ORDER BY score DESC
                """,
                {
                    "knowledge_id": knowledge_id,
                    "query": fulltext_query,
                    "candidate_limit": limit * 4,
                },
                read=True,
            )
            rankings.append([row["id"] for row in lexical])

        vectors = await self._execute(
            """
            CALL db.index.vector.queryNodes(
                'entity_embedding', $candidate_limit, $embedding
            )
            YIELD node, score
            WHERE node.knowledge_id = $knowledge_id
            RETURN node.id AS id, score
            ORDER BY score DESC
            """,
            {
                "knowledge_id": knowledge_id,
                "candidate_limit": limit * 4,
                "embedding": embedding,
            },
            read=True,
        )
        rankings.append([row["id"] for row in vectors])

        evidence_rows = await self._execute(
            """
            CALL db.index.vector.queryNodes(
                'evidence_embedding', $candidate_limit, $embedding
            )
            YIELD node, score
            WHERE node.knowledge_id = $knowledge_id
            MATCH (node)<-[:SUPPORTED_BY]-(claim:Claim)-[:SUBJECT|OBJECT]->(entity)
            RETURN entity.id AS id, max(score) AS score
            ORDER BY score DESC
            """,
            {
                "knowledge_id": knowledge_id,
                "candidate_limit": limit * 4,
                "embedding": embedding,
            },
            read=True,
        )
        rankings.append([row["id"] for row in evidence_rows])

        fused: defaultdict[str, float] = defaultdict(float)
        for ranking in rankings:
            for rank, entity_id in enumerate(ranking, 1):
                fused[entity_id] += 1 / (60 + rank)
        return sorted(fused.items(), key=lambda item: item[1], reverse=True)[:limit]

    async def expand_entity_ids(
        self,
        knowledge_id: str,
        seed_ids: list[str],
        depth: int,
        limit: int,
    ) -> tuple[list[str], bool]:
        max_edges = depth * 2
        rows = await self._execute(
            f"""
            MATCH (seed:Entity {{knowledge_id: $knowledge_id}})
            WHERE seed.id IN $seed_ids
            OPTIONAL MATCH path=(seed)-[:SUBJECT|OBJECT*1..{max_edges}]-(other:Entity {{
                knowledge_id: $knowledge_id
            }})
            WITH collect(DISTINCT seed.id) + collect(DISTINCT other.id) AS ids
            UNWIND ids AS id
            WITH DISTINCT id
            WHERE id IS NOT NULL
            RETURN id
            LIMIT $fetch_limit
            """,
            {
                "knowledge_id": knowledge_id,
                "seed_ids": seed_ids,
                "fetch_limit": limit + 1,
            },
            read=True,
        )
        ids = [row["id"] for row in rows]
        return ids[:limit], len(ids) > limit

    async def fetch_entities(
        self,
        knowledge_id: str,
        entity_ids: list[str],
    ) -> list[dict[str, Any]]:
        if not entity_ids:
            return []
        return await self._execute(
            """
            MATCH (entity:Entity {knowledge_id: $knowledge_id})
            WHERE entity.id IN $entity_ids
            OPTIONAL MATCH (alias:Alias)-[:ALIAS_OF]->(entity)
            RETURN entity.id AS id,
                   entity.canonical_name AS name,
                   entity.kind AS kind,
                   entity.summary AS summary,
                   collect(DISTINCT alias.display) AS aliases
            """,
            {"knowledge_id": knowledge_id, "entity_ids": entity_ids},
            read=True,
        )

    async def fetch_claims(
        self,
        knowledge_id: str,
        entity_ids: list[str],
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        if not entity_ids:
            return []
        return await self._execute(
            """
            MATCH (claim:Claim {knowledge_id: $knowledge_id})-[:SUBJECT]->(subject)
            OPTIONAL MATCH (claim)-[:OBJECT]->(object)
            WHERE subject.id IN $entity_ids OR object.id IN $entity_ids
            WITH claim, subject, object
            OPTIONAL MATCH (subject_alias:Alias)-[:ALIAS_OF]->(subject)
            WITH claim, subject, object,
                 collect(DISTINCT subject_alias.display) AS subject_aliases
            OPTIONAL MATCH (object_alias:Alias)-[:ALIAS_OF]->(object)
            WITH claim, subject, object, subject_aliases,
                 collect(DISTINCT object_alias.display) AS object_aliases
            OPTIONAL MATCH (claim)-[:SUPPORTED_BY]->(evidence:Evidence)
            WITH claim, subject, object, subject_aliases, object_aliases,
                 collect(DISTINCT evidence {
                     .id, .source, .text,
                     ingested_at: toString(evidence.ingested_at)
                 }) AS evidence_items
            RETURN claim {
                       .id, .predicate, .object_literal, .polarity, .status,
                       .confidence, .valid_from, .valid_to
                   } AS claim,
                   subject {
                       .id,
                       name: subject.canonical_name,
                       .kind,
                       .summary,
                       aliases: subject_aliases
                   } AS subject,
                   CASE WHEN object IS NULL THEN NULL ELSE object {
                       .id,
                       name: object.canonical_name,
                       .kind,
                       .summary,
                       aliases: object_aliases
                   } END AS object,
                   evidence_items AS evidence
            ORDER BY claim.status, claim.id
            LIMIT $limit
            """,
            {
                "knowledge_id": knowledge_id,
                "entity_ids": entity_ids,
                "limit": limit,
            },
            read=True,
        )
