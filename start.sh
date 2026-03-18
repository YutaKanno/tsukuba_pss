#!/bin/bash
set -e

PORT=${PORT:-10000}

echo "[start.sh] PORT=$PORT"

# Nginx 設定を生成（PORT を環境変数から注入）
cat > /etc/nginx/nginx.conf << NGINX_EOF
worker_processes 1;

events {
    worker_connections 1024;
}

http {
    # Basic Auth のユーザー名に日本語を使うため UTF-8 設定
    charset utf-8;

    server {
        listen ${PORT};

        auth_basic "Tsukuba PSS";
        auth_basic_user_file /etc/nginx/.htpasswd;

        location / {
            proxy_pass http://127.0.0.1:8501;

            # 認証済みユーザー名を Streamlit に転送
            proxy_set_header X-Remote-User \$remote_user;

            # WebSocket サポート（Streamlit に必須）
            proxy_http_version 1.1;
            proxy_set_header Upgrade \$http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_set_header Host \$host;
            proxy_read_timeout 86400;
        }
    }
}
NGINX_EOF

# BASIC_AUTH_USERS または INITIAL_TEAM_PASSWORDS から .htpasswd を生成
python3 /app/scripts/generate_htpasswd.py

# Streamlit をバックグラウンドで起動
streamlit run /app/main.py \
    --server.port 8501 \
    --server.address 127.0.0.1 \
    --server.headless true \
    --server.enableCORS false \
    --server.enableXsrfProtection false &

# Streamlit の起動を待機
echo "[start.sh] Waiting for Streamlit to start..."
sleep 5

# Nginx をフォアグラウンドで起動
echo "[start.sh] Starting Nginx on port ${PORT}"
exec nginx -g 'daemon off;'
