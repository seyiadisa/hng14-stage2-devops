FROM node:25-alpine AS deps

WORKDIR /app

COPY package.json ./
RUN npm install --omit=dev


FROM node:25-alpine AS runtime

ENV NODE_ENV=production

RUN addgroup -S app && adduser -S app -G app

WORKDIR /app

COPY --from=deps /app/node_modules ./node_modules
COPY package.json app.js ./
COPY views ./views

USER app

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD node -e "const http=require('http'); const port=process.env.PORT || 3000; const req=http.get({host:'127.0.0.1', port, path:'/health', timeout:3000}, (res) => process.exit(res.statusCode === 200 ? 0 : 1)); req.on('error', () => process.exit(1)); req.on('timeout', () => { req.destroy(); process.exit(1); });"

CMD ["node", "app.js"]
