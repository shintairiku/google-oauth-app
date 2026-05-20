FROM oven/bun:1.3.9-alpine

WORKDIR /app

COPY package.json bun.lock /app/
RUN bun install --frozen-lockfile

COPY . /app

EXPOSE 3000

CMD ["bun", "run", "dev"]
