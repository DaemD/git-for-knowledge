# Knowledge base commands (`kb`)

## How it works

These are **not** terminal commands. You type them in **AI chat** (Cursor,
Claude, etc.). The model reads what you typed and calls the matching grphly
MCP tool.

Three ways to invoke:

1. **Plain chat** — type `kb push We use Postgres` and send
2. **Slash command** — type `/kb-push` then the text (Cursor inserts a prompt)
3. **Natural language** — “push this to the knowledge base” also works via the project rule

`kb use` is local only: it writes `.cursor/kb-id` so later push/fetch know the default KB.

## Quick reference

```text
kb list
kb create <kb_id> [name]
kb use <kb_id>
kb push <text>
kb fetch <question>
kb invite <email> [read|write]
kb members
kb revoke <email>
kb delete <kb_id>
```

## Like git

| Git feel | You type in chat | MCP tool |
|----------|------------------|----------|
| `git remote -v` | `kb list` | `kb_list` |
| `git init` | `kb create my-project` | `kb_create` |
| `git checkout` | `kb use my-project` | (writes `.cursor/kb-id`) |
| `git push` | `kb push We use Postgres` | `kb_push` |
| `git fetch` | `kb fetch What DB?` | `kb_fetch` |
| invite | `kb invite alice@gmail.com write` | `kb_invite` |
| | `kb members` | `kb_members` |
| | `kb revoke alice@gmail.com` | `kb_revoke` |
| | `kb delete my-project` | `kb_delete` |

## Examples

```text
kb create startup-idea "Startup notes"
kb use startup-idea
kb push Backend uses Neo4j for relationships
kb fetch What database do we use and why?
kb invite bob@gmail.com write
kb members
```
