---
name: docker-composer
description: "Generate production-grade Dockerfiles and docker-compose configurations with multi-stage builds, security hardening, health checks, volume strategies, and network configuration."
category: coding
difficulty: intermediate
model_boost: "Weak models produce bloated images, missing security layers, or incorrect compose configurations"
---

# Docker Composer

## Purpose
This skill generates optimized, secure, and maintainable Docker and docker-compose configurations for containerized applications. It covers multi-stage builds to minimize image size, security hardening practices including rootless containers and minimal base images, health check implementation, sophisticated volume management strategies, and network configuration for inter-service communication. Output artifacts are production-ready and follow industry best practices.

## When to Use
- Creating Dockerfiles for new applications or services
- Setting up docker-compose for local development or staging environments
- Optimizing existing Docker images for size and security
- Implementing health checks and restart policies
- Configuring persistent data storage across container restarts
- Setting up service-to-service networking and communication
- **Do NOT use when**: Using Kubernetes exclusively (use K8s-specific manifests), or deploying to serverless platforms like Lambda

## Instructions

### Step 1: Analyze Application Type and Dependencies
Understand the application's technology stack, dependencies, and deployment requirements. Ask: Is this a Node.js, Python, Go, or compiled application? What are runtime dependencies vs. build-only dependencies? Does it need a database, cache layer, message queue? What are the security requirements (PCI, HIPAA)?

### Step 2: Design Multi-Stage Dockerfile Architecture
Build images in stages to separate build artifacts from runtime:

**Node.js Example:**
```dockerfile
# Stage 1: Build
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production && \
    npm run build
RUN npm ci --only=development && \
    npm test

# Stage 2: Runtime
FROM node:20-alpine
RUN apk add --no-cache dumb-init
WORKDIR /app
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./
EXPOSE 3000
ENTRYPOINT ["/usr/sbin/dumb-init", "--"]
CMD ["node", "dist/server.js"]
```

**Python Example:**
```dockerfile
# Stage 1: Build
FROM python:3.11-slim AS builder
WORKDIR /app
COPY requirements.txt .
RUN python -m venv /opt/venv && \
    /opt/venv/bin/pip install --no-cache-dir -r requirements.txt

# Stage 2: Runtime
FROM python:3.11-slim
RUN useradd -m -u 1000 appuser
WORKDIR /app
COPY --from=builder /opt/venv /opt/venv
COPY . .
USER appuser
ENV PATH="/opt/venv/bin:$PATH"
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0"]
```

### Step 3: Implement Security Hardening
Apply defense-in-depth security practices:

```dockerfile
# Use specific Alpine version, not 'latest'
FROM python:3.11.8-alpine

# Run as non-root user
RUN addgroup -g 1001 appgroup && \
    adduser -D -u 1001 -G appgroup appuser

# Remove unnecessary packages
RUN apk del apk-tools apk-tools-static && \
    rm -rf /var/cache/apk/*

# Use read-only filesystem where possible
RUN chmod 555 /etc/passwd /etc/group

# Copy with proper permissions
COPY --chown=appuser:appgroup . .

USER appuser
```

### Step 4: Configure Health Checks
Implement container health monitoring:

```dockerfile
# For HTTP services
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:3000/health || exit 1

# For process-based services
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD ps aux | grep "[n]ode" || exit 1

# Custom health check script
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD /app/healthcheck.sh
```

**healthcheck.sh example:**
```bash
#!/bin/sh
set -e
STATUS=$(curl -s -w "%{http_code}" -o /dev/null http://localhost:8000/api/health)
if [ "$STATUS" = "200" ]; then
  exit 0
else
  exit 1
fi
```

### Step 5: Design Volume Strategy
Define persistent storage and data sharing:

```yaml
# docker-compose.yml
services:
  postgres:
    image: postgres:16-alpine
    volumes:
      # Named volume for data persistence
      - postgres_data:/var/lib/postgresql/data
      # Initialization scripts
      - ./init-db.sql:/docker-entrypoint-initdb.d/init.sql:ro
    environment:
      POSTGRES_PASSWORD_FILE: /run/secrets/db_password

  app:
    image: myapp:latest
    volumes:
      # Bind mount for development (local path:container path)
      - ./src:/app/src
      # Volume mount for logs
      - app_logs:/app/logs
      # Temporary storage
      - /tmp:/tmp
    depends_on:
      postgres:
        condition: service_healthy

  cache:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes

volumes:
  postgres_data:
    driver: local
  redis_data:
    driver: local
  app_logs:
    driver: local
```

### Step 6: Configure Service Networking and Communication
Set up inter-service communication patterns:

```yaml
services:
  frontend:
    image: web-ui:latest
    ports:
      - "80:3000"
    networks:
      - frontend
    environment:
      API_URL: http://api:3000

  api:
    image: api-server:latest
    networks:
      - frontend
      - backend
    depends_on:
      - postgres
    expose:
      - "3000"

  postgres:
    image: postgres:16-alpine
    networks:
      - backend
    environment:
      POSTGRES_HOST_AUTH_METHOD: trust

  worker:
    image: worker-service:latest
    networks:
      - backend
    depends_on:
      - postgres
      - rabbitmq

  rabbitmq:
    image: rabbitmq:3.12-management-alpine
    networks:
      - backend
    ports:
      - "15672:15672"

networks:
  frontend:
    driver: bridge
  backend:
    driver: bridge
```

