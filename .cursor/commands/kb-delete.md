# kb delete

Owner-only. Deletes the knowledge base from Postgres and best-effort clears the NAMS conversation.

1. kb_id from `$ARGUMENTS` or `.cursor/kb-id`.
2. Confirm destructive intent briefly, then call `kb_delete`.
3. If `.cursor/kb-id` matched, tell the user to clear/update that file.

Arguments:

$ARGUMENTS
