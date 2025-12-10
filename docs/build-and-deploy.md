# 构建和部署指南

本项目提供了完整的构建、测试和部署脚本，支持本地开发和 CI/CD 集成。

## 📁 项目目录结构

```
AnyRouter-Transparent-Proxy/
├── backend/              # 后端服务（FastAPI）
│   ├── app.py           # 核心代理逻辑
│   └── requirements.txt # Python 依赖
├── frontend/            # 前端项目（Vue 3 + TypeScript）
│   ├── src/            # 源代码
│   ├── package.json    # 前端依赖
│   └── vite.config.ts  # Vite 配置
├── scripts/             # 构建和部署脚本
│   ├── build.sh          # 完整构建脚本（前端+后端）
│   ├── build-frontend.sh  # 前端构建脚本
│   └── test.sh           # 应用测试脚本
├── env/                 # 配置文件目录
├── static/              # 前端构建产物（.gitignore）
├── Dockerfile           # Docker 镜像构建
└── docker-compose.yml   # Docker Compose 配置
```

## 🚀 快速开始

### 1. 本地开发构建

```bash
# 克隆项目
git clone <repository-url>
cd anyrouter-transparent-proxy

# 完整构建
./scripts/build.sh

# 仅构建前端
./scripts/build-frontend.sh

# 开发模式构建
./scripts/build.sh --dev
```

### 2. 构建选项

```bash
# 完整构建脚本选项
./scripts/build.sh [选项]

选项:
  --skip-frontend  跳过前端构建
  --skip-backend   跳过后端构建
  --clean          清理所有构建产物
  --dev            开发模式构建
  --help, -h       显示帮助信息
```

## 📦 构建产物

构建完成后会生成：

- `frontend/dist/` - 前端构建产物
- `build_output/` - 所有构建输出
- `anyrouter-transparent-proxy_YYYYMMDD_HHMMSS.tar.gz` - 部署包

## 🐳 Docker 部署

### 使用 Docker Compose（推荐）

```bash
# 1. 复制环境变量
cp .env.example .env

# 2. 编辑配置文件
vim .env
# 设置 DASHBOARD_API_KEY 等配置

# 3. 构建并启动
docker-compose up -d

# 4. 查看日志
docker-compose logs -f

# 5. 停止服务
docker-compose down
```

### 使用 Docker 直接构建

```bash
# 构建镜像
docker build -t anyrouter-proxy .

# 运行容器
docker run -d \
  --name anyrouter-proxy \
  -p 8088:8088 \
  -e ENABLE_DASHBOARD=true \
  -e DASHBOARD_API_KEY=your-secret-key \
  anyrouter-proxy
```

## 🧪 测试

### 自动化测试

```bash
# 设置环境变量
export API_BASE_URL=http://localhost:8088
export API_KEY=your-secret-api-key

# 运行测试
./scripts/test.sh
```

### 测试覆盖

- ✅ 健康检查
- ✅ API 功能测试
- ✅ 认证测试
- ✅ 安全性测试
- ✅ 性能测试

## 🔄 CI/CD

### GitHub Actions

项目已配置完整的 CI/CD 流水线 (`.github/workflows/ci-cd.yml`)：

- 代码质量检查（lint + type check）
- 单元测试
- 构建验证
- Docker 镜像构建
- 自动部署（可选）

### 触发条件

- `push` 到 `main` 或 `develop` 分支
- 创建 Pull Request
- 手动触发 (`workflow_dispatch`)

## 📋 环境变量配置

### 必需配置

```bash
# API 访问密钥（管理面板认证）
DASHBOARD_API_KEY=your-secret-api-key

# 启用管理面板
ENABLE_DASHBOARD=true
```

### 可选配置

```bash
# 上游 API 地址
API_BASE_URL=https://anyrouter.top

# 端口
PORT=8088

# 调试模式
DEBUG_MODE=false

# System Prompt 配置
SYSTEM_PROMPT_REPLACEMENT="You are Claude Code, Anthropic's official CLI for Claude."
SYSTEM_PROMPT_BLOCK_INSERT_IF_NOT_EXIST=false
```

## 🔧 故障排除

### 构建失败

1. **Node.js 版本问题**
   ```bash
   node --version  # 需要版本 >= 18
   ```

2. **依赖安装失败**
   ```bash
   # 清理并重新安装
   rm -rf frontend/node_modules
   cd frontend && npm install
   ```

3. **权限问题**
   ```bash
   # 确保脚本可执行
   chmod +x scripts/*.sh
   ```

### 运行时问题

1. **端口占用**
   ```bash
   # 查看端口占用
   lsof -i :8088
   ```

2. **Docker 问题**
   ```bash
   # 清理 Docker 资源
   docker system prune -a
   ```

3. **权限问题**
   ```bash
   # 检查文件权限
   ls -la /app/env/
   ```

## 📊 监控和日志

### 查看日志

```bash
# Docker Compose
docker-compose logs -f

# Docker 直接运行
docker logs -f anyrouter-proxy

# 本地运行
tail -f logs/app.log
```

### 健康检查

```bash
curl http://localhost:8088/health
```

## 🚀 访问地址

- **代理服务**: http://localhost:8088
- **管理面板**: http://localhost:8088/admin
- **健康检查**: http://localhost:8088/health

## 📚 更多文档

- [项目 README](../README.md)
- [API 文档](../docs/api.md)
- [配置指南](../docs/configuration.md)