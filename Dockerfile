# RAPR AI — server image. Runs headless: chat apps, the web UI, schedules and
# group chats work; the tray, desktop Kelvin and computer use are Windows-only.
#
#   docker build -t raprai .
#   docker run -p 8000:8000 -v raprai-data:/data raprai
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    RAPR_HEADLESS=1 \
    RAPR_DATA_DIR=/data \
    WEB_HOST=0.0.0.0 \
    WEB_PORT=8000

# git: AIs and bake-off work on repositories. nodejs/npm: the Node-based AI CLIs.
# curl: the health check.
RUN apt-get update \
 && apt-get install -y --no-install-recommends git curl ca-certificates nodejs npm ffmpeg \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements-server.txt ./
RUN pip install --no-cache-dir -r requirements-server.txt

COPY . .
RUN useradd --create-home rapr \
 && mkdir -p /data \
 && chown -R rapr:rapr /data /app
USER rapr

VOLUME ["/data"]
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
  CMD curl -fsS http://127.0.0.1:8000/health || exit 1

CMD ["python", "web_app.py"]
