# kb fetch

Like reading from remote memory.

1. Read default `kb_id` from `.cursor/kb-id` (ask/list if missing).
2. Call `kb_fetch` with that `kb_id` and the question below.
3. Answer using fetched context. If empty, say so briefly.
4. Mention writer_email from provenance when useful.

Question:

$ARGUMENTS
