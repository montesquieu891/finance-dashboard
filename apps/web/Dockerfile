FROM node:20-alpine AS build

WORKDIR /app

COPY package.json ./
COPY tsconfig.json vite.config.ts tailwind.config.ts postcss.config.cjs index.html eslint.config.js ./
COPY src ./src

RUN corepack enable \
    && corepack pnpm install --no-frozen-lockfile --ignore-workspace \
    && corepack pnpm build

FROM nginx:1.27-alpine AS runtime

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]