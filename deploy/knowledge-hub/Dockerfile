FROM nginx:alpine

RUN rm -rf /usr/share/nginx/html/*

COPY site/ /usr/share/nginx/html/
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 8080
