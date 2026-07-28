# Recall from shared knowledge

Use the Shared Knowledge MCP tools.

1. Read `.cursor/kb-id` if it exists; that is the default `kb_id`.
2. If missing, call `list_knowledge_bases` and pick the best match, or ask which `kb_id`.
3. Call `recall` with that `kb_id` and the question below.
4. Answer using the recalled context. If nothing useful is found, say so briefly.

Question:

$ARGUMENTS
