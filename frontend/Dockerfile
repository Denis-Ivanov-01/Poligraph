FROM node:22-slim

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm install --include=optional --no-package-lock

COPY . .

EXPOSE 5173

CMD ["npm", "run", "dev"]
