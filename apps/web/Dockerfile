FROM node:20-alpine AS build

WORKDIR /app

COPY package.json ./
COPY tsconfig.json vite.config.ts tailwind.config.ts postcss.config.cjs index.html eslint.config.js ./
COPY src ./src

RUN corepack enable \
    && corepack pnpm install --no-frozen-lockfile --ignore-workspace \
    && corepack pnpm build

FROM nginx:1.27-alpine AS runtime

RUN apk add --no-cache gettext

COPY nginx.conf.template /etc/nginx/templates/default.conf.template
COPY start-nginx.sh /start-nginx.sh
RUN chmod +x /start-nginx.sh

COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["/start-nginx.sh"]