# kb use

Set the default knowledge base for this project.

1. Parse `$ARGUMENTS` as the `kb_id`.
2. Optionally call `kb_list` to confirm it exists / is accessible.
3. Write the kb_id (single line, no quotes) to `.cursor/kb-id`.
4. Confirm: now using that kb_id for `kb push` / `kb fetch`.

Arguments:

$ARGUMENTS
