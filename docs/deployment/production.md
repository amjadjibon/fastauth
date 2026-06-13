# Production Deployment Guide

## Prerequisites

- Docker 24+ and Docker Compose v2
- PostgreSQL 14+
- Redis 7+
- A domain with TLS termination (nginx, Caddy, or cloud load balancer)

---

## Environment Variables

Copy `.env.example` to `.env` and fill in all values:

```bash
# Core
SECRET_KEY=<64-char random hex — generate with: openssl rand -hex 32>
DATABASE_URL=postgresql+asyncpg://fastauth:password@db:5432/fastauth
REDIS_URL=redis://:password@redis:6379/0

# Token lifetimes
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=30

# CORS — comma-separated list of allowed origins
ALLOWED_ORIGINS=https://app.example.com

# Social login (optional)
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GITHUB_CLIENT_ID=
GITHUB_CLIENT_SECRET=
GITLAB_CLIENT_ID=
GITLAB_CLIENT_SECRET=

# Observability (optional)
OTEL_ENABLED=true
OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4317
```

---

## Docker Compose

```yaml
version: "3.9"
services:
  app:
    image: fastauth:latest
    build: .
    env_file: .env
    ports:
      - "8000:8000"
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    command: >
      sh -c "alembic upgrade head && uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/livez"]
      interval: 10s
      retries: 5

  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: fastauth
      POSTGRES_USER: fastauth
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U fastauth"]
      interval: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    command: redis-server --requirepass ${REDIS_PASSWORD}
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      retries: 5

volumes:
  pgdata:
```

### Running Migrations

```bash
docker compose run --rm app alembic upgrade head
```

---

## Kubernetes (Helm-style)

### Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: fastauth
spec:
  replicas: 3
  selector:
    matchLabels:
      app: fastauth
  template:
    spec:
      initContainers:
        - name: migrate
          image: fastauth:latest
          command: ["alembic", "upgrade", "head"]
          envFrom:
            - secretRef:
                name: fastauth-secrets
      containers:
        - name: fastauth
          image: fastauth:latest
          ports:
            - containerPort: 8000
          envFrom:
            - secretRef:
                name: fastauth-secrets
          readinessProbe:
            httpGet:
              path: /healthz/ready
              port: 8000
            initialDelaySeconds: 10
            periodSeconds: 10
          livenessProbe:
            httpGet:
              path: /livez
              port: 8000
            initialDelaySeconds: 30
            periodSeconds: 30
          resources:
            requests:
              cpu: "250m"
              memory: "256Mi"
            limits:
              cpu: "1000m"
              memory: "512Mi"
```

---

## TLS / Reverse Proxy

### Nginx example

```nginx
server {
    listen 443 ssl http2;
    server_name auth.example.com;

    ssl_certificate     /etc/ssl/certs/auth.example.com.crt;
    ssl_certificate_key /etc/ssl/private/auth.example.com.key;

    location / {
        proxy_pass http://fastauth:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Set `FORWARDED_ALLOW_IPS=*` or the proxy's IP in the app config to trust `X-Forwarded-For`.

---

## Database Backup

```bash
# Daily backup
pg_dump -U fastauth fastauth | gzip > /backups/fastauth_$(date +%Y%m%d).sql.gz

# Restore
gunzip -c /backups/fastauth_20260613.sql.gz | psql -U fastauth fastauth
```

---

## Scaling Considerations

- **Horizontal scaling**: All state is in PostgreSQL + Redis; the app is stateless — run any number of replicas.
- **Connection pooling**: Use PgBouncer in transaction-mode in front of PostgreSQL when running >10 replicas.
- **Rate limiter**: Uses Redis for distributed rate limiting; without Redis it falls back to per-process in-memory counters (not suitable for multi-replica deployments).
- **Sessions**: JTI-based session validation hits PostgreSQL once per refresh — use read replicas for session lookups under high load.

---

## Health Checks

| Endpoint | Purpose |
|----------|---------|
| `GET /livez` | Kubernetes liveness — returns 200 if the process is up |
| `GET /healthz` | Simple DB connectivity check |
| `GET /healthz/ready` | Full readiness — checks DB + Redis |
| `GET /metrics` | Prometheus metrics scrape endpoint |
