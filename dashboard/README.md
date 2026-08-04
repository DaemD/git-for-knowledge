# grphly dashboard

Knowledge-base control plane for grphly (GitHub-shaped UX for shared knowledge).

## Run locally

1. Backend with `AUTH_DISABLED=true` (or Auth0 configured).
2. API CORS already allows `http://localhost:3000`.

```bash
cd dashboard
cp .env.example .env.local
npm install
npm run dev
```

Open http://localhost:3000 — with `NEXT_PUBLIC_AUTH_DISABLED=true` you are signed in as `sub:dashboard-dev`.

## Deploy (Railway)

The repo-root `railway.toml` is for the **MCP/API** service. Do not let the dashboard service use that file.

### Recommended settings (dashboard service)

1. Branch: `dev`
2. **Root Directory: leave empty** (blank)
3. **Config-as-code path:** `railway.dashboard.toml`  
   (or turn off config-as-code and set Dockerfile path to `Dockerfile.dashboard`)
4. Do **not** attach Postgres

Then set env vars (see below) and deploy a **new** deployment (not “Redeploy” on the failed one).

If you previously set Root Directory to `dashboard` and got  
`lstat .../dashboard: no such file or directory` — clear Root Directory and use `Dockerfile.dashboard` instead.

```text
NEXT_PUBLIC_API_BASE_URL=https://grphly-dev.miless.app
NEXT_PUBLIC_AUTH_DISABLED=false
NEXT_PUBLIC_AUTH0_DOMAIN=dev-xx4jrebrryos1jre.us.auth0.com
NEXT_PUBLIC_AUTH0_CLIENT_ID=<spa-client-id>
NEXT_PUBLIC_AUTH0_AUDIENCE=<same as API OAUTH_AUDIENCE>
NEXT_PUBLIC_AUTH0_REDIRECT_URI=https://<your-dashboard-domain>
```

5. On the **API** service, add the dashboard origin to CORS:

```text
DASHBOARD_CORS_ORIGINS=https://<your-dashboard-domain>,http://localhost:3000
```

6. Auth0 SPA app: Allowed Callback / Logout / Web Origins = dashboard URL

Without Google Auth0 env, the dashboard will load but login will not work against the live API.
