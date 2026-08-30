# Stage 1: Build Angular SPA using Bun
FROM oven/bun:1.2-alpine AS builder

WORKDIR /app

# Copy root workspace configurations and dependency lockfile
COPY package.json bun.lock nx.json tsconfig.base.json ./

# Install dependencies
RUN bun install --frozen-lockfile

# Copy frontend application sources
COPY apps/frontend ./apps/frontend

# Build frontend production bundle
RUN bunx nx build frontend --configuration=production

# Stage 2: Production Nginx Server
FROM nginx:alpine

# Copy built static SPA assets from builder stage
COPY --from=builder /app/dist/apps/frontend/browser /usr/share/nginx/html

# Copy custom reverse proxy & SSL Nginx configuration
COPY apps/frontend/nginx.conf /etc/nginx/conf.d/default.conf

# Expose standard HTTP and HTTPS ports
EXPOSE 80 443

CMD ["nginx", "-g", "daemon off;"]
