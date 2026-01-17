# GitHub Actions 自动部署配置

## 📋 配置说明

本工作流会在你推送代码到 `main` 或 `master` 分支时，自动部署到阿里云服务器。

## 🔧 配置步骤

### 1. 在 GitHub 仓库设置 Secrets

进入你的 GitHub 仓库 → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

添加以下 Secrets：

| Secret 名称 | 说明 | 示例值 |
|------------|------|--------|
| `SERVER_IP` | 服务器 IP 地址 | `123.456.789.0` |
| `SERVER_SSH_KEY` | SSH 私钥 | 见下方说明 |

### 2. 获取 SSH 私钥

#### 如果服务器已有 SSH 密钥对：

```bash
# 在服务器上查看公钥
cat ~/.ssh/id_rsa.pub

# 在本地生成新的密钥对（推荐）
ssh-keygen -t rsa -b 4096 -C "github-actions"
# 保存为 ~/.ssh/github_actions_key

# 将公钥添加到服务器
ssh-copy-id -i ~/.ssh/github_actions_key.pub root@your-server-ip

# 将私钥内容复制到 GitHub Secrets
cat ~/.ssh/github_actions_key
```

#### 如果没有 SSH 密钥：

```bash
# 在本地生成
ssh-keygen -t rsa -b 4096 -C "github-actions-deploy"

# 将公钥添加到服务器
ssh-copy-id -i ~/.ssh/id_rsa.pub root@your-server-ip

# 将私钥内容复制到 GitHub Secrets
cat ~/.ssh/id_rsa
```

**重要**: 
- 私钥内容要完整复制，包括 `-----BEGIN` 和 `-----END` 行
- 不要泄露私钥
- Secret 名称必须使用 `SERVER_IP` 和 `SERVER_SSH_KEY`（与工作流配置一致）

### 3. 配置服务器目录

确保服务器上的目标目录存在：

```bash
# SSH 登录服务器
ssh root@your-server-ip

# 创建项目目录
mkdir -p /opt/smart-pdf-splitter
```

### 4. 测试部署

推送代码测试：

```bash
git add .
git commit -m "测试自动部署"
git push origin main
```

然后在 GitHub 仓库的 **Actions** 标签页查看部署进度。

## 🔍 工作流说明

### 触发条件

- 推送到 `main` 或 `master` 分支
- 手动触发（在 Actions 页面点击 "Run workflow"）

### 执行步骤

1. **检出代码**: 从 GitHub 拉取最新代码
2. **SCP 上传**: 将代码上传到服务器 `/opt/smart-pdf-splitter`
3. **清理文件**: 删除不需要的文件（`.github`, `.git`, `.gitignore`, 文档等）
4. **部署应用**: 
   - Docker 方式：重新构建镜像并重启容器
   - Systemd 方式：更新依赖并重启服务
5. **健康检查**: 验证服务是否正常运行

### 清理的文件

工作流会自动清理以下文件（不需要在服务器上保留）：
- `.github/` - GitHub Actions 配置
- `.git/` - Git 仓库
- `.gitignore` - Git 忽略文件
- `.claude/` - Claude 配置
- `*.md` - 文档文件
- `deploy.sh`, `sync.sh`, `update.sh` - 部署脚本

## 🐛 故障排查

### 1. SCP 上传失败

- 检查 `SERVER_IP` 是否正确
- 检查 `SERVER_SSH_KEY` 是否完整（包括首尾行）
- 检查服务器防火墙是否开放 SSH 端口（默认 22）
- 测试手动 SSH 连接：`ssh -i ~/.ssh/your_key root@your-server-ip`

### 2. 部署失败

- 检查目标目录是否存在：`/opt/smart-pdf-splitter`
- 检查目录权限：`ls -la /opt/smart-pdf-splitter`
- 查看详细日志：在 Actions 页面查看失败步骤的日志

### 3. Docker 部署失败

- 检查 Docker 是否运行：`ssh root@your-server-ip "docker ps"`
- 查看详细日志：在 Actions 页面查看失败步骤的日志
- 手动登录服务器检查：`docker-compose logs`

### 4. 健康检查失败

- 检查服务是否启动：`ssh root@your-server-ip "cd /opt/smart-pdf-splitter && docker-compose ps"`
- 查看应用日志排查问题
- 检查端口是否被占用

## 🔒 安全建议

1. **使用专用 SSH 密钥**: 不要使用个人 SSH 密钥，创建专门用于部署的密钥
2. **限制 SSH 访问**: 在服务器上配置 SSH 密钥认证，禁用密码登录
3. **定期轮换密钥**: 定期更新 SSH 密钥
4. **保护 Secrets**: 不要在代码中硬编码敏感信息，使用 GitHub Secrets

## 📝 自定义配置

### 修改部署路径

编辑 `.github/workflows/deploy.yml`:

```yaml
target: "/your/custom/path"  # 修改目标路径
```

### 修改清理文件列表

编辑工作流文件中的清理步骤：

```yaml
script: |
  rm -rf .github
  rm -rf .git
  # 添加或删除需要清理的文件
```

### 添加部署前/后步骤

在工作流中添加自定义步骤：

```yaml
- name: Custom step
  uses: appleboy/ssh-action@master
  with:
    host: ${{ secrets.SERVER_IP }}
    username: root
    key: ${{ secrets.SERVER_SSH_KEY }}
    script: |
      # 你的自定义命令
      echo "部署前备份"
      cp -r /opt/smart-pdf-splitter /opt/backup
```

## 💡 最佳实践

1. **使用分支保护**: 在 GitHub 设置分支保护规则，确保代码质量
2. **测试后再部署**: 推送到测试分支验证，确认无误后再合并到主分支
3. **查看部署日志**: 每次部署后检查 Actions 日志，及时发现问题
4. **备份数据**: 部署前自动备份重要数据（可在工作流中添加）
5. **回滚方案**: 保留上一个版本的 Docker 镜像或代码，便于快速回滚

## 🔄 与 React 项目的区别

| 项目类型 | React | Streamlit |
|---------|-------|-----------|
| **部署方式** | 静态文件上传 | 需要构建和重启服务 |
| **清理文件** | 删除 `.github` | 删除更多文件（包括文档和脚本） |
| **部署后操作** | 无需操作 | 需要重启 Docker/Systemd 服务 |
| **健康检查** | 无需 | 需要验证服务运行状态 |

## 📞 变量说明

工作流使用的变量（必须在 GitHub Secrets 中配置）：

- `SERVER_IP`: 服务器 IP 地址
- `SERVER_SSH_KEY`: SSH 私钥

这些变量名称与你的 React 项目保持一致，方便统一管理。
