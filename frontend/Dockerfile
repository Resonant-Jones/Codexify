# syntax=docker/dockerfile:1.6
ARG NODE_IMAGE=node:20-alpine
FROM ${NODE_IMAGE}

WORKDIR /app

# Pin pnpm; v10 works great with Node 20 & Vite 7
RUN corepack enable && corepack prepare pnpm@10.18.2 --activate

# Toolchain for any native modules (safe to keep)
RUN apk add --no-cache python3 make g++ linux-headers

COPY src/package.json ./src/package.json
# Lockfile is optional in this repo layout; don't fail the Docker build if it isn't present.
RUN pnpm --dir src install --include=dev

# Now copy the app source
COPY src ./src

# Vite dev port
ENV VITE_DEV_PORT=5173
EXPOSE 5173

# Dev server entry
CMD ["sh","-lc","cd /app/src && npx vite dev --host 0.0.0.0 --port ${VITE_DEV_PORT:-5173}"]
