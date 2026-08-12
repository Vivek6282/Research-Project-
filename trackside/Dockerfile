# Trackside — Multi-Stage Production Dockerfile
# Backend: Django + Daphne ASGI WebSocket server

FROM python:3.14-slim as backend

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python requirements
COPY backend/requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt daphne gunicorn

# Copy backend application source
COPY backend/ /app/

EXPOSE 8000

# Run Daphne ASGI server for HTTP & WebSockets
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "config.asgi:application"]
