# Delete knowledge base

Use Shared Knowledge MCP `delete_knowledge_base`.

1. Read `.cursor/kb-id` if present, otherwise parse `$ARGUMENTS` as the kb_id.
2. Call `delete_knowledge_base` for that kb_id (owner only).
3. Confirm deleted / whether NAMS conversation was cleared.
4. If `.cursor/kb-id` matched the deleted KB, tell the user to update or remove that file.

Arguments:

$ARGUMENTS
