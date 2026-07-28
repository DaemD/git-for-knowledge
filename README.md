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

- `get_identity`: generates an opaque, human-readable client identifier for a
  client to save locally.
- `remember`: queues durable natural language for NAMS-managed graph ingestion
  and records its provenance locally.
- `recall`: retrieves relevant context, entities, relationships, and sources for
  the connected AI to use in its answer.

The server instructions ask clients to call `recall` before memory-dependent
answers and `remember` when the user requests durable storage. MCP cannot force
every host application to invoke a tool, so add an equivalent instruction in
clients that support project rules.

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

Use MCP Inspector or an MCP client against the configured knowledge ID:

```text
http://127.0.0.1:8000/mcp/kg_<configured-id>
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
Before answering a question that may depend on shared knowledge, call recall.
Before the first remember call in this project, read `.mcp-identity` from the
project root. If it is missing, call get_identity, save the returned value to
`.mcp-identity`, then ensure `.gitignore` excludes it: append `.mcp-identity`
if `.gitignore` exists without that line, otherwise create `.gitignore`
containing only `.mcp-identity`. Use the saved value as client_id for every
remember call. Never replace an existing `.mcp-identity` value. When the user
asks to preserve durable information, call remember. Use returned context and
sources, and do not invent missing facts.
```

Use the same URL in another compatible AI client to share the graph.

## Client identity, provenance, and retry safety

The first AI client working in a project handles the identity automatically:

1. Check for `.mcp-identity` in the client project's root directory.
2. If the file does not exist, call `get_identity` and save its returned string
   as the complete file content. In the same bootstrap step, ensure `.gitignore`
   excludes `.mcp-identity`: append the line if `.gitignore` exists without it,
   or create `.gitignore` containing only that line if it does not exist.
3. If the file exists, read its content instead. Never call `get_identity` to
   replace an existing value.
4. Pass the file content as `client_id` on every `remember` call.

The MCP server cannot read or write the client's filesystem. The tool
descriptions give compatible AI clients these instructions, so copying the MCP
configuration is the only human setup required.

Clients without project-file access, such as a browser-hosted chat interface,
may omit `client_id`. The service records those pushes as
`web-unattributed` instead of rejecting them. This preserves ingestion and
idempotency, but not per-client provenance.

`remember` uses these fields in addition to `text`:

| Field | Supplied by | Purpose |
| --- | --- | --- |
| `client_id` | MCP client | Optional. Opaque value read from `.mcp-identity`; omitted values become `web-unattributed`. |
| `idempotency_key` | MCP client | Stable client-generated UUID (recommended) reused when retrying the same push. |
| `accepted_at` | This server | UTC time at which the server accepts a new push. Do not send this field. |

For example, an MCP client should call `remember` with:

```json
{
  "text": "The production API uses Neo4j Aura.",
  "client_id": "swift-otter-482193",
  "idempotency_key": "5be1f3e7-c742-46a3-8e1a-e299a0cb6863"
}
```

Hosted NAMS accepts `metadata` and `user_identifier` without rejecting the
write, but a live round-trip test against the hosted endpoint confirmed that it
does not retain either value on message retrieval. The service therefore keeps
provenance and idempotency in its own SQLite ledger at
`data/memory_writes.db`; it does not send unsupported metadata fields to NAMS.

Before calling NAMS, `remember` creates a pending row keyed by
`idempotency_key`. A retry of a completed row returns the original `memory_id`
with `status="already_exists"` without another NAMS call. A retry while the
row is pending returns `status="processing"` and does not submit a duplicate.
If NAMS fails, the row is marked failed and a later retry may submit it again.
The ledger records the server-generated UTC acceptance time, a SHA-256 content
hash, the client identifier, and the NAMS message ID once available.

`recall` preserves NAMS as `sources[].source` and returns provenance for a
matching source message as `sources[].provenance`:

```json
{
  "id": "msg-1",
  "source": "nams",
  "text": "The production API uses Neo4j Aura.",
  "ingested_at": "2026-07-28T12:00:00Z",
  "provenance": {
    "client_id": "swift-otter-482193",
    "accepted_at": "2026-07-28T12:00:00Z"
  }
}
```

`client_id` is an installation-level label, not a verified human identity or
an authorization mechanism. Authentication and user identity are separate,
deferred work.

Older NAMS messages that predate the ledger, or messages written outside this
service, have `provenance: null` rather than causing `recall` to fail.

## Railway deployment

1. Push this directory to a repository and create a Railway service from it.
2. Railway builds the included `Dockerfile`.
3. Add these Railway variables:
   - `MEMORY_API_KEY`
   - `MEMORY_ENDPOINT` (normally `https://memory.neo4jlabs.com/v1`)
   - `KNOWLEDGE_ID` (set this to preserve an existing MCP URL)
   - `MEMORY_WORKSPACE_ID` only for an admin/header-scoped key
4. Generate a public Railway domain.
5. Give `https://DOMAIN/mcp/$KNOWLEDGE_ID` to each AI client.

Railway supplies `PORT`; the container listens on that value. `/health` is used
for deployment health checks.

The default Railway filesystem is ephemeral. To retain provenance and
idempotency data across deploys, configure a Railway Volume mounted at
`/app/data`; this is where the service's relative
`data/memory_writes.db` path resolves in the container. Without that volume,
the SQLite database is reset on redeploy.

## NAMS ingestion

`remember` calls NAMS `add_message`. NAMS runs its extraction pipeline
server-side and creates `Entity`, `MENTIONS`, and `RELATED_TO` graph structures
asynchronously. A successful call reports `status="processing"`; new entities
may take a few seconds to appear in `recall` and in the NAMS console.

## Tests

```powershell
pytest
```

The unit tests do not require NAMS or an API key. End-to-end ingestion requires
the configured NAMS workspace.
