# Graphly landing

Static marketing page. Deploy as a **separate** Railway service from the MCP API.

## Local preview

```powershell
cd landing
python -m http.server 5173
```

## Railway

1. New service → this repo → branch `dev`
2. Set **Root Directory** to `landing` (required)
3. Leave Build / Start empty — `railway.toml` + `Dockerfile` handle it
4. Deploy

Do **not** point this service at the repo root; the root `Dockerfile` builds the Graphly MCP API.
