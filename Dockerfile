FROM node:24-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY index.html vite.config.js ./
COPY src ./src
COPY public ./public
RUN npm run build
FROM nginx:alpine
LABEL org.opencontainers.image.source="https://github.com/mdriverpl/perlylubuskie.pl"
LABEL org.opencontainers.image.description="Perły Ziemi Lubuskiej — Vue frontend and Nginx reverse proxy"
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
