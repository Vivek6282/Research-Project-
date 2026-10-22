# Trackside — multi-stage production build (build context: the trackside/ folder).
#   target "backend": Django + Daphne (HTTP and WebSockets), runs as a non-root user
#   target "web":     Caddy serving the built frontend and proxying /api and /ws to the backend

# ---------------------------------------------------------------------------
# Stage 1: build the frontend
# ---------------------------------------------------------------------------
FROM node:22-alpine AS frontend

WORKDIR /build/frontend

# The demo controls must never be part of a hosted build (the server refuses them anyway)
ARG VITE_ENABLE_DEMO_TOOLS=false

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./

# Fail the build when the demo switch is on, whether it came from a build argument or a .env file
RUN set -eu; \
    case "${VITE_ENABLE_DEMO_TOOLS}" in ""|false) ;; *) echo "ERROR: VITE_ENABLE_DEMO_TOOLS must be unset or false for a hosted build." >&2; exit 1;; esac; \
    if grep -qE '^[[:space:]]*VITE_ENABLE_DEMO_TOOLS[[:space:]]*=[[:space:]]*"?true' .env .env.* 2>/dev/null; then \
        echo "ERROR: a frontend .env file turns the demo tools on; remove it for a hosted build." >&2; exit 1; \
    fi

RUN VITE_ENABLE_DEMO_TOOLS=false npm run build

# ---------------------------------------------------------------------------
# Stage 2: backend (Django + Daphne)
# ---------------------------------------------------------------------------
FROM python:3.14-slim AS backend

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# System libraries for PostgreSQL drivers
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# The pinned requirements only (daphne is already in requirements.txt)
COPY backend/requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Application source and the start-up script
COPY backend/ /app/
COPY scripts/backend-entrypoint.sh /usr/local/bin/backend-entrypoint.sh
RUN chmod 0755 /usr/local/bin/backend-entrypoint.sh

# A non-root user runs the server
RUN useradd --system --no-create-home --uid 10001 trackside && chown -R trackside:trackside /app
USER trackside

EXPOSE 8000

ENTRYPOINT ["/usr/local/bin/backend-entrypoint.sh"]
# Daphne serves HTTP and WebSockets
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "config.asgi:application"]

# ---------------------------------------------------------------------------
# Stage 3: web (Caddy: HTTPS, the built frontend, proxy to the backend)
# ---------------------------------------------------------------------------
FROM caddy:2-alpine AS web

COPY Caddyfile /etc/caddy/Caddyfile
COPY --from=frontend /build/frontend/dist /srv
