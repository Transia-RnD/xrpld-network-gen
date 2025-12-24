FROM nginx:latest

# Install curl for healthcheck
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

COPY vl.json /usr/share/nginx/html/vl.json

EXPOSE 80