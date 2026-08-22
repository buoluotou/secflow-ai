# Base images are configurable for offline/mirror-registry environments
# (see docker-compose.yml NODE_IMAGE / NGINX_IMAGE variables).
# ARGs must be declared before the first FROM to be visible to later FROMs.
ARG NODE_IMAGE=node:20-alpine
ARG NGINX_IMAGE=nginx:1.27-alpine
ARG NPM_REGISTRY=https://registry.npmjs.org
FROM ${NODE_IMAGE} AS build
WORKDIR /app
COPY frontend/package.json ./
RUN npm install --registry=${NPM_REGISTRY}
COPY frontend/ ./
RUN npm run build

FROM ${NGINX_IMAGE}
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
