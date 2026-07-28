# kb invite

Parse `$ARGUMENTS` as: email, optional role (`read` or `write`, default `write`), optional kb_id.

1. Default kb_id from `.cursor/kb-id` unless overridden.
2. Call `kb_invite`.
3. Report status (`pending`/`active`) and whether `email_sent`.
4. Tell the owner to share the `kb_id` if email did not send.

Arguments:

$ARGUMENTS
