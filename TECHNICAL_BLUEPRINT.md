# Technical Blueprint

## Model

grphly: one shared NAMS workspace. Logical knowledge bases are
`(auth_user, kb_id)` → NAMS conversation. Clients pass `kb_id` on every
`kb_push` / `kb_fetch`. Username is derived from the verified OAuth identity,
never from an untrusted payload field.

## Tools

`kb_list`, `kb_create`, `kb_delete`, `kb_push`, `kb_fetch`, `kb_invite`,
`kb_members`, `kb_revoke`.

## Isolation

- Hard (app): Postgres ownership on `(user_id, kb_id)`
- Soft (NAMS): shared Neo4j entity pool

## Control plane

Postgres: `users`, `graphs` (`kb_id`), `memory_writes`
