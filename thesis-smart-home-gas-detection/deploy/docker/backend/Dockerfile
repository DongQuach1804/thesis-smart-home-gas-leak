FROM node:22.3.0-alpine

WORKDIR /app

# Install dependencies (use npm install instead of npm ci so no lockfile is required)
COPY application/backend/package*.json ./
RUN npm install --omit=dev 2>/dev/null || npm install

# Copy source and build TypeScript
COPY application/backend ./
RUN npm run build

EXPOSE 3000
CMD ["npm", "run", "start"]
