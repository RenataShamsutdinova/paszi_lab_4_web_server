#этап сборки React-приложения
FROM node:24-alpine AS build

WORKDIR /app

COPY package*.json ./

RUN npm install

COPY . .

RUN npm run build


#этап запуска приложения через Nginx
FROM nginx:alpine

COPY --from=build /app/dist /usr/share/nginx/html

#копируем конфиг файл внутрь Nginx, чтоб он работал
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

