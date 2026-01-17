# 阿里云服务器部署指南

本文档介绍如何将智能PDF切分工具部署到阿里云服务器。

## 📋 前置要求

- 阿里云 ECS 服务器（Ubuntu/CentOS）
- 服务器已开放 8501 端口（或自定义端口）
- 服务器有公网 IP
- 已安装 Docker（推荐）或 Python 3.8+

---

## 🐳 方式一：Docker 部署（推荐）

### 1. 安装 Docker

**Ubuntu/Debian:**
```bash
# 更新系统
sudo apt-get update

# 安装 Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# 启动 Docker
sudo systemctl start docker
sudo systemctl enable docker

# 验证安装
docker --version
```

**CentOS/RHEL:**
```bash
# 安装 Docker
sudo yum install -y docker
sudo systemctl start docker
sudo systemctl enable docker

# 验证安装
docker --version
```

### 2. 安装 Docker Compose

```bash
# 下载 Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose

# 添加执行权限
sudo chmod +x /usr/local/bin/docker-compose

# 验证安装
docker-compose --version
```

### 3. 上传项目文件

将项目文件上传到服务器（使用 scp 或 SFTP）：

```bash
# 在本地执行
scp -r smart-pdf-splitter root@your-server-ip:/opt/
```

或使用 Git：
```bash
# 在服务器上执行
cd /opt
git clone your-repo-url smart-pdf-splitter
cd smart-pdf-splitter
```

### 4. 启动应用

```bash
cd /opt/smart-pdf-splitter

# 使用 Docker Compose 启动
docker-compose up -d --build

# 查看日志
docker-compose logs -f
```

### 5. 访问应用

打开浏览器访问：`http://your-server-ip:8501`

---

## 🖥️ 方式二：传统部署（不使用 Docker）

### 1. 安装系统依赖

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install -y python3 python3-pip poppler-utils nginx
```

**CentOS/RHEL:**
```bash
sudo yum install -y python3 python3-pip poppler-utils nginx
```

### 2. 安装 Python 依赖

```bash
cd /opt/smart-pdf-splitter
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. 配置 systemd 服务

创建服务文件 `/etc/systemd/system/pdf-splitter.service`:

```ini
[Unit]
Description=Smart PDF Splitter Streamlit App
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/smart-pdf-splitter
Environment="PATH=/opt/smart-pdf-splitter/venv/bin"
ExecStart=/opt/smart-pdf-splitter/venv/bin/streamlit run app.py --server.port=8501 --server.address=0.0.0.0
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

启动服务：
```bash
sudo systemctl daemon-reload
sudo systemctl enable pdf-splitter
sudo systemctl start pdf-splitter
sudo systemctl status pdf-splitter
```

### 4. 配置 Nginx 反向代理（可选）

创建 Nginx 配置 `/etc/nginx/sites-available/pdf-splitter`:

```nginx
server {
    listen 80;
    server_name your-domain.com;  # 替换为你的域名或 IP

    location / {
        proxy_pass http://localhost:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 86400;
        proxy_buffering off;
    }
}
```

启用配置：
```bash
sudo ln -s /etc/nginx/sites-available/pdf-splitter /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 5. 配置 HTTPS（推荐）

使用 Let's Encrypt 免费证书：

```bash
# 安装 Certbot
sudo apt-get install certbot python3-certbot-nginx  # Ubuntu/Debian
# 或
sudo yum install certbot python3-certbot-nginx      # CentOS/RHEL

# 获取证书
sudo certbot --nginx -d your-domain.com

# 自动续期测试
sudo certbot renew --dry-run
```

---

## 🔒 安全配置

### 1. 防火墙设置

**Ubuntu (UFW):**
```bash
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw allow 8501/tcp  # Streamlit (如果不用 Nginx)
sudo ufw enable
```

**CentOS (firewalld):**
```bash
sudo firewall-cmd --permanent --add-service=ssh
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --permanent --add-port=8501/tcp  # 如果不用 Nginx
sudo firewall-cmd --reload
```

### 2. 阿里云安全组配置

在阿里云控制台配置安全组规则：
- 开放 22 端口（SSH）
- 开放 80 端口（HTTP）
- 开放 443 端口（HTTPS）
- 如需直接访问 Streamlit，开放 8501 端口

### 3. 限制文件上传大小

编辑 `.streamlit/config.toml`:
```toml
[server]
maxUploadSize = 200  # MB
```

---

## 📝 常用管理命令

### Docker 方式

```bash
# 查看日志
docker-compose logs -f

# 重启服务
docker-compose restart

# 停止服务
docker-compose down

# 更新代码后重新部署
git pull
docker-compose up -d --build
```

### 传统方式

```bash
# 查看服务状态
sudo systemctl status pdf-splitter

# 查看日志
sudo journalctl -u pdf-splitter -f

# 重启服务
sudo systemctl restart pdf-splitter

# 停止服务
sudo systemctl stop pdf-splitter

# 更新代码后重启
cd /opt/smart-pdf-splitter
git pull
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart pdf-splitter
```

---

## 🐛 常见问题

### 1. 端口被占用

```bash
# 查看端口占用
sudo netstat -tlnp | grep 8501
# 或
sudo lsof -i :8501

# 修改端口（编辑 config.toml 或 docker-compose.yml）
```

### 2. Poppler 未找到（传统部署）

```bash
# 检查 Poppler
which pdftoppm

# 如果未安装
sudo apt-get install poppler-utils  # Ubuntu/Debian
sudo yum install poppler-utils      # CentOS/RHEL
```

### 3. 内存不足

- 检查服务器内存：`free -h`
- 大文件处理可能需要更多内存
- 考虑升级服务器配置

### 4. 无法访问

- 检查防火墙规则
- 检查阿里云安全组配置
- 检查服务是否运行：`sudo systemctl status pdf-splitter` 或 `docker-compose ps`

### 5. API 调用失败

- 检查服务器网络连接
- 验证 API Key 是否有效
- 检查是否需要配置代理

---

## 📞 快速部署脚本

使用提供的 `deploy.sh` 脚本：

```bash
chmod +x deploy.sh
./deploy.sh
```

脚本会自动检查 Docker 环境并完成部署。

---

## 🔄 更新应用

详细的更新指南请查看 [UPDATE.md](UPDATE.md)

### 快速更新（使用脚本）

```bash
cd /opt/smart-pdf-splitter
chmod +x update.sh
./update.sh git    # Git 拉取更新
```

### 手动更新

```bash
cd /opt/smart-pdf-splitter

# Docker 方式
git pull
docker-compose up -d --build

# 传统方式
git pull
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart pdf-splitter
```

### 本地同步到服务器

在本地项目目录运行：
```bash
# 1. 修改 sync.sh 中的服务器信息
# 2. 运行同步脚本
chmod +x sync.sh
./sync.sh
```