### Step 7: Optimize and Document Build Configuration
Create .dockerignore and build optimization:

```
# .dockerignore
node_modules/
npm-debug.log
.git
.gitignore
.env
.env.local
dist/
build/
.DS_Store
*.log
.vscode/
.idea/
__pycache__/
*.pyc
.pytest_cache/
.coverage
venv/
```

**Build script with caching:**
```bash
#!/bin/bash
docker build \
  --tag myapp:latest \
  --tag myapp:$(git rev-parse --short HEAD) \
  --build-arg BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ') \
  --build-arg VCS_REF=$(git rev-parse --short HEAD) \
  --file Dockerfile \
  .
```

## Output Template

```yaml
# Dockerfile for {{application_type}}
FROM {{base_image}} AS builder
WORKDIR /app
COPY {{build_dependencies}} .
RUN {{build_commands}}

FROM {{runtime_base_image}}
RUN {{security_setup}}
WORKDIR /app
COPY --from=builder {{copy_commands}}
USER {{non_root_user}}
HEALTHCHECK {{health_check_config}}
EXPOSE {{ports}}
CMD {{start_command}}

---
# docker-compose.yml
version: '3.9'
services:
  {{service_name}}:
    image: {{image_name}}:{{tag}}
    build:
      context: .
      dockerfile: Dockerfile
      args:
        - BUILD_ARG={{value}}
    ports:
      - "{{external_port}}:{{internal_port}}"
    volumes:
      - {{volume_config}}
    environment:
      - {{env_vars}}
    networks:
      - {{network_name}}
    depends_on:
      {{dependencies}}
    restart: {{restart_policy}}

volumes:
  {{volume_definitions}}

networks:
  {{network_definitions}}
```

## Quality Gates
- [ ] Dockerfile uses multi-stage builds with clear separation of build and runtime stages
- [ ] Base images are pinned to specific versions (not 'latest'), prefer Alpine/distroless
- [ ] Application runs as non-root user with explicit USER directive
- [ ] All services have HEALTHCHECK configured with appropriate intervals
- [ ] docker-compose includes proper depends_on conditions (service_healthy)
- [ ] Volumes are named (not anonymous) and include access mode specifications
- [ ] Networks are explicitly defined with bridge driver where needed
- [ ] .dockerignore file excludes unnecessary files (node_modules, .git, etc.)

## Examples

### Good Output (excerpt)
```dockerfile
# Node.js API Server - Production Ready
FROM node:20.11.0-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci && npm run build

FROM node:20.11.0-alpine
RUN apk add --no-cache curl
RUN addgroup -g 1001 nodejs && adduser -D -u 1001 -G nodejs nodejs
WORKDIR /app
COPY --from=builder --chown=nodejs:nodejs /app/dist ./dist
COPY --from=builder --chown=nodejs:nodejs /app/node_modules ./node_modules
USER nodejs
HEALTHCHECK --interval=30s --timeout=3s CMD curl -f http://localhost:3000/health || exit 1
EXPOSE 3000
CMD ["node", "dist/server.js"]
```

### Bad Output (what to avoid)
```dockerfile
FROM node:latest
WORKDIR /app
COPY . .
RUN npm install
EXPOSE 3000
CMD ["npm", "start"]
# Problems: runs as root, uses 'latest' tag, no health check,
# includes node_modules and dev dependencies, no multi-stage
```

## Common Mistakes

1. **Bloated Images from Missing .dockerignore**: Including node_modules, .git, and build artifacts in the final image. Results in 500MB+ images when 50MB is possible. Solution: Create comprehensive .dockerignore file.

2. **Running as Root User**: Default behavior executes all processes as root (UID 0), creating security vulnerability. If container is compromised, attacker has full system access. Solution: Create non-root user with `RUN adduser -D -u 1000 appuser` and `USER appuser`.

3. **Using 'latest' Tag**: Base images updated without notice break reproducibility. Your production app suddenly behaves differently with Ubuntu 22.04 instead of 20.04. Solution: Pin versions: `FROM python:3.11.8-alpine`, not `FROM python:3.11-alpine`.

4. **Missing Health Checks**: Container appears running but application is deadlocked or crashed. Orchestrators can't detect and restart it automatically. Solution: Implement HEALTHCHECK for all services.

5. **Incorrect depends_on Without Conditions**: Services start in order but don't wait for dependencies to be healthy. Application connects to empty database. Solution: Use `depends_on: { service: { condition: service_healthy } }`.

## Anti-Patterns

1. **Single Monolithic Dockerfile**: Thousands of lines with every tool and language included. Image size bloats, attack surface expands, caching becomes ineffective. Use multi-stage builds to separate concerns.

2. **Volume Mounts Without Read-Only**: Mounting entire /app directory as read-write allows container to modify code during runtime, breaking immutability. Use `:ro` flag for config: `- ./config:/app/config:ro`

3. **No Network Isolation**: All services on default bridge network, exposing internal communication. Use explicit networks: frontend services on one network, backend on another, separate databases.

4. **ENV Secrets in Dockerfile**: Hardcoding API keys or passwords in ENV directives leaves them in image history. Use secrets management: `docker run --secret my_secret` or compose `secrets:` section.

5. **Ignoring Image Size During Development**: Building 2GB Docker images to save 30 minutes of development time. Increases CI/CD time by hours, slows deployments, costs storage. Use Alpine images and multi-stage builds even in development.
