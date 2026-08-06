# Stage 1: Build frontend
FROM node:20-alpine AS frontend
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci || npm install
COPY frontend/ ./
RUN npm run build

# Stage 2: Python app
FROM python:3.13-slim-bookworm

LABEL org.opencontainers.image.title="FusionSync Email Verifier"
LABEL org.opencontainers.image.description="Local-first email list verification with web UI"
LABEL org.opencontainers.image.source="https://github.com/recallsync/email-verifier"
LABEL org.opencontainers.image.vendor="EnvisionTech AI"

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    dnsutils \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py config.py entrypoint.sh ./
COPY db/ ./db/
COPY migrations/ ./migrations/
COPY processor/ ./processor/
COPY routes/ ./routes/
COPY services/ ./services/
COPY utils/ ./utils/
COPY scripts/ ./scripts/
COPY --from=frontend /build/dist ./static

RUN mkdir -p /app/data/uploads /app/data/logs \
    && chmod +x /app/entrypoint.sh

EXPOSE 5050

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:5050/health || exit 1

ENTRYPOINT ["/app/entrypoint.sh"]
