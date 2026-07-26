import re

from app.graph import GraphRepository
from app.llm import KnowledgeLLM
from app.models import (
    ClaimView,
    EntityCandidate,
    EntityResult,
    EntityView,
    EvidenceView,
    NeighborhoodResult,
    PushMemoryResult,
    SearchHit,
    SearchResult,
)
from app.utils import (
    new_id,
    normalize_predicate,
    normalize_text,
    stable_id,
)


KNOWLEDGE_ID_PATTERN = re.compile(r"^kg_[A-Za-z0-9_-]{8,128}$")


def validate_knowledge_id(knowledge_id: str) -> str:
    if not KNOWLEDGE_ID_PATTERN.fullmatch(knowledge_id):
        raise ValueError(
            "Invalid knowledge ID. Expected kg_ followed by 8-128 safe characters."
        )
    return knowledge_id


class KnowledgeService:
    def __init__(self, graph: GraphRepository, llm: KnowledgeLLM) -> None:
        self._graph = graph
        self._llm = llm

    async def create_knowledge_base(self) -> str:
        knowledge_id = new_id("kg")
        await self._graph.ensure_knowledge_base(knowledge_id)
        return knowledge_id

    async def push_memory(
        self,
        knowledge_id: str,
        text: str,
        source: str,
        idempotency_key: str | None = None,
    ) -> PushMemoryResult:
        validate_knowledge_id(knowledge_id)
        text = text.strip()
        source = source.strip() or "unspecified"
        if not text:
            raise ValueError("Memory text cannot be empty")

        await self._graph.ensure_knowledge_base(knowledge_id)
        memory_key = idempotency_key or stable_id("content", source, text)
        memory_id = stable_id("mem", knowledge_id, memory_key)
        text_embedding = await self._llm.embed(text)
        await self._graph.create_evidence(
            knowledge_id=knowledge_id,
            evidence_id=memory_id,
            text=text,
            source=source,
            embedding=text_embedding,
        )

        extraction = await self._llm.extract(text)
        resolved: dict[str, EntityView] = {}
        created_entities: dict[str, EntityView] = {}
        reused_entities: dict[str, EntityView] = {}
        unresolved_entities: list[str] = []

        for mention in extraction.entities:
            normalized = normalize_text(mention.name)
            if not normalized:
                unresolved_entities.append(mention.name)
                continue
            entity_description = (
                f"{mention.name}\nKind: {mention.kind}\n{mention.summary}"
            )
            entity_embedding = await self._llm.embed(entity_description)
            candidates = await self._graph.find_candidates(
                knowledge_id,
                mention.name,
                normalized,
                entity_embedding,
            )

            entity: EntityView | None = None
            if candidates:
                decision = await self._llm.resolve(mention, candidates, text)
                if decision.action == "LINK":
                    if not decision.candidate_id or decision.confidence < 0.85:
                        unresolved_entities.append(mention.name)
                        continue
                    selected = next(
                        candidate
                        for candidate in candidates
                        if candidate.id == decision.candidate_id
                    )
                    entity = self._candidate_to_view(selected)
                    alias_pairs = self._alias_pairs(
                        mention.name,
                        mention.aliases,
                    )
                    await self._graph.add_aliases(
                        knowledge_id,
                        entity.id,
                        alias_pairs,
                    )
                    known_aliases = {normalize_text(alias) for alias in entity.aliases}
                    entity.aliases.extend(
                        display
                        for display, alias_norm in alias_pairs
                        if alias_norm not in known_aliases
                    )
                    reused_entities[entity.id] = entity
                elif decision.action == "UNRESOLVED":
                    unresolved_entities.append(mention.name)
                    continue

            if entity is None:
                entity_id = new_id("ent")
                alias_pairs = self._alias_pairs(mention.name, mention.aliases)
                entity = await self._graph.create_entity(
                    knowledge_id=knowledge_id,
                    entity_id=entity_id,
                    name=mention.name,
                    normalized=normalized,
                    kind=mention.kind,
                    summary=mention.summary,
                    aliases=alias_pairs,
                    embedding=entity_embedding,
                )
                created_entities[entity.id] = entity
            resolved[mention.temp_id] = entity

        created_claim_ids: list[str] = []
        reused_claim_ids: list[str] = []
        for claim in extraction.claims:
            subject = resolved.get(claim.subject_temp_id)
            object_entity = (
                resolved.get(claim.object_temp_id)
                if claim.object_temp_id is not None
                else None
            )
            if subject is None:
                continue
            if claim.object_temp_id is not None and object_entity is None:
                continue
            if claim.evidence_quote not in text:
                continue

            predicate = normalize_predicate(claim.predicate)
            object_key = (
                object_entity.id
                if object_entity is not None
                else f"literal:{normalize_text(claim.object_literal or '')}"
            )
            claim_id = stable_id(
                "clm",
                knowledge_id,
                subject.id,
                predicate,
                object_key,
                claim.polarity,
                claim.valid_from or "",
                claim.valid_to or "",
            )
            created = await self._graph.upsert_claim(
                knowledge_id=knowledge_id,
                claim_id=claim_id,
                subject_id=subject.id,
                predicate=predicate,
                object_entity_id=object_entity.id if object_entity else None,
                object_literal=claim.object_literal,
                polarity=claim.polarity,
                confidence=claim.confidence,
                valid_from=claim.valid_from,
                valid_to=claim.valid_to,
                evidence_id=memory_id,
                supersedes_existing=claim.supersedes_existing,
            )
            target = created_claim_ids if created else reused_claim_ids
            target.append(claim_id)

        return PushMemoryResult(
            knowledge_id=knowledge_id,
            memory_id=memory_id,
            created_entities=list(created_entities.values()),
            reused_entities=list(reused_entities.values()),
            created_claim_ids=created_claim_ids,
            reused_claim_ids=reused_claim_ids,
            unresolved_entities=unresolved_entities,
        )

    async def search(
        self,
        knowledge_id: str,
        query: str,
        limit: int = 5,
    ) -> SearchResult:
        validate_knowledge_id(knowledge_id)
        query = query.strip()
        if not query:
            raise ValueError("Search query cannot be empty")
        limit = max(1, min(limit, 20))
        embedding = await self._llm.embed(query)
        seeds = await self._graph.search_seed_entity_ids(
            knowledge_id,
            query,
            embedding,
            limit,
        )
        if not seeds:
            return SearchResult(query=query, hits=[], insufficient_evidence=True)

        seed_ids = [entity_id for entity_id, _ in seeds]
        expanded_ids, _ = await self._graph.expand_entity_ids(
            knowledge_id,
            seed_ids,
            depth=1,
            limit=50,
        )
        entity_rows = await self._graph.fetch_entities(knowledge_id, expanded_ids)
        entity_map = {
            row["id"]: self._row_to_entity(row)
            for row in entity_rows
        }
        claim_rows = await self._graph.fetch_claims(knowledge_id, expanded_ids)
        claims = [self._row_to_claim(row) for row in claim_rows]

        hits: list[SearchHit] = []
        for entity_id, score in seeds:
            entity = entity_map.get(entity_id)
            if entity is None:
                continue
            related_claims = [
                claim
                for claim in claims
                if claim.subject.id == entity_id
                or (
                    isinstance(claim.object, EntityView)
                    and claim.object.id == entity_id
                )
            ]
            hits.append(
                SearchHit(entity=entity, score=score, claims=related_claims)
            )
        return SearchResult(
            query=query,
            hits=hits,
            insufficient_evidence=not any(hit.claims for hit in hits),
        )

    async def get_entity(
        self,
        knowledge_id: str,
        entity_id: str,
    ) -> EntityResult:
        validate_knowledge_id(knowledge_id)
        rows = await self._graph.fetch_entities(knowledge_id, [entity_id])
        if not rows:
            raise ValueError("Entity not found in this knowledge base")
        claim_rows = await self._graph.fetch_claims(knowledge_id, [entity_id])
        return EntityResult(
            entity=self._row_to_entity(rows[0]),
            claims=[self._row_to_claim(row) for row in claim_rows],
        )

    async def get_neighborhood(
        self,
        knowledge_id: str,
        entity_id: str,
        depth: int = 1,
        limit: int = 50,
    ) -> NeighborhoodResult:
        validate_knowledge_id(knowledge_id)
        depth = max(1, min(depth, 2))
        limit = max(1, min(limit, 100))
        ids, truncated = await self._graph.expand_entity_ids(
            knowledge_id,
            [entity_id],
            depth,
            limit,
        )
        if entity_id not in ids:
            raise ValueError("Entity not found in this knowledge base")
        rows = await self._graph.fetch_entities(knowledge_id, ids)
        entities = [self._row_to_entity(row) for row in rows]
        center = next(entity for entity in entities if entity.id == entity_id)
        claims = [
            self._row_to_claim(row)
            for row in await self._graph.fetch_claims(
                knowledge_id,
                ids,
                limit=limit * 2,
            )
        ]
        return NeighborhoodResult(
            center=center,
            entities=entities,
            claims=claims,
            truncated=truncated,
        )

    @staticmethod
    def _alias_pairs(name: str, aliases: list[str]) -> list[tuple[str, str]]:
        unique: dict[str, str] = {}
        for display in [name, *aliases]:
            normalized = normalize_text(display)
            if normalized:
                unique.setdefault(normalized, display)
        return [(display, normalized) for normalized, display in unique.items()]

    @staticmethod
    def _candidate_to_view(candidate: EntityCandidate) -> EntityView:
        return EntityView(
            id=candidate.id,
            name=candidate.name,
            kind=candidate.kind,
            summary=candidate.summary,
            aliases=candidate.aliases,
        )

    @staticmethod
    def _row_to_entity(row: dict) -> EntityView:
        return EntityView(
            id=row["id"],
            name=row["name"],
            kind=row["kind"],
            summary=row.get("summary") or "",
            aliases=[alias for alias in row.get("aliases", []) if alias],
        )

    @classmethod
    def _row_to_claim(cls, row: dict) -> ClaimView:
        claim = row["claim"]
        subject = cls._row_to_entity(row["subject"])
        object_value: EntityView | str
        if row.get("object"):
            object_value = cls._row_to_entity(row["object"])
        else:
            object_value = claim.get("object_literal") or ""
        evidence = [
            EvidenceView(**item)
            for item in row.get("evidence", [])
            if item and item.get("id")
        ]
        return ClaimView(
            id=claim["id"],
            subject=subject,
            predicate=claim["predicate"],
            object=object_value,
            polarity=claim["polarity"],
            status=claim["status"],
            confidence=claim["confidence"],
            valid_from=claim.get("valid_from"),
            valid_to=claim.get("valid_to"),
            evidence=evidence,
        )
