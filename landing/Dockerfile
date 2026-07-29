FROM python:3.12-slim

WORKDIR /app
COPY index.html styles.css app.js ./

ENV PORT=8080
EXPOSE 8080

CMD ["sh", "-c", "python -m http.server ${PORT:-8080}"]
