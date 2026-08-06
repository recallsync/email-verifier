# Stage 1: Build frontend
FROM node:20-alpine AS frontend
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# Stage 2: Python app
FROM python:3.13-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    dnsutils \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
COPY --from=frontend /build/dist ./static

RUN mkdir -p /app/data/uploads /app/data/logs \
    && chmod +x /app/entrypoint.sh

EXPOSE 5050

ENTRYPOINT ["/app/entrypoint.sh"]
