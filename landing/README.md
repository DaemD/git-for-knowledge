# Graphly landing

Static marketing page. Deploy as a **separate** Railway service from the MCP API.

## Railway

1. New service from this repo
2. **Root Directory:** `landing`
3. Builder: Dockerfile (uses `landing/Dockerfile`)
4. No build command needed — image serves files with Python’s HTTP server

Do not point this service at the repo-root `Dockerfile` (that’s the MCP API).

## Local preview

```powershell
python -m http.server 5173
```
