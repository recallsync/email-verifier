# Use official Python runtime as base image
FROM python:3.13-slim

# Set working directory in container
WORKDIR /app

# Install system dependencies for DNS resolution
RUN apt-get update && apt-get install -y \
    dnsutils \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better Docker caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app.py .
COPY utils/ ./utils/

# Create directory for temporary files
RUN mkdir -p /tmp/email-verifier

# Expose port
EXPOSE 5050

# Use gunicorn as production WSGI server
# Workers: 4 (adjust based on your server CPU cores)
# Threads: 2 per worker
# Timeout: 300 seconds (5 min) for slow email verification
CMD ["gunicorn", "--bind", "0.0.0.0:5050", "--workers", "4", "--threads", "2", "--timeout", "300", "--access-logfile", "-", "--error-logfile", "-", "app:app"]

