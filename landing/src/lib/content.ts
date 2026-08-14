export const MCP_URL = "https://grphly-dev.miless.app/mcp";
export const OAUTH_CLIENT_ID = "0duBflkrH7BfwctBStAM8h6AAzAtbexD";

export const SNIPPETS = {
  cursor: `{
  "mcpServers": {
    "grphly": {
      "type": "http",
      "url": "${MCP_URL}",
      "auth": {
        "CLIENT_ID": "${OAUTH_CLIENT_ID}"
      }
    }
  }
}`,
  antigravity: `{
  "mcpServers": {
    "grphly": {
      "command": "npx",
      "args": [
        "-y",
        "mcp-remote",
        "${MCP_URL}",
        "3334",
        "--host",
        "127.0.0.1",
        "--static-oauth-client-info",
        "{\\"client_id\\":\\"${OAUTH_CLIENT_ID}\\"}"
      ]
    }
  }
}`,
  "claude-code": `claude mcp add --transport http \\
  --client-id ${OAUTH_CLIENT_ID} \\
  grphly ${MCP_URL}`,
  claude: MCP_URL,
  "claude-client": OAUTH_CLIENT_ID,
  chatgpt: MCP_URL,
  "chatgpt-client": OAUTH_CLIENT_ID,
} as const;

export type ClientId =
  | "cursor"
  | "antigravity"
  | "claude-code"
  | "claude"
  | "chatgpt";
