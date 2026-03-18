FROM python:3.11-slim

# Nginx + htpasswd ユーティリティをインストール
RUN apt-get update && apt-get install -y nginx apache2-utils && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Python 依存関係を先にインストール（キャッシュ効率化）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chmod +x /app/start.sh

EXPOSE 10000

CMD ["/app/start.sh"]
