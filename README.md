# Shared Knowledge Graph MCP

A prototype shared memory service for AI assistants. Users push natural-language
knowledge; the service extracts evidence-backed entities and claims into Neo4j.
Any MCP client connected to the same knowledge-specific URL can retrieve that
context.

## Architecture

```text
Cursor / Claude / another MCP client
                 |
    Streamable HTTP /mcp/{knowledge_id}
                 |
        Python MCP service
          |             |
     OpenAI API      Neo4j Aura
```

The generated `knowledge_id` is a capability identifier. It scopes every graph
query, but it is not authentication. Anyone who knows the URL can use that graph.

## MCP tools

- `create_knowledge_base`: creates a graph ID from `/mcp/bootstrap`.
- `push_memory`: accepts natural language and stores entities, claims, and source
  evidence.
- `get_relevant_context`: evidence-first retrieval intended to run before project
  answers.
- `search_knowledge`: searches entities and claims.
- `get_entity`: retrieves one entity and its evidence-backed claims.
- `get_neighborhood`: traverses one or two bounded claim hops.

The server instructions ask clients to retrieve context before project answers
and push durable information. MCP cannot force every host application to invoke a
tool, so add an equivalent instruction in clients that support project rules.

## Local setup

Python 3.12 or newer is required.

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
Copy-Item .env.example .env
```

Put the rotated Neo4j credentials and the LLM provider key in `.env`. Never
commit `.env`.

```powershell
uvicorn app.server:app --reload
```

Health check:

```text
GET http://127.0.0.1:8000/health
```

Use MCP Inspector or an MCP client against:

```text
http://127.0.0.1:8000/mcp/bootstrap
```

Call `create_knowledge_base`, then reconnect using the returned path:

```text
http://127.0.0.1:8000/mcp/kg_<generated-id>
```

## Cursor configuration

Create `.cursor/mcp.json` in the client project:

```json
{
  "mcpServers": {
    "shared-knowledge": {
      "type": "http",
      "url": "https://YOUR-RAILWAY-DOMAIN/mcp/kg_YOUR_ID"
    }
  }
}
```

Add a project rule:

```text
Before answering questions that may depend on project knowledge, call
get_relevant_context. When the user states durable project information, call
push_memory. Cite returned evidence and do not invent missing facts.
```

Use the same URL in another compatible AI client to share the graph.

## Railway deployment

1. Push this directory to a repository and create a Railway service from it.
2. Railway builds the included `Dockerfile`.
3. Add these Railway variables:
   - `NEO4J_URI`
   - `NEO4J_USERNAME`
   - `NEO4J_PASSWORD`
   - `NEO4J_DATABASE`
   - `OPENAI_API_KEY`
   - `OPENAI_MODEL`
   - `OPENAI_EMBEDDING_MODEL`
   - `EMBEDDING_DIMENSIONS`
4. Generate a public Railway domain.
5. Connect to `https://DOMAIN/mcp/bootstrap` once to create a knowledge ID.
6. Give the resulting knowledge-specific MCP URL to each AI client.

Railway supplies `PORT`; the container listens on that value. `/health` is used
for deployment health checks.

## Graph model

```text
(KnowledgeBase)-[:CONTAINS]->(Entity)
(Alias)-[:ALIAS_OF]->(Entity)
(Claim)-[:SUBJECT]->(Entity)
(Claim)-[:OBJECT]->(Entity)
(Claim)-[:SUPPORTED_BY]->(Evidence)
(new Claim)-[:SUPERSEDES]->(old Claim)
```

Generated semantics such as `USES`, `REPLACED`, or `DEPENDS_ON` are stored in
`Claim.predicate`. This keeps predicates open-ended while allowing each claim to
retain evidence, confidence, temporal fields, and replacement history.

## Tests

```powershell
pytest
```

The unit tests do not require Neo4j or an API key. End-to-end ingestion requires
both configured services.
