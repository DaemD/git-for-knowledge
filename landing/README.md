# grphly landing

Vite + React marketing site. Deploy as a **separate** Railway service from the MCP API.

## Local preview

```powershell
cd landing
npm install
npm run dev
```

Open http://localhost:5173

## Build

```powershell
npm run build
npm run preview
```

## Railway

1. New service → this repo → branch `dev`
2. Set **Root Directory** to `landing` (required)
3. Leave Build / Start empty — `railway.toml` + `Dockerfile` handle it
4. Deploy

Do **not** point this service at the repo root; the root `Dockerfile` builds the grphly MCP API.

Legacy static HTML lives in `_legacy/` for reference.
