#!/usr/bin/env python3
"""
BASIC_AUTH_USERS または INITIAL_TEAM_PASSWORDS 環境変数から
/etc/nginx/.htpasswd を生成する。

環境変数の形式（JSON）:
    {"チーム名": "パスワード", "筑波大学": "password2", ...}

.htpasswd は {SHA} 形式（SHA-1 + Base64）で生成する。
Nginx の auth_basic モジュールはこの形式をサポートしている。
"""
import base64
import hashlib
import json
import os
import sys

raw = os.environ.get("BASIC_AUTH_USERS") or os.environ.get("INITIAL_TEAM_PASSWORDS", "")

try:
    users: dict = json.loads(raw.strip()) if raw.strip() else {}
except Exception as e:
    print(f"[generate_htpasswd] 環境変数のパースに失敗: {e}", file=sys.stderr)
    users = {}

if not users:
    print("[generate_htpasswd] 警告: BASIC_AUTH_USERS が未設定のため .htpasswd は空になります", file=sys.stderr)

lines = []
for username, password in users.items():
    digest = hashlib.sha1(password.encode("utf-8")).digest()
    b64 = base64.b64encode(digest).decode("ascii")
    lines.append(f"{username}:{{SHA}}{b64}")

out_path = "/etc/nginx/.htpasswd"
with open(out_path, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))
    if lines:
        f.write("\n")

print(f"[generate_htpasswd] {len(lines)} ユーザーを {out_path} に書き込みました")
