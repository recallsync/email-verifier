# Use official Python runtime as base image
FROM python:3.13-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    dnsutils \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/data/uploads /app/data/logs \
    && chmod +x /app/entrypoint.sh

EXPOSE 5050

ENTRYPOINT ["/app/entrypoint.sh"]
