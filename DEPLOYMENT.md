# 🚀 Production Deployment Guide

## Docker Deployment

### Prerequisites

- Docker installed
- Docker Compose installed

### Quick Start

#### 1. Build and Run with Docker Compose

```bash
# Build and start the service
docker-compose up -d

# View logs
docker-compose logs -f

# Stop the service
docker-compose down
```

#### 2. Build Docker Image Manually

```bash
# Build image
docker build -t email-verifier:latest .

# Run container
docker run -d \
  -p 5050:5050 \
  --name email-verifier \
  email-verifier:latest
```

### Production Server Setup

The app uses **Gunicorn** (production WSGI server) instead of Flask's development server.

**Configuration:**

- **Workers:** 4 (adjust based on CPU cores)
- **Threads:** 2 per worker
- **Timeout:** 300 seconds (for slow SMTP verification)
- **Port:** 5050

### Environment Variables (Optional)

Create a `.env` file:

```bash
# Optional configurations
WORKERS=4
THREADS=2
TIMEOUT=300
PORT=5050
```

Update `docker-compose.yml`:

```yaml
environment:
  - WORKERS=${WORKERS:-4}
  - THREADS=${THREADS:-2}
```

### Health Check

The service includes a health check endpoint:

```bash
curl http://localhost:5050/health
```

Response:

```json
{
  "status": "healthy",
  "service": "email-verifier"
}
```

### Monitoring

#### View Logs

```bash
# Docker Compose
docker-compose logs -f email-verifier

# Docker
docker logs -f email-verifier
```

#### Container Stats

```bash
docker stats email-verifier
```

### Scaling

Update `docker-compose.yml` to scale:

```yaml
services:
  email-verifier:
    deploy:
      replicas: 3 # Run 3 instances
```

Or manually scale:

```bash
docker-compose up -d --scale email-verifier=3
```

### Reverse Proxy (Nginx)

For production, put Nginx in front:

```nginx
server {
    listen 80;
    server_name yourdomain.com;

    location / {
        proxy_pass http://localhost:5050;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Increase timeout for slow email verification
        proxy_read_timeout 300s;
        proxy_connect_timeout 300s;
    }
}
```

### SSL/HTTPS (Let's Encrypt)

```bash
# Install certbot
sudo apt-get install certbot python3-certbot-nginx

# Get SSL certificate
sudo certbot --nginx -d yourdomain.com
```

### Cloud Deployment

#### AWS (EC2/ECS)

```bash
# Build and push to ECR
docker build -t email-verifier .
docker tag email-verifier:latest <account-id>.dkr.ecr.<region>.amazonaws.com/email-verifier:latest
docker push <account-id>.dkr.ecr.<region>.amazonaws.com/email-verifier:latest
```

#### Google Cloud (Cloud Run)

```bash
# Build and deploy
gcloud builds submit --tag gcr.io/<project-id>/email-verifier
gcloud run deploy email-verifier --image gcr.io/<project-id>/email-verifier --platform managed
```

#### DigitalOcean

```bash
# Use their container registry
docker build -t email-verifier .
docker tag email-verifier:latest registry.digitalocean.com/<your-registry>/email-verifier:latest
docker push registry.digitalocean.com/<your-registry>/email-verifier:latest
```

### Performance Tuning

#### Adjust Workers (based on CPU cores)

```bash
# Formula: (2 x CPU cores) + 1
# 2 CPU cores = 5 workers
# 4 CPU cores = 9 workers
```

Update Dockerfile:

```dockerfile
CMD ["gunicorn", "--workers", "9", ...]
```

#### Memory Considerations

- Each worker uses ~100-200MB
- 4 workers = ~800MB RAM minimum
- Recommend 2GB+ for production

### Troubleshooting

#### Container won't start

```bash
# Check logs
docker-compose logs email-verifier

# Debug mode
docker run -it email-verifier:latest /bin/bash
```

#### SMTP connection issues

```bash
# Test DNS resolution inside container
docker exec -it email-verifier nslookup gmail.com

# Test SMTP connectivity
docker exec -it email-verifier telnet smtp.gmail.com 25
```

#### Port already in use

```bash
# Find process using port 5050
lsof -i :5050

# Kill process
kill -9 <PID>
```

### Security Best Practices

1. **Use secrets for sensitive data**
2. **Run container as non-root user** (add to Dockerfile)
3. **Limit container resources:**
   ```yaml
   deploy:
     resources:
       limits:
         cpus: "2"
         memory: 2G
   ```
4. **Enable firewall rules**
5. **Regular security updates**

### Backup & Restore

#### Export logs

```bash
docker-compose logs email-verifier > logs_backup.txt
```

#### Save container state

```bash
docker commit email-verifier email-verifier-backup:$(date +%Y%m%d)
```

---

## Quick Commands Reference

```bash
# Build
docker-compose build

# Start
docker-compose up -d

# Stop
docker-compose down

# Restart
docker-compose restart

# Logs
docker-compose logs -f

# Shell access
docker exec -it email-verifier /bin/bash

# Remove everything
docker-compose down -v --rmi all
```
