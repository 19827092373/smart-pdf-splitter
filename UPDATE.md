# 代码更新指南

本文档介绍如何更新已部署的应用代码。有多种方式可以实现代码更新，选择最适合你的方案。

## 📋 更新方案对比

| 方案 | 优点 | 缺点 | 适用场景 |
|------|------|------|----------|
| **GitHub Actions** | 全自动、CI/CD、推送即部署 | 需要配置一次 | ⭐ 推荐，适合所有场景 |
| **Git 拉取** | 版本控制、可回滚 | 需要手动操作 | 服务器直接更新 |
| **SCP/SFTP** | 简单直接、无需 Git | 手动操作、无版本控制 | 快速修改、临时更新 |
| **Rsync 同步** | 增量同步、速度快 | 需要配置 | 本地开发同步到服务器 |

---

## 🚀 方案一：GitHub Actions 自动部署（⭐ 推荐）

### 适用场景
- 代码推送到 GitHub 后自动部署
- 无需手动操作，推送即部署
- 适合所有场景，最推荐的方式

### 配置步骤

#### 1. 配置 GitHub Secrets

进入 GitHub 仓库 → Settings → Secrets and variables → Actions → New repository secret

添加以下 Secrets：

| Secret 名称 | 说明 | 示例值 |
|------------|------|--------|
| `SERVER_IP` | 服务器 IP 地址 | `123.456.789.0` |
| `SERVER_SSH_KEY` | SSH 私钥 | 见下方说明 |

**注意**: 变量名称与你的 React 项目保持一致，方便统一管理。

#### 2. 获取 SSH 私钥

```bash
# 如果已有密钥，直接使用
cat ~/.ssh/id_rsa

# 或创建新的部署专用密钥
ssh-keygen -t rsa -b 4096 -C "github-actions"
# 保存为 ~/.ssh/github_actions_key

# 将公钥添加到服务器
ssh-copy-id -i ~/.ssh/github_actions_key.pub root@your-server-ip

# 复制私钥内容到 GitHub Secrets
cat ~/.ssh/github_actions_key
```

#### 3. 配置服务器目录

确保服务器上的目标目录存在：

```bash
# SSH 登录服务器
ssh root@your-server-ip

# 创建项目目录
mkdir -p /opt/smart-pdf-splitter
```

**注意**: 本工作流使用 SCP 直接上传文件，不需要在服务器上配置 Git 仓库。

#### 4. 使用

配置完成后，每次推送代码到 `main` 或 `master` 分支，GitHub Actions 会自动：

1. 检出最新代码
2. **SCP 上传**: 将代码上传到服务器
3. **清理文件**: 删除不需要的文件（`.github`, `.git`, 文档等）
4. **重新构建并部署**: Docker 或 Systemd 方式
5. **健康检查**: 验证服务是否正常运行

```bash
# 本地开发
git add .
git commit -m "更新功能"
git push origin main  # 推送后自动部署！
```

### 查看部署状态

在 GitHub 仓库的 **Actions** 标签页查看部署进度和日志。

### 详细配置

查看 [.github/workflows/README.md](.github/workflows/README.md) 获取完整配置说明。

---

## 📥 方案二：Git 拉取更新（服务器端）

### 前提条件
- 代码已推送到 Git 仓库（GitHub / Gitee / GitLab）
- 服务器已安装 Git

### 更新步骤

#### 方式 A：手动更新

```bash
# SSH 登录服务器
ssh root@your-server-ip

# 进入项目目录
cd /opt/smart-pdf-splitter

# 拉取最新代码
git pull origin main  # 或 master

# Docker 方式：重新构建并重启
docker-compose up -d --build

# 传统方式：重启服务
sudo systemctl restart pdf-splitter
```

#### 方式 B：使用更新脚本（推荐）

```bash
# 在服务器上运行
cd /opt/smart-pdf-splitter
chmod +x update.sh
./update.sh
```

脚本会自动拉取代码、重新构建并重启服务。

---

## 📤 方案二：SCP 直接上传

### 适用场景
- 快速修改单个文件
- 不想使用 Git
- 临时更新

### 更新步骤

```bash
# 在本地执行（Windows PowerShell 或 Git Bash）
# 上传单个文件
scp app.py root@your-server-ip:/opt/smart-pdf-splitter/

# 上传整个项目
scp -r smart-pdf-splitter root@your-server-ip:/opt/

# 然后 SSH 登录服务器重启服务
ssh root@your-server-ip
cd /opt/smart-pdf-splitter
docker-compose restart
# 或
sudo systemctl restart pdf-splitter
```

### Windows 用户可以使用 WinSCP
1. 下载安装 WinSCP
2. 连接服务器
3. 拖拽文件上传
4. SSH 登录重启服务

---

## 🔄 方案三：Rsync 同步（本地开发推荐）

### 适用场景
- 本地开发，需要频繁同步到服务器
- 增量同步，速度快

