# Shared Knowledge Graph MCP

A prototype shared memory service for AI assistants. Users push natural-language
knowledge to Neo4j Agent Memory Service (NAMS), which stores the message and
asynchronously extracts, embeds, deduplicates, and links entities in the
workspace's Neo4j graph. Any MCP client connected to the same
knowledge-specific URL can retrieve that context.

## Architecture

```text
Cursor / Claude / another MCP client
                 |
    Streamable HTTP /mcp/{knowledge_id}
                 |
        Python MCP service
                 |
       NAMS hosted memory API
                 |
    NAMS-managed or external Aura graph
```

The `knowledge_id` is a capability identifier for the one NAMS workspace bound
to this deployment. The NAMS API key provides workspace isolation; anyone who
knows the public MCP URL can use the tools exposed by this service.

## MCP tools

- `create_knowledge_base`: returns the ID bound to the configured NAMS workspace.
- `push_memory`: queues natural language for NAMS-managed graph ingestion.
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

Put the NAMS workspace API key in `.env`. Never commit `.env`. No direct Neo4j
or OpenAI credentials are required by this MCP service.

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
   - `MEMORY_API_KEY`
   - `MEMORY_ENDPOINT` (normally `https://memory.neo4jlabs.com/v1`)
   - `KNOWLEDGE_ID` (set this to preserve an existing MCP URL)
   - `MEMORY_WORKSPACE_ID` only for an admin/header-scoped key
4. Generate a public Railway domain.
5. Connect to `https://DOMAIN/mcp/bootstrap` once to create a knowledge ID.
6. Give the resulting knowledge-specific MCP URL to each AI client.

Railway supplies `PORT`; the container listens on that value. `/health` is used
for deployment health checks.

## NAMS ingestion

`push_memory` calls NAMS `add_message`. NAMS runs its extraction pipeline
server-side and creates `Entity`, `MENTIONS`, and `RELATED_TO` graph structures
asynchronously. A successful push therefore reports `ingestion_status="queued"`;
new entities may take a few seconds to appear in searches and in the NAMS
console.

## Tests

```powershell
pytest
```

The unit tests do not require NAMS or an API key. End-to-end ingestion requires
the configured NAMS workspace.
