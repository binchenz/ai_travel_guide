#!/bin/bash
# =============================================================
# Shanghai Museum AI Guide — One-click server deploy script
# Usage: bash deploy.sh [OPENAI_API_KEY]
# =============================================================
set -e

OPENAI_KEY="${1:-}"
APP_DIR="/root/ai_travel_guide"
BACKEND_DIR="$APP_DIR/backend"
FRONTEND_DIR="$APP_DIR/frontend"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
log()  { echo -e "${GREEN}[deploy]${NC} $*"; }
warn() { echo -e "${YELLOW}[warn]${NC} $*"; }
die()  { echo -e "${RED}[error]${NC} $*"; exit 1; }

log "=== 上海博物馆 AI 导览 — 服务器部署 ==="

# ── 系统依赖 ────────────────────────────────────────────────
log "1/7 检查系统依赖…"
if command -v yum &>/dev/null; then
    yum install -y python3 python3-pip git nginx 2>/dev/null | tail -2
    if ! command -v node &>/dev/null; then
        curl -fsSL https://rpm.nodesource.com/setup_20.x | bash - 2>/dev/null | tail -2
        yum install -y nodejs 2>/dev/null | tail -2
    fi
elif command -v apt-get &>/dev/null; then
    apt-get update -qq && apt-get install -y python3 python3-pip python3-venv git nginx 2>/dev/null | tail -2
    if ! command -v node &>/dev/null; then
        curl -fsSL https://deb.nodesource.com/setup_20.x | bash - 2>/dev/null | tail -2
        apt-get install -y nodejs 2>/dev/null | tail -2
    fi
fi
log "  node $(node -v)  python3 $(python3 --version)  nginx $(nginx -v 2>&1 | cut -d/ -f2)"

# ── 后端 venv + 依赖 ─────────────────────────────────────────
log "2/7 安装后端 Python 依赖…"
cd "$BACKEND_DIR"
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt \
    -i https://pypi.tuna.tsinghua.edu.cn/simple \
    --quiet 2>&1 | tail -3
deactivate
log "  后端依赖安装完成"

# ── 前端构建 ─────────────────────────────────────────────────
log "3/7 构建前端…"
cd "$FRONTEND_DIR"

# 把 API_BASE_URL 指向同域（nginx 会做反向代理）
sed -i 's|const API_BASE_URL = "http://127.0.0.1:8080"|const API_BASE_URL = ""|g' src/App.tsx 2>/dev/null || true

npm install --registry=https://registry.npmmirror.com 2>&1 | tail -3
npm run build 2>&1 | tail -5
log "  前端构建完成 → $FRONTEND_DIR/dist"

# ── 环境变量 ─────────────────────────────────────────────────
log "4/7 写入环境变量…"
cat > "$BACKEND_DIR/.env" <<ENV
VOLCANO_APP_KEY=1724131082
VOLCANO_ACCESS_TOKEN=0QTUBjVNQcXYIT0wvkHveeJUymhtPsZq
VOLCANO_SECRET_KEY=Ux06WLrByMb1w1tBNKG4yiyjCxe-H6O8
CORS_ORIGINS=*
OPENAI_API_KEY=${OPENAI_KEY}
OPENAI_BASE_URL=https://api.moonshot.cn/v1
MODEL_NAME=kimi-k2-turbo-preview
VOICE_TTS_BACKEND=edge
ENV
log "  .env 写入完成"

# ── systemd 服务 ─────────────────────────────────────────────
log "5/7 配置 systemd 后端服务…"
cat > /etc/systemd/system/ai-guide.service <<SERVICE
[Unit]
Description=Shanghai Museum AI Guide Backend
After=network.target

[Service]
User=root
WorkingDirectory=${BACKEND_DIR}
ExecStart=${BACKEND_DIR}/venv/bin/python -m uvicorn main:app --host 127.0.0.1 --port 8080
EnvironmentFile=${BACKEND_DIR}/.env
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
SERVICE

systemctl daemon-reload
systemctl enable ai-guide
systemctl restart ai-guide
sleep 3
systemctl is-active ai-guide >/dev/null 2>&1 && log "  后端服务启动成功 ✓" || die "后端服务启动失败，运行 journalctl -u ai-guide -n 30 查看日志"

# ── nginx ────────────────────────────────────────────────────
log "6/7 配置 nginx…"
# 关闭 nginx 默认站点
[ -f /etc/nginx/sites-enabled/default ] && rm -f /etc/nginx/sites-enabled/default 2>/dev/null || true
[ -f /etc/nginx/conf.d/default.conf ]   && rm -f /etc/nginx/conf.d/default.conf   2>/dev/null || true

cat > /etc/nginx/conf.d/ai-guide.conf <<NGINX
server {
    listen 80 default_server;
    server_name _;

    root ${FRONTEND_DIR}/dist;
    index index.html;

    # SPA 路由回落
    location / {
        try_files \$uri \$uri/ /index.html;
    }

    # 后端 API（TTS / ASR / chat / exhibits / ontology / voice）
    location ~ ^/(tts|asr|chat|exhibits|ontology|voice|api) {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "";
        proxy_read_timeout 90s;
        proxy_send_timeout 90s;
    }

    # SSE 流式响应（chat/stream）
    location /chat/stream {
        proxy_pass http://127.0.0.1:8080/chat/stream;
        proxy_set_header Host \$host;
        proxy_http_version 1.1;
        proxy_set_header Connection "";
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 300s;
    }
}
NGINX

nginx -t 2>&1 && log "  nginx 配置验证通过 ✓"
systemctl enable nginx
systemctl restart nginx
log "  nginx 重启成功 ✓"

# ── 防火墙开放 80 ─────────────────────────────────────────────
log "7/7 开放端口…"
if command -v firewall-cmd &>/dev/null; then
    firewall-cmd --permanent --add-service=http 2>/dev/null || true
    firewall-cmd --reload 2>/dev/null || true
fi
# iptables fallback
iptables -I INPUT -p tcp --dport 80 -j ACCEPT 2>/dev/null || true

# ── 健康检查 ─────────────────────────────────────────────────
log ""
log "=== 部署完成，验证中… ==="
sleep 2

BACKEND_OK=$(curl -sf http://127.0.0.1:8080/voice/health 2>/dev/null && echo "ok" || echo "fail")
FRONTEND_OK=$(curl -sf http://127.0.0.1:80/ 2>/dev/null | grep -c "html" || echo "0")

echo ""
if [[ "$BACKEND_OK" == "ok" ]]; then
    log "✓ 后端 API 健康"
else
    warn "✗ 后端 API 异常 — journalctl -u ai-guide -n 30"
fi

if [[ "$FRONTEND_OK" -gt "0" ]]; then
    log "✓ 前端页面正常"
else
    warn "✗ 前端页面异常 — nginx -t && systemctl status nginx"
fi

echo ""
echo -e "${GREEN}=============================================="
echo -e "  🎉 访问地址：http://$(curl -s ifconfig.me 2>/dev/null || echo '47.97.225.14')"
echo -e "==============================================${NC}"
