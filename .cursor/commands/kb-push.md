# kb push

Like `git push`, but for durable knowledge.

1. Read default `kb_id` from `.cursor/kb-id` (ask/list if missing).
2. Call `kb_push` with:
   - that `kb_id`
   - `text` = the content below (clean it up if needed)
   - `idempotency_key` = a new UUID
3. Confirm what was stored in one short sentence.

Content to push:

$ARGUMENTS
