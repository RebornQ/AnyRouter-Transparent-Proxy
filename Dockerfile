# 使用官方 Python 3.12 slim 镜像作为基础镜像
FROM python:3.12-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
# PYTHONUNBUFFERED: 确保 Python 输出直接显示到控制台
# PYTHONDONTWRITEBYTECODE: 防止 Python 生成 .pyc 文件
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# 服务端口配置（默认 8088）
ARG PORT=8088
ENV PORT=${PORT}

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY app.py .

# 复制环境变量示例文件（可选）
# COPY .env.example .

# 暴露端口（注意：host 网络模式下不起实际作用）
EXPOSE ${PORT}

# 健康检查
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD python -c "import httpx; import os; port = os.getenv('PORT', '8088'); r = httpx.get(f'http://localhost:{port}/health', timeout=2); exit(0 if r.status_code == 200 else 1)"

# CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", ${PORT}]
# 启动应用（端口通过环境变量 PORT 配置）
CMD ["python", "app.py"]