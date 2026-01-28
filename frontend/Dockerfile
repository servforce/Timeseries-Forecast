# Build stage
FROM node:20-alpine AS build
WORKDIR /app

COPY package.json /app/package.json
RUN npm install

COPY . /app
ARG VITE_API_BASE_URL=http://localhost:5001
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
RUN npm run build

# Runtime stage
FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]

