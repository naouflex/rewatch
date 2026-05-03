# --- Stage 1: build the static site ----------------------------------------
FROM node:24-bookworm AS builder

WORKDIR /landing

# Install deps first so they're cached when only source files change.
COPY package.json ./
RUN npm install --no-audit --no-fund

# Copy the rest of the project and build.
COPY index.html vite.config.js ./
COPY public ./public
COPY src ./src
RUN npm run build

# --- Stage 2: serve via nginx ----------------------------------------------
FROM nginx:1.27-alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /landing/dist /usr/share/nginx/html

EXPOSE 80
