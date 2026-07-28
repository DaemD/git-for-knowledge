# Shared Knowledge Graph MCP

Google-authenticated shared memory. Everyone shares **one** NAMS workspace.
Each user owns logical **knowledge bases** addressed by `kb_id`. Username
comes from OAuth (not a client-supplied field).

## Addressing

```text
remember(kb_id="project-a", text=..., idempotency_key=...)
recall(kb_id="project-a", question=...)
```

Logical key = authenticated user + `kb_id` → NAMS conversation.

Bob cannot use Alice’s `kb_id`; ownership is enforced in Postgres.

Entity search remains workspace-wide soft isolation inside Neo4j.

## MCP tools

- `list_knowledge_bases` / `create_knowledge_base(kb_id, name?)` / `delete_knowledge_base(kb_id)`
- `remember(kb_id, text, idempotency_key, client_id?)`
- `recall(kb_id, question, limit?)`
- `invite_to_knowledge_base` / `list_knowledge_base_members` / `revoke_knowledge_base_access`

Invite emails are optional (`INVITE_EMAIL_ENABLED` + Resend).

## Local setup

```powershell
pip install -e ".[dev]"
Copy-Item .env.example .env
uvicorn app.server:app --reload
```

Required env: `MEMORY_API_KEY`, `MEMORY_WORKSPACE_ID`, `DATABASE_URL`, plus
OAuth settings or `AUTH_DISABLED=true`.

MCP URL: `https://host/mcp`

## Tests

```powershell
pytest
```
