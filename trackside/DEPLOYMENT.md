# Trackside — Production Deployment Guide

This guide walks through step-by-step instructions for provisioning and deploying Trackside to a production server or karting academy node.

---

## 1. Prerequisites

- Ubuntu 22.04 / 24.04 LTS or Debian 12 server
- Docker Engine 24.0+ & Docker Compose v2
- Domain name pointed to server IP (e.g. `trackside.example.com`)
- Nginx & Certbot for SSL termination

---

## 2. Environment Configuration

1. Clone repository to server:
   ```bash
   git clone https://github.com/Vivek6282/Research-Project-.git /opt/trackside
   cd /opt/trackside/trackside
   ```

2. Copy `.env.example` to `.env` and fill in secrets:
   ```bash
   cp .env.example .env
   nano .env
   ```

3. Update mandatory variables:
   - `DJANGO_ENV=production`
   - `DEBUG=False`
   - `SECRET_KEY=<secure_random_key>`
   - `ALLOWED_HOSTS=trackside.example.com,127.0.0.1`
   - `CORS_ALLOWED_ORIGINS=https://trackside.example.com`

---

## 3. Database Migration & Admin Seeding

1. Start database and Redis containers:
   ```bash
   docker-compose up -d db redis
   ```

2. Run database migrations:
   ```bash
   docker-compose run --rm backend python manage.py migrate
   ```

3. Seed initial System Admin account:
   ```bash
   docker-compose run --rm backend python manage.py seed_admin
   ```
   *Note credentials output on console (e.g., `admin@trackside.local` / generated password).*

---

## 4. Launching Backend & Frontend

1. Start all containers in detached mode:
   ```bash
   docker-compose up -d
   ```

2. Verify Daphne ASGI server is running on port 8000:
   ```bash
   docker-compose logs -f backend
   ```

---

## 5. SSL & Nginx Configuration

Configure Nginx reverse proxy for HTTP and WebSocket (`/ws/`) traffic:

```nginx
server {
    server_name trackside.example.com;

    location / {
        root /opt/trackside/trackside/frontend/dist;
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # WebSocket Proxying for Live Telemetry
    location /ws/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "Upgrade";
        proxy_set_header Host $host;
    }
}
```

Enable SSL certificate using Certbot:
```bash
sudo certbot --nginx -d trackside.example.com
```
