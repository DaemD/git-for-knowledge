# Remember to shared knowledge

Use the Shared Knowledge MCP tools.

1. Read `.cursor/kb-id` if it exists; that is the default `kb_id`.
2. If `.cursor/kb-id` is missing, call `list_knowledge_bases` and use the most relevant KB, or ask which `kb_id` to use.
3. Call `remember` with:
   - `kb_id`: from step 1/2
   - `text`: the durable fact/decision below (rewrite clearly if needed)
   - `idempotency_key`: a new UUID
4. Confirm what was stored in one short sentence.

Content to remember:

$ARGUMENTS
