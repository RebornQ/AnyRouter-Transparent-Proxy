# AnyRouter Transparent Proxy

一个基于 FastAPI 的轻量级透明 HTTP 代理服务，专为解决 AnyRouter 的 Anthropic API 在 Claude Code for VS Code 插件中报错 500 的问题而设计。

## 效果图

![效果图](./screenshot/效果图.png)

![仪表板页面](./screenshot/仪表板页面.png)


## 目录

- [核心特性](#核心特性)
- [项目结构](#项目结构)
- [快速开始](#快速开始)
  - [Docker 部署（推荐）](#docker-部署推荐)
  - [本地运行](#本地运行)
- [配置说明](#配置说明)
- [核心功能](#核心功能)
- [架构与技术](#架构与技术)
- [安全性](#安全性)
- [贡献](#贡献)

## 核心特性

- **完全透明** - 支持所有 HTTP 方法，无缝代理请求
- **流式响应** - 基于 `httpx.AsyncClient` 异步架构，完美支持流式传输
- **标准兼容** - 严格遵循 RFC 7230 规范，正确处理 HTTP 头部
- **灵活配置** - 支持环境变量配置目标 URL 和 System Prompt 替换
- **高性能** - 连接池复用，异步处理，高效应对并发请求
- **智能处理** - 自动计算 Content-Length，避免请求体修改导致的协议错误
- **Web 管理面板** - 提供实时监控、统计分析和配置管理功能

## 项目结构

```
AnyRouter-Transparent-Proxy/
├── backend/              # 后端服务（FastAPI）
│   ├── app.py           # 核心代理逻辑
│   └── requirements.txt # Python 依赖
├── frontend/            # 前端项目（Vue 3 + TypeScript）
│   ├── src/            # 源代码
│   ├── package.json    # 前端依赖
│   └── vite.config.ts  # Vite 配置
├── env/                 # 配置文件目录
│   ├── .env             # 环境变量配置（需从 .env.example 复制）
│   └── .env.headers.json # 自定义请求头配置
├── docs/                # 文档
├── static/              # 前端构建产物（.gitignore）
├── Dockerfile           # Docker 镜像构建
├── docker-compose.yml   # Docker Compose 配置
├── .env.example         # 环境变量模板
└── CLAUDE.md           # AI 上下文索引
```

**说明**：
- `backend/` - 后端 Python 服务，负责代理逻辑和 API 处理
- `frontend/` - 前端 Vue 项目，提供 Web 管理面板
- `static/` - 前端构建产物，由 Docker 构建时自动生成，不提交到 Git
- `env/` - 运行时配置文件目录

## 快速开始

### Docker 部署（推荐）

**使用 Docker Compose：**

```bash
# 克隆项目
git clone <repository-url>
cd AnyRouter-Transparent-Proxy

# 复制环境变量模板（可选）
cp .env.example env/.env

# 编辑 env/.env 文件修改配置（可选）
# 默认使用 https://anyrouter.top

# 启动服务
docker-compose up -d
# 若部署后有改动过项目源码，则需要加上 --build --remove-orphans 重新构建
docker-compose up -d --build --remove-orphans 

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down

# 重启服务
docker-compose down && docker-compose up -d
```

**或使用 Docker 命令：**

```bash
# 构建并运行
docker build -t anthropic-proxy .
docker run -d --name anthropic-proxy -p 8088:8088 anthropic-proxy

# 自定义目标 URL
docker run -d --name anthropic-proxy -p 8088:8088 \
  -e API_BASE_URL=https://anyrouter.top \
  anthropic-proxy
```

服务将在 [http://localhost:8088](http://localhost:8088) 启动，然后在 Claude Code 中配置此地址即可。

~~管理面板通过 [http://localhost:8088/admin](http://localhost:8088/admin) 访问。~~

现在管理面板可以直接访问主页 [http://localhost:8088](http://localhost:8088) 自动跳转了

### 本地运行

**环境要求：** Python 3.7+

```bash
# 安装依赖
pip install -r backend/requirements.txt

# 或手动安装
pip install fastapi uvicorn httpx python-dotenv

# 复制环境变量模板
cp .env.example env/.env

# 启动服务（从项目根目录运行）
python -m backend.app
```

服务将在 [http://localhost:8088](http://localhost:8088) 启动。

**注意**：本地开发时，如果需要使用 Web 管理面板，需要先构建前端：

```bash
cd frontend
npm install
npm run build
cd ..
```

构建产物会输出到 `static/` 目录（该目录已在 `.gitignore` 中忽略）。

~~管理面板通过 [http://localhost:8088/admin](http://localhost:8088/admin) 访问。~~

现在管理面板可以直接访问主页 [http://localhost:8088](http://localhost:8088) 自动跳转了

## 配置说明

### 环境变量

创建 `env/.env` 文件或设置环境变量：

```bash
# API 目标地址（默认：https://anyrouter.top）或使用反代地址
API_BASE_URL=https://anyrouter.top

# System Prompt 替换（可选）
# 替换请求体中 system 数组的第一个元素的 text 内容
SYSTEM_PROMPT_REPLACEMENT="You are Claude Code, Anthropic's official CLI for Claude."

# 如果需要通过代理访问，请取消下面两行的注释并设置代理地址
# HTTP_PROXY=http://127.0.0.1:7890
# HTTPS_PROXY=http://127.0.0.1:7890
```

### 自定义请求头（可选）

可以通过 `env/.env.headers.json` 文件配置自定义请求头，这些头部会被注入到所有代理请求中。

**配置步骤：**

1. 复制模板文件创建配置：
   ```bash
   cp .env.headers.json.example env/.env.headers.json
   ```

2. 编辑 `env/.env.headers.json` 文件，添加你需要的请求头：
   ```json
   {
     "User-Agent": "claude-cli/2.0.8 (external, cli)"
   }
   ```

3. 重启服务使配置生效

**说明：**
- 配置文件使用标准 JSON 格式
- 以 `__` 开头的字段会被忽略（可用于添加注释）
- 如果文件不存在，默认使用空配置 `{}`
- 自定义请求头会覆盖原请求中的同名头部

> 注：配置完成后需要重新启动服务

## 核心功能

### System Prompt 替换

动态替换 Anthropic API 请求体中 `system` 数组第一个元素的 `text` 内容：

- 自定义 Claude Code CLI 行为
- 调整 Claude Agent SDK 响应
- 统一注入系统级提示词

配置 `SYSTEM_PROMPT_REPLACEMENT` 变量启用此功能。

### 智能请求头处理

- **自动过滤** - 移除 hop-by-hop 头部（Connection、Keep-Alive 等）
- **Host 重写** - 自动改写为目标服务器域名
- **Content-Length 自动计算** - 根据实际内容自动计算，避免长度不匹配
- **自定义注入** - 支持覆盖或添加任意请求头
- **IP 追踪** - 自动维护 X-Forwarded-For 链

## 使用示例

将原本指向 `anyrouter.top` 或其他 API 的请求改为指向代理服务：

```bash
# 原始请求
curl https://anyrouter.top/v1/messages \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "content-type: application/json" \
  -d '{"model": "claude-3-5-sonnet-20241022", "messages": [...]}'

# 通过代理
curl http://localhost:8088/v1/messages \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "content-type: application/json" \
  -d '{"model": "claude-3-5-sonnet-20241022", "messages": [...]}'
```

## 架构与技术

### 请求处理流程

```
客户端请求
    ↓
proxy() 捕获路由
    ↓
filter_request_headers() 过滤请求头
    ↓
process_request_body() 处理请求体(可选替换 system prompt)
    ↓
重写 Host 头 + 注入自定义头 + 添加 X-Forwarded-For
    ↓
httpx.AsyncClient 通过 build_request() + send(stream=True) 发起上游请求
    ↓
filter_response_headers() 过滤响应头
    ↓
StreamingResponse 流式返回给客户端,使用 BackgroundTask 自动关闭连接
```

### 关键技术

- **路由处理** - `@app.api_route("/{path:path}")` 捕获所有路径和 HTTP 方法
- **生命周期管理** - 使用 FastAPI lifespan 事件管理 HTTP 客户端生命周期
- **连接池复用** - 全局共享 `httpx.AsyncClient` 实现连接复用
- **异步请求** - 60 秒超时,支持长时间流式响应
- **流式传输** - `build_request()` + `send(stream=True)` + `aiter_bytes()` + `BackgroundTask` 高效处理大载荷,自动管理连接生命周期
- **头部过滤** - 符合 RFC 7230 规范,双向过滤 hop-by-hop 头部

### 技术细节

**请求头过滤规则（RFC 7230）：**

移除的头部：Connection、Keep-Alive、Proxy-Authenticate、Proxy-Authorization、TE、Trailers、Transfer-Encoding、Upgrade、Content-Length（由 httpx 自动重新计算）

**System Prompt 替换逻辑：**

1. 检查 `SYSTEM_PROMPT_REPLACEMENT` 配置
2. 解析请求体为 JSON
3. 验证 `system` 字段存在且为非空数组
4. 替换 `system[0].text` 内容
5. 重新序列化为 JSON

失败时自动回退到原始请求体，确保服务稳定性。

**HTTP 客户端生命周期：**

- 启动时创建共享的 `httpx.AsyncClient` 实例
- 运行时所有请求复用同一客户端，享受连接池优势
- 关闭时优雅释放所有连接资源

### 日志输出示例

```
[Proxy] Original body (123 bytes): {...}
[System Replacement] Successfully parsed JSON body
[System Replacement] Original system[0].text: You are Claude Code...
[System Replacement] Replaced with: 你是一个有用的AI助手
[System Replacement] Successfully modified body (original size: 123 bytes, new size: 145 bytes)
```

## 安全性

- **防重定向攻击** - `follow_redirects=False`
- **请求超时** - 60 秒超时防止资源耗尽
- **错误处理** - 上游请求失败时返回 502 状态码
- **自动容错** - Content-Length 自动计算，避免协议错误
- **连接管理** - 共享客户端池确保连接正确关闭
- **日志记录** - 详细的调试信息（生产环境建议移除敏感信息）

## 贡献

欢迎提交 Issue 和 Pull Request！

---

**注意**：本项目仅供学习和开发测试使用，请确保遵守相关服务的使用条款。
