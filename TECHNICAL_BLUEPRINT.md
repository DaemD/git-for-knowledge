# Technical Blueprint

## Prototype hypothesis

A centrally hosted knowledge graph can provide persistent shared memory to
otherwise isolated AI clients. The prototype succeeds when one client writes
natural-language knowledge and another client, using the same MCP URL, retrieves
the resulting NAMS context and graph entities.

## Scope

Included:

- Natural-language ingestion through NAMS
- Server-managed extraction, embeddings, deduplication, and observations
- Semantic entity search and bounded relationship traversal
- Source messages and NAMS entity history
- Shared Streamable HTTP MCP access

Excluded:

- Authentication and permissions beyond an unguessable MCP URL
- Dynamic NAMS workspace provisioning
- Organizations and collaboration workflows
- Git-style branches, commits, and conflict resolution
- A custom extraction or embedding pipeline

## Isolation

The configured `MEMORY_API_KEY` is bound to one NAMS workspace. That workspace
is the hard graph boundary. This deployment exposes it through one
`knowledge_id`; `KNOWLEDGE_ID` can preserve an existing MCP URL, otherwise a
stable ID is derived from the API key.

There is no public bootstrap tool. The operator configures the knowledge ID and
distributes the resulting MCP URL.

## Ingestion

1. Scope the request from `/mcp/{knowledge_id}`.
2. Verify that the URL matches this deployment's workspace ID.
3. Reuse or create one NAMS conversation for the knowledge base.
4. Send the unmodified text to NAMS with `add_message`.
5. Return the NAMS message ID immediately with `status="processing"`.
6. NAMS asynchronously extracts and embeds entities, resolves duplicates,
   creates `MENTIONS` links, stores semantic relationships, and updates
   observations/reflections.

The service no longer calls OpenAI directly and no longer writes custom Cypher.
NAMS may still use models internally as part of its managed extraction service.

## Retrieval

1. Search workspace entities through NAMS semantic search.
2. Retrieve NAMS's three-tier conversation context.
3. Read entity relationships through NAMS's read-only Cypher endpoint.
4. Retrieve entity mention history for source evidence.
5. Map the results to the existing MCP response objects.
6. Let the consuming AI synthesize the final answer.

Newly pushed information is eventually consistent and may take a few seconds to
appear in entity search.

## MCP deployment

One stateless MCP server runs on Railway:

```text
https://DOMAIN/mcp/kg_<id>
```

Required Railway variables:

```text
MEMORY_API_KEY
MEMORY_ENDPOINT=https://memory.neo4jlabs.com/v1
KNOWLEDGE_ID=kg_<existing-id>
```

`MEMORY_WORKSPACE_ID` is needed only for admin/header-scoped deployments.

## MCP tools

- `remember`: queue durable knowledge for NAMS ingestion.
- `recall`: return relevant NAMS context, entities, relationships, and sources
  for the connected AI to use in its answer.

## Limitations

- A workspace-bound API key supports one hard-isolated graph.
- NAMS ingestion is asynchronous.
- The hosted API controls extraction and ontology behavior.
- NAMS does not currently provide durable request idempotency through the Python
  message API; entity deduplication is server-managed, but retrying a push can
  create another source message.
- The MCP URL remains a bearer capability rather than user authentication.
- NAMS is a Neo4j Labs project and should be treated as experimental.
