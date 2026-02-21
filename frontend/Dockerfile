FROM node:22-alpine

WORKDIR /app

# 依存関係インストール
COPY package.json package-lock.json ./
RUN npm install

# アプリケーションコピー
COPY . .

# 開発サーバー起動
CMD ["npm", "run", "dev"]
