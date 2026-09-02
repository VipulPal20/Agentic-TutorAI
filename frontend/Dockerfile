# --- Stage 1: build the Vite bundle -----------------------------------------
FROM node:20-alpine AS build

WORKDIR /app

# Copy manifests first so dependency installs cache independently of source.
COPY package.json package-lock.json* ./
# `npm ci` when a lockfile exists (reproducible), otherwise fall back.
RUN if [ -f package-lock.json ]; then npm ci; else npm install; fi

COPY . .

# Same origin in production: nginx serves the bundle and proxies the API,
# so no base URL is needed.
ENV VITE_API_BASE=""
RUN npm run build

# --- Stage 2: serve it -------------------------------------------------------
FROM nginx:1.27-alpine AS runtime

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD wget -qO- http://localhost/ >/dev/null 2>&1 || exit 1

CMD ["nginx", "-g", "daemon off;"]
