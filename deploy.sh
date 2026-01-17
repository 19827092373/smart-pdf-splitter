#!/bin/bash

# 智能PDF切分工具 - 阿里云服务器部署脚本

set -e

echo "🚀 智能PDF切分工具 - 阿里云服务器部署"
echo "======================================"

# 检查是否为 root 用户
if [ "$EUID" -ne 0 ]; then 
    echo "⚠️  建议使用 root 用户运行此脚本"
    read -p "是否继续？(y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# 检查 Docker 是否安装
if ! command -v docker &> /dev/null; then
    echo "📦 正在安装 Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    rm get-docker.sh
    systemctl start docker
    systemctl enable docker
    echo "✅ Docker 安装完成"
else
    echo "✅ Docker 已安装"
fi

# 检查 Docker Compose
if ! command -v docker-compose &> /dev/null; then
    echo "📦 正在安装 Docker Compose..."
    curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
    echo "✅ Docker Compose 安装完成"
else
    echo "✅ Docker Compose 已安装"
fi

echo ""
echo "🔧 开始部署应用..."

# 检查是否存在 docker-compose.yml
if [ ! -f "docker-compose.yml" ]; then
    echo "❌ 错误: 未找到 docker-compose.yml 文件"
    echo "   请确保在项目根目录运行此脚本"
    exit 1
fi

# 构建并启动
echo "📦 构建 Docker 镜像..."
docker-compose build

echo "🚀 启动容器..."
docker-compose up -d

echo ""
echo "✅ 部署完成！"
echo ""
echo "📊 服务状态:"
docker-compose ps

echo ""
echo "📝 常用命令:"
echo "  查看日志: docker-compose logs -f"
echo "  重启服务: docker-compose restart"
echo "  停止服务: docker-compose down"
echo "  更新代码: git pull && docker-compose up -d --build"
echo ""
echo "🌐 应用地址: http://$(hostname -I | awk '{print $1}'):8501"
echo "   或访问: http://your-server-ip:8501"
echo ""

# 检查防火墙
if command -v ufw &> /dev/null; then
    echo "🔒 检查防火墙..."
    if ufw status | grep -q "8501"; then
        echo "✅ 端口 8501 已开放"
    else
        echo "⚠️  端口 8501 未开放，正在开放..."
        ufw allow 8501/tcp
        echo "✅ 端口 8501 已开放"
    fi
elif command -v firewall-cmd &> /dev/null; then
    echo "🔒 检查防火墙..."
    if firewall-cmd --list-ports | grep -q "8501"; then
        echo "✅ 端口 8501 已开放"
    else
        echo "⚠️  端口 8501 未开放，正在开放..."
        firewall-cmd --permanent --add-port=8501/tcp
        firewall-cmd --reload
        echo "✅ 端口 8501 已开放"
    fi
fi

echo ""
echo "✨ 部署完成！请确保在阿里云安全组中开放 8501 端口"