### 配置步骤

#### 1. 创建同步脚本 `sync.sh`（本地）

```bash
#!/bin/bash
# 同步代码到服务器

SERVER="root@your-server-ip"
REMOTE_DIR="/opt/smart-pdf-splitter"
LOCAL_DIR="./"

# 排除不需要同步的文件
rsync -avz --exclude '.git' \
          --exclude '__pycache__' \
          --exclude '*.pyc' \
          --exclude '.streamlit/secrets.toml' \
          --exclude 'venv' \
          --exclude '*.pdf' \
          --exclude '*.zip' \
          $LOCAL_DIR $SERVER:$REMOTE_DIR

# 在服务器上重启服务
ssh $SERVER "cd $REMOTE_DIR && docker-compose restart"
```

#### 2. 使用

```bash
chmod +x sync.sh
./sync.sh
```

---

## 🤖 方案四：GitHub Actions 自动部署（高级）

### 适用场景
- 代码推送到 GitHub 后自动部署
- 适合团队协作

### 配置步骤

#### 1. 创建 `.github/workflows/deploy.yml`

```yaml
name: Deploy to Aliyun

on:
  push:
    branches: [ main ]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Deploy to server
        uses: appleboy/scp-action@master
        with:
          host: ${{ secrets.SERVER_HOST }}
          username: ${{ secrets.SERVER_USER }}
          key: ${{ secrets.SSH_KEY }}
          source: "."
          target: "/opt/smart-pdf-splitter"
          
      - name: Restart service
        uses: appleboy/ssh-action@master
        with:
          host: ${{ secrets.SERVER_HOST }}
          username: ${{ secrets.SERVER_USER }}
          key: ${{ secrets.SSH_KEY }}
          script: |
            cd /opt/smart-pdf-splitter
            docker-compose up -d --build
```

#### 2. 在 GitHub 仓库设置 Secrets
- `SERVER_HOST`: 服务器 IP
- `SERVER_USER`: SSH 用户名（如 root）
- `SSH_KEY`: SSH 私钥

---

## 🔧 方案五：使用更新脚本（最简单）

### 创建更新脚本

已提供 `update.sh` 脚本，支持多种更新方式：

```bash
# 使用 Git 更新
./update.sh git

# 手动上传后更新（只重启服务）
./update.sh restart

# 完整更新（拉取 + 构建 + 重启）
./update.sh full
```

---

## 📝 推荐工作流程

### 日常开发流程（GitHub Actions）

1. **本地修改代码**
   ```bash
   # 在本地开发
   code app.py
   ```

2. **测试本地运行**
   ```bash
   streamlit run app.py
   ```

3. **提交并推送**
   ```bash
   git add .
   git commit -m "更新说明"
   git push origin main
   ```
   
   **推送后自动部署！** 🎉

4. **查看部署状态**
   - 在 GitHub 仓库的 Actions 标签页查看部署进度
   - 部署完成后访问服务器验证

### 服务器端手动更新（备用方案）

如果 GitHub Actions 不可用，可以在服务器上手动更新：

```bash
# SSH 登录服务器
ssh root@your-server-ip

# 运行更新脚本
cd /opt/smart-pdf-splitter
./update.sh git
```

### 快速修改单个文件

```bash
# 直接上传文件
scp app.py root@your-server-ip:/opt/smart-pdf-splitter/

# SSH 重启
ssh root@your-server-ip "cd /opt/smart-pdf-splitter && docker-compose restart"
```

---

## ⚠️ 注意事项

1. **备份重要数据**
   - 更新前建议备份数据库或配置文件
   - 使用 Git 可以随时回滚

2. **测试环境**
   - 建议先在测试环境验证
   - 确认无误后再更新生产环境

3. **服务重启**
   - 更新代码后必须重启服务才能生效
   - Docker 方式需要重新构建镜像

4. **配置文件**
   - `.streamlit/config.toml` 等配置文件更新后需要重启
   - 注意不要覆盖服务器特定的配置

5. **依赖更新**
   - 如果 `requirements.txt` 有变化，需要重新安装依赖
   - Docker 方式会自动处理

---

## 🐛 更新失败处理

### 回滚到上一个版本（Git 方式）

```bash
cd /opt/smart-pdf-splitter
git log  # 查看提交历史
git reset --hard HEAD~1  # 回滚到上一个版本
docker-compose up -d --build
```

### 查看更新日志

```bash
# Docker 方式
docker-compose logs -f

# 传统方式
sudo journalctl -u pdf-splitter -f
```

---

## 💡 最佳实践

1. **使用 Git 管理代码**（推荐）
   - 版本控制
   - 可回滚
   - 便于协作

2. **创建更新脚本**
   - 自动化更新流程
   - 减少人为错误

3. **定期备份**
   - 代码备份（Git）
   - 数据备份（配置文件等）

4. **测试后再部署**
   - 本地测试通过
   - 再更新服务器
