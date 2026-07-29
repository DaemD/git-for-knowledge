FROM python:3.12-slim

WORKDIR /app

COPY index.html styles.css app.js ./

ENV PORT=8080
EXPOSE 8080

# Railway healthchecks need 0.0.0.0, not localhost-only.
CMD ["sh", "-c", "python -m http.server \"${PORT:-8080}\" --bind 0.0.0.0"]
