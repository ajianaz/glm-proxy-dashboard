# Build stage
FROM oven/bun:1 AS build
WORKDIR /app
COPY package.json bun.lock ./
RUN bun install --frozen-lockfile
COPY . .
ARG VITE_API_BASE=https://glm.ajianaz.dev
ENV VITE_API_BASE=$VITE_API_BASE
RUN bun run build

# Serve stage
FROM caddy:2-alpine
COPY --from=build /app/dist /srv
COPY Caddyfile /etc/caddy/Caddyfile
EXPOSE 80
