#!/bin/bash

# 本地代码同步到服务器脚本
# 使用方法: 修改下面的服务器信息，然后运行 ./sync.sh

set -e

# ========== 配置区域 ==========
# 修改为你的服务器信息
SERVER="root@your-server-ip"
REMOTE_DIR="/opt/smart-pdf-splitter"
# =============================

LOCAL_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo "🔄 同步代码到服务器"
echo "=================="
echo "服务器: $SERVER"
echo "远程目录: $REMOTE_DIR"
echo "本地目录: $LOCAL_DIR"
echo ""

# 检查服务器连接
echo "🔍 检查服务器连接..."
if ! ssh -o ConnectTimeout=5 $SERVER "echo '连接成功'" &> /dev/null; then
    echo "❌ 无法连接到服务器: $SERVER"
    echo "   请检查:"
    echo "   1. 服务器 IP 是否正确"
    echo "   2. SSH 密钥是否配置"
    echo "   3. 网络是否通畅"
    exit 1
fi

echo "✅ 服务器连接正常"
echo ""

# 同步文件
echo "📤 同步文件到服务器..."
rsync -avz --progress \
    --exclude '.git' \
    --exclude '__pycache__' \
    --exclude '*.pyc' \
    --exclude '.streamlit/secrets.toml' \
    --exclude 'venv' \
    --exclude 'env' \
    --exclude '*.pdf' \
    --exclude '*.zip' \
    --exclude '.DS_Store' \
    --exclude 'Thumbs.db' \
    --exclude 'test_*.py' \
    "$LOCAL_DIR/" "$SERVER:$REMOTE_DIR/"

echo ""
echo "✅ 文件同步完成"
echo ""

# 询问是否重启服务
read -p "是否重启服务器上的服务？(y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🔄 重启服务..."
    ssh $SERVER "cd $REMOTE_DIR && docker-compose restart 2>/dev/null || sudo systemctl restart pdf-splitter 2>/dev/null || echo '请手动重启服务'"
    echo "✅ 服务重启完成"
fi

echo ""
echo "✨ 同步完成！"
echo "🌐 访问: http://$(echo $SERVER | cut -d'@' -f2):8501"
