# Technical Blueprint

## Model

One shared NAMS workspace. Logical knowledge bases are `(auth_user, kb_id)` →
NAMS conversation. Clients pass `kb_id` on every remember/recall. Username is
derived from the verified OAuth identity, never from an untrusted payload field.

## Tools

`get_identity`, `list_knowledge_bases`, `create_knowledge_base`, `remember`,
`recall`

## Isolation

- Hard (app): Postgres ownership on `(user_id, kb_id)`
- Soft (NAMS): shared Neo4j entity pool

## Control plane

Postgres: `users`, `graphs` (`kb_id`), `memory_writes`
