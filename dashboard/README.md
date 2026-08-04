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

1. New Railway service from this repo
2. **Root Directory:** `dashboard`
3. Builder: Dockerfile (`dashboard/Dockerfile`)
4. Set build/runtime env (NEXT_PUBLIC_* must exist at **build** time):

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
