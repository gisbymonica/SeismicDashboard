FROM node:22-alpine AS build
WORKDIR /app

# Use package-lock for reproducible installs
COPY package*.json ./
RUN npm ci

# Copy source and build
COPY . .
RUN npm run build

FROM nginx:1.27-alpine
# Copy built assets to nginx
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Ensure nginx serves files as non-root user where possible
RUN chown -R nginx:nginx /usr/share/nginx/html

EXPOSE 80
USER nginx

