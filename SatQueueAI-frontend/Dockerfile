# SatQuery AI — Frontend Dockerfile (Next.js 14+ Production)
# Build context root: the SatQueueAI-frontend directory.
FROM node:20-alpine AS base
WORKDIR /app

# Install dependencies (leverages Docker layer caching)
FROM base AS deps
COPY package.json package-lock.json* ./
RUN npm install --legacy-peer-deps

# Build production assets
FROM deps AS builder
COPY . .
RUN npm run build

# Production image
FROM base AS runner
ENV NODE_ENV=production
ENV PORT=3000

COPY --from=deps /app/node_modules ./node_modules
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/public ./public
COPY --from=builder /app/next.config.ts ./
COPY --from=builder /app/next-env.d.ts ./
COPY --from=builder /app/tsconfig.json ./
COPY --from=builder /app/package.json ./

EXPOSE 3000
CMD ["npm", "start"]
