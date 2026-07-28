# Invite to knowledge base

Use the Shared Knowledge MCP `invite_to_knowledge_base` tool.

1. Read `.cursor/kb-id` if it exists for the default `kb_id`.
2. Parse `$ARGUMENTS` as: email, optional role (`read` or `write`, default `write`), optional kb_id override.
3. Call `invite_to_knowledge_base`.
4. Tell me the invite status (`pending` or `active`) and remind me to tell the invitee the `kb_id`.

Arguments:

$ARGUMENTS
