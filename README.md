# Shared Knowledge Graph MCP

Google-authenticated shared memory. Everyone shares **one** NAMS workspace.
Each user owns logical **knowledge bases** addressed by `kb_id`. Username
comes from OAuth (not a client-supplied field).

## Addressing

```text
kb_push(kb_id="project-a", text=..., idempotency_key=...)
kb_fetch(kb_id="project-a", question=...)
```

Logical key = authenticated user + `kb_id` → NAMS conversation.

Bob cannot use Alice’s `kb_id`; ownership is enforced in Postgres.

Entity search remains workspace-wide soft isolation inside Neo4j.

## MCP tools (git-style)

| Tool | What it does |
|------|----------------|
| `kb_list` | List your knowledge bases |
| `kb_create(kb_id, name?)` | Create a KB |
| `kb_delete(kb_id)` | Delete a KB you own |
| `kb_push(kb_id, text, idempotency_key, client_id?)` | Store knowledge |
| `kb_fetch(kb_id, question, limit?)` | Retrieve knowledge |
| `kb_invite(kb_id, email, role?)` | Share by Google email |
| `kb_members(kb_id)` | List members / invites |
| `kb_revoke(kb_id, email)` | Remove access |

Invite emails are optional (`INVITE_EMAIL_ENABLED` + Resend).

## Easy commands (Cursor chat)

Type these in AI chat (or `/kb-push` slash commands). The model calls the
matching MCP tool — there is no separate shell.

See [docs/KB_COMMANDS.md](docs/KB_COMMANDS.md).

```text
kb list
kb create my-project
kb use my-project
kb push We use Postgres for the control plane
kb fetch What database do we use?
kb invite alice@gmail.com write
```

## Local setup

```powershell
pip install -e ".[dev]"
Copy-Item .env.example .env
uvicorn app.server:app --reload
```

## Auth note

Configure Auth0 (or compatible) with Google social login. Set
`PUBLIC_BASE_URL` to the public MCP URL. Cursor callbacks must be Cursor
localhost URLs, not your Railway `/mcp` path.
