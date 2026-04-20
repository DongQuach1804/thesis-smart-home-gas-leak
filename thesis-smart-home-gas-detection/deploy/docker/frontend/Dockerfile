FROM node:22.3.0-alpine

WORKDIR /app

COPY application/frontend/package*.json ./
RUN npm install 2>/dev/null || npm install

COPY application/frontend ./

EXPOSE 8080
CMD ["npm", "run", "start"]
