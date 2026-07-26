# Technical Blueprint

## Prototype hypothesis

A centrally hosted, evidence-backed knowledge graph can provide persistent shared
memory to otherwise isolated AI clients. The prototype succeeds when one client
can write natural-language knowledge and a second client, using the same MCP URL,
can retrieve and correctly use it.

## Scope

Included:

- Natural-language ingestion
- Dynamic entity kinds and predicates
- Conservative entity resolution
- Evidence and basic supersession
- Hybrid lexical/vector retrieval plus bounded traversal
- Shared Streamable HTTP MCP access

Excluded:

- Authentication and permissions
- Organizations and collaboration workflows
- Git-style branches, commits, and conflict resolution
- UI, queues, and production scaling

## Data model

Every node carries `knowledge_id`, and all queries enforce it.

- `KnowledgeBase`: generated opaque ID.
- `Entity`: immutable ID, canonical name, dynamic kind, summary, embedding.
- `Alias`: normalized surface form connected to an entity. The same normalized
  name may map to multiple entities, preserving ambiguity.
- `Evidence`: original text, source, ingestion time, and embedding.
- `Claim`: dynamic predicate, status, confidence, polarity, validity fields, and
  deterministic fingerprint.

Claims are first-class nodes instead of arbitrary Neo4j relationship types. This
allows multiple evidence records, contradictions, and supersession without
discarding the old context.

## Ingestion

1. Scope the request from `/mcp/{knowledge_id}`.
2. Store and embed the original text as immutable evidence.
3. Ask one server-controlled LLM for validated entities and claims.
4. Generate candidates from exact aliases, Neo4j full-text search, and vector
   similarity.
5. Ask the LLM to choose `LINK`, `NEW`, or `UNRESOLVED`; require high confidence
   before linking.
6. Create or reuse entities.
7. Fingerprint and upsert claims.
8. If the text explicitly replaces a fact, retain the old claim as `superseded`
   and link the new claim to it.

The original text is always retained because structured extraction can lose
nuance or be incorrect.

## Retrieval

1. Embed the question.
2. Search aliases lexically and entities/evidence semantically.
3. Fuse rankings rather than comparing incompatible raw scores.
4. Expand selected entities through at most two claim hops.
5. Return structured entities, claims, statuses, and source evidence.
6. Let the client model synthesize the final answer and abstain when
   `insufficient_evidence` is true.

## MCP deployment

One stateless MCP server runs on Railway. Its middleware converts a
knowledge-specific URL into a request scope:

```text
https://DOMAIN/mcp/kg_<id>
```

The model never needs to provide the ID as a tool argument. `/mcp/bootstrap`
exposes `create_knowledge_base`; after creation, clients reconnect to the scoped
URL.

## Demo acceptance cases

1. Ingest “Our backend uses Neo4j” twice; the second ingestion reuses the entity
   and claim.
2. Ingest “Cursor”, then “Cursor IDE”; resolution should reuse the entity when
   context supports it.
3. Ingest Apple the company and apple the fruit; they must remain separate.
4. Ingest “We migrated from FastAPI to NestJS”; the graph retains FastAPI and
   records the replacement.
5. Ask why Neo4j was chosen; the response must include source evidence.
6. Store a multi-hop chain and retrieve the two-hop answer.
7. Write from client A and read from client B using the same URL.

False entity merges and unsupported answers are considered more serious than
temporary duplicates or abstention.

## Known limitations

- MCP instructions encourage but cannot force a host LLM to call memory tools.
- The LLM confidence value is not calibrated probability.
- Knowledge IDs are bearer capabilities, not real authorization.
- Full entity resolution and contradiction detection remain hard research
  problems.
- Embedding dimensions must match the configured Neo4j vector indexes.
- The implementation targets the stable MCP Python SDK 1.x; v2 requires a
  deliberate migration.
