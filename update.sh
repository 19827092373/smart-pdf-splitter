#!/bin/bash

# 智能PDF切分工具 - 代码更新脚本

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo "🔄 智能PDF切分工具 - 代码更新"
echo "=============================="
echo ""

# 检测部署方式
if [ -f "docker-compose.yml" ] && command -v docker-compose &> /dev/null; then
    DEPLOY_MODE="docker"
elif [ -f "/etc/systemd/system/pdf-splitter.service" ]; then
    DEPLOY_MODE="systemd"
else
    DEPLOY_MODE="unknown"
fi

echo "📦 检测到部署方式: $DEPLOY_MODE"
echo ""

# 更新方式
UPDATE_MODE=${1:-"git"}

case $UPDATE_MODE in
    git)
        echo "📥 方式: Git 拉取更新"
        echo ""
        
        # 检查是否在 Git 仓库中
        if [ ! -d ".git" ]; then
            echo "❌ 错误: 当前目录不是 Git 仓库"
            echo "   请先初始化 Git 仓库或使用其他更新方式"
            exit 1
        fi
        
        # 检查是否有未提交的更改
        if [ -n "$(git status --porcelain)" ]; then
            echo "⚠️  警告: 检测到未提交的更改"
            read -p "是否继续？可能会丢失本地更改 (y/n): " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                exit 1
            fi
            git stash
        fi
        
        # 拉取最新代码
        echo "📥 拉取最新代码..."
        git pull origin main 2>/dev/null || git pull origin master 2>/dev/null || {
            echo "❌ Git 拉取失败"
            echo "   请检查网络连接和 Git 配置"
            exit 1
        }
        
        echo "✅ 代码拉取完成"
        ;;
        
    restart)
        echo "🔄 方式: 仅重启服务（代码已手动上传）"
        ;;
        
    full)
        echo "🚀 方式: 完整更新（Git + 构建 + 重启）"
        echo ""
        
        # 先执行 Git 更新
        if [ -d ".git" ]; then
            if [ -n "$(git status --porcelain)" ]; then
                git stash
            fi
            git pull origin main 2>/dev/null || git pull origin master 2>/dev/null
        else
            echo "⚠️  警告: 未检测到 Git 仓库，跳过代码拉取"
        fi
        ;;
        
    *)
        echo "❌ 未知的更新方式: $UPDATE_MODE"
        echo ""
        echo "用法:"
        echo "  ./update.sh git      - Git 拉取更新（默认）"
        echo "  ./update.sh restart  - 仅重启服务"
        echo "  ./update.sh full     - 完整更新"
        exit 1
        ;;
esac

echo ""

# 根据部署方式执行更新
case $DEPLOY_MODE in
    docker)
        echo "🐳 使用 Docker 方式更新..."
        echo ""
        
        if [ "$UPDATE_MODE" = "full" ] || [ "$UPDATE_MODE" = "git" ]; then
            echo "🔨 重新构建镜像..."
            docker-compose build
            
            echo "🚀 重启容器..."
            docker-compose up -d
            
            echo ""
            echo "📊 服务状态:"
            docker-compose ps
        else
            echo "🔄 重启容器..."
            docker-compose restart
            
            echo ""
            echo "📊 服务状态:"
            docker-compose ps
        fi
        ;;
        
    systemd)
        echo "🖥️  使用 systemd 方式更新..."
        echo ""
        
        if [ "$UPDATE_MODE" = "full" ] || [ "$UPDATE_MODE" = "git" ]; then
            echo "📦 更新 Python 依赖..."
            if [ -d "venv" ]; then
                source venv/bin/activate
                pip install -r requirements.txt --quiet
            fi
        fi
        
        echo "🔄 重启服务..."
        sudo systemctl restart pdf-splitter
        
        echo ""
        echo "📊 服务状态:"
        sudo systemctl status pdf-splitter --no-pager
        ;;
        
    unknown)
        echo "⚠️  未检测到部署方式，尝试手动重启..."
        echo ""
        echo "请手动执行以下命令之一:"
        echo "  Docker: docker-compose restart"
        echo "  Systemd: sudo systemctl restart pdf-splitter"
        echo "  或直接运行: streamlit run app.py"
        exit 1
        ;;
esac

echo ""
echo "✅ 更新完成！"
echo ""
echo "🌐 应用地址: http://$(hostname -I | awk '{print $1}'):8501"
echo ""
echo "📝 查看日志:"
case $DEPLOY_MODE in
    docker)
        echo "   docker-compose logs -f"
        ;;
    systemd)
        echo "   sudo journalctl -u pdf-splitter -f"
        ;;
esac
