# ================================
# 构建阶段 - 前端 Vue 应用构建
# ================================
FROM node:20-alpine AS frontend-builder

# 设置工作目录
WORKDIR /app/frontend

# 安装 pnpm
RUN npm install -g pnpm

# 复制 package 文件
COPY frontend/package.json frontend/pnpm-lock.yaml ./

# 安装依赖（包括 devDependencies，因为构建需要）
RUN pnpm install --frozen-lockfile

# 复制前端源代码
COPY frontend/ ./

# 构建前端应用
RUN pnpm run build

# ================================
# 运行时阶段 - Python 后端 + 静态文件
# ================================
FROM python:3.12-slim AS runtime

# 设置工作目录
WORKDIR /app

# 设置环境变量
# PYTHONUNBUFFERED: 确保 Python 输出直接显示到控制台
# PYTHONDONTWRITEBYTECODE: 防止 Python 生成 .pyc 文件
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    ENABLE_DASHBOARD=true

# 服务端口配置（默认 8088）
ARG PORT=8088
ENV PORT=${PORT}

# 配置 apt 镜像源
# 检查 /etc/apt/sources.list 是否存在，如果不存在则创建一个新的
RUN test -e /etc/apt/sources.list || echo "deb http://mirrors.aliyun.com/debian bookworm main" > /etc/apt/sources.list && \
    echo "deb-src http://mirrors.aliyun.com/debian bookworm main" >> /etc/apt/sources.list && \
    echo "deb http://mirrors.aliyun.com/debian-security bookworm-security main" >> /etc/apt/sources.list && \
    echo "deb-src http://mirrors.aliyun.com/debian-security bookworm-security main" >> /etc/apt/sources.list && \
    echo "deb http://mirrors.aliyun.com/debian bookworm-updates main" >> /etc/apt/sources.list && \
    echo "deb-src http://mirrors.aliyun.com/debian bookworm-updates main" >> /etc/apt/sources.list
# 安装系统依赖（优化镜像大小）
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    ca-certificates && \
    rm -rf /var/lib/apt/lists/* && \
    apt-get clean

# 创建非 root 用户（安全最佳实践）
RUN useradd --create-home --shell /bin/bash appuser

# 复制 Python 依赖文件
COPY backend/requirements.txt .

# 使用 Pip 清华源
RUN pip config set global.index-url https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple
# 安装 Python 依赖
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 复制后端应用代码（整个 backend 包）
COPY backend/ ./backend/

# 复制环境变量示例文件（可选）
# COPY .env.example .env

# 复制前端构建产物（vite 配置输出到 ../static，即 /app/static）
COPY --from=frontend-builder /app/static ./static/

# 复制环境配置目录
# COPY env/ ./env/

# 设置目录权限
RUN chown -R appuser:appuser /app
USER appuser

# 暴露端口（注意：host 网络模式下不起实际作用）
EXPOSE ${PORT}

# 健康检查
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD python -c "import httpx; import os; port = os.getenv('PORT', '8088'); r = httpx.get(f'http://localhost:{port}/health', timeout=2); exit(0 if r.status_code == 200 else 1)"

# 启动应用（端口通过环境变量 PORT 配置）
# 使用模块方式启动以支持相对导入
CMD ["python", "-m", "backend.app"]