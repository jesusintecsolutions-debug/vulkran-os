FROM node:20-slim

WORKDIR /app/remotion

RUN apt-get update && apt-get install -y --no-install-recommends \
    chromium \
    && rm -rf /var/lib/apt/lists/*

ENV PUPPETEER_SKIP_CHROMIUM_DOWNLOAD=true
ENV CHROMIUM_PATH=/usr/bin/chromium

COPY package.json package-lock.json* ./
RUN npm install --production=false

COPY . .

RUN npx remotion bundle --public-dir=public 2>/dev/null || true

CMD ["tail", "-f", "/dev/null"]
