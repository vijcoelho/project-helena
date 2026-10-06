# The site is static: nginx serves site/ as is.
FROM nginx:1.27-alpine
COPY site/ /usr/share/nginx/html/
EXPOSE 80
HEALTHCHECK CMD wget -qO- http://127.0.0.1/ >/dev/null || exit 1
