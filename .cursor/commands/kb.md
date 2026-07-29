# kb — Graphly commands

Users type git-style commands in chat. Map them to Graphly MCP tools.

## Command → tool

| User types | MCP tool |
|------------|----------|
| `kb list` | `kb_list` |
| `kb create <id> [name]` | `kb_create` |
| `kb use <id>` | save `<id>` to `.cursor/kb-id` (no MCP call) |
| `kb push <text>` | `kb_push` |
| `kb fetch <question>` | `kb_fetch` |
| `kb invite <email> [read\|write]` | `kb_invite` |
| `kb members` | `kb_members` |
| `kb revoke <email>` | `kb_revoke` |
| `kb delete <id>` | `kb_delete` |

## Defaults

- Prefer `kb_id` from `.cursor/kb-id` when the command omits an id.
- For `kb push`, use a fresh UUID as `idempotency_key`.
- Confirm results briefly after each command.

## Arguments

$ARGUMENTS
