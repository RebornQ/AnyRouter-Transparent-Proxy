# Technology Stack

## Project Type
**高性能异步 HTTP 代理服务** - 基于 FastAPI 的轻量级透明代理服务器，专为解决 Anthropic API 兼容性问题而设计，支持流式响应和企业级部署。

## Core Technologies

### Primary Language(s)
- **Language**: Python 3.12 (现代化异步编程支持)
- **Runtime**: CPython 官方解释器
- **Language-specific tools**:
  - pip (包管理器)
  - venv (虚拟环境)
  - Python async/await (异步编程范式)

### Key Dependencies/Libraries
- **FastAPI 0.115.5**: 现代高性能 Web 框架，支持自动 API 文档生成和异步处理
- **Uvicorn 0.32.1**: ASGI 服务器，支持 HTTP/1.1 和 WebSocket，生产级性能
- **httpx 0.28.1**: 现代异步 HTTP 客户端，支持 HTTP/2 和连接池复用
- **python-dotenv 1.0.1**: 环境变量管理，支持 .env 文件配置

### Application Architecture
**单文件异步代理架构**
- **设计模式**: 单文件模块化架构，所有核心功能集中在 app.py
- **异步处理**: 基于 FastAPI + Uvicorn 的 ASGI 异步架构
- **代理模式**: 透明 HTTP 代理，完全转发请求/响应
- **生命周期**: FastAPI lifespan 事件管理 HTTP 客户端初始化和清理
- **核心函数架构**:
  - `lifespan()`: 应用启动/关闭时的资源管理
  - `proxy()`: 主代理函数，捕获所有路由请求
  - `filter_request_headers()`: 请求头过滤和改写
  - `process_request_body()`: System Prompt 处理逻辑
  - `filter_response_headers()`: 响应头过滤

### Data Storage
- **Primary storage**: 无状态设计，不持久化数据
- **Configuration**: 环境变量 + JSON 配置文件
- **Caching**: 连接池复用（httpx 内置）
- **Data formats**: JSON (API 请求/响应), 环境配置文件

### External Integrations
- **APIs**: AnyRouter API (https://anyrouter.top) - Anthropic API 代理服务
- **Protocols**:
  - HTTP/1.1 (主要协议)
  - HTTPS (加密传输)
  - Server-Sent Events (流式响应)
  - WebSocket (未来支持)
- **Authentication**:
  - API Key 转发
  - 自定义请求头注入
  - 透明身份验证

### Monitoring & Dashboard Technologies
- **Health Monitoring**: `/health` 端点用于 Docker 容器健康检查
- **Logging**:
  - 前缀日志系统: `[Proxy]`, `[System Replacement]`, `[Custom Headers]`, `[Stream Error]`
  - 可选调试模式: 详细请求/响应信息
  - 生产安全: 自动过滤敏感信息
- **实时监控**:
  - 连接状态监控
  - 流式响应错误处理
  - 资源使用追踪

## Development Environment

### Build & Development Tools
- **Build System**: 无需构建，Python 直接执行
- **Package Management**: pip + requirements.txt (4 个核心依赖)
- **Development workflow**:
  - 开发模式: `python app.py`
  - 生产模式: `uvicorn app:app --host 0.0.0.0 --port 8088`
  - Docker 模式: `docker-compose up -d`

### Code Quality Tools
- **静态分析**: 可选的 pyflakes 和 mypy
- **代码格式化**: black, isort (推荐但不强制)
- **测试框架**: pytest + httpx TestClient (基础测试覆盖)
- **文档生成**: FastAPI 自动生成 `/docs` Swagger UI

### Version Control & Collaboration
- **VCS**: Git (主分支为 main)
- **Branching Strategy**: 简单的主分支开发，功能分支可选
- **代码审查**: Pull Request 流程 (可选)

### Dashboard Development
- **Live Reload**: Uvicorn 自动重载
- **Port Management**: 可配置端口 (默认 8088)
- **Multi-Instance Support**: 支持多实例部署（通过端口配置）

## Deployment & Distribution
- **Target Platform(s)**:
  - Linux (主要生产环境)
  - Docker 容器 (推荐部署方式)
- **Distribution Method**:
  - GitHub 源码
  - Docker 镜像构建
- **Installation Requirements**:
  - Python 3.12+ (或 Docker 环境)
  - 网络访问 AnyRouter API
- **Deployment**:
  - Docker Compose: 一键部署
  - 健康检查: 30秒间隔检查 `/health`
  - 自动重启: `unless-stopped` 策略

## Technical Requirements & Constraints

### Performance Requirements
- **启动时间**: < 5 秒
- **代理延迟**: < 50ms (不包括上游 API 延迟)
- **并发处理**: 100+ 并发连接 (单实例)
- **内存使用**: < 128MB 基础运行
- **流式响应**: 支持 60+ 秒长连接

### Compatibility Requirements
- **Platform Support**:
  - Linux: Ubuntu 20.04+, CentOS 8+, Alpine 3.15+
  - macOS: 11.0+ (Big Sur)
  - Windows: 10+ (通过 WSL2 推荐)
- **Dependency Versions**:
  - Python: 3.12+ (利用最新异步特性)
  - FastAPI: 0.100+ (确保 ASGI 支持)
  - httpx: 0.25+ (HTTP/2 支持)
- **Standards Compliance**:
  - RFC 7230 (HTTP/1.1 消息语法和路由)
  - RFC 7231 (HTTP 语义和内容)
  - SSE 规范 (流式响应)

### Security & Compliance
- **Security Requirements**:
  - 防重定向攻击 (follow_redirects=False)
  - 请求超时保护 (60秒)
  - 敏感信息过滤 (生产环境日志)
  - HTTP 头部安全过滤
- **Compliance Standards**:
  - 数据保护合规 (不记录敏感请求内容)
  - 企业安全标准 (可配置的安全策略)
- **Threat Model**:
  - DoS 攻击防护 (超时和连接限制)
  - 中间人攻击防护 (HTTPS 传输)
  - 资源耗尽防护 (连接池管理)

### Scalability & Reliability
- **Expected Load**:
  - 并发连接: 1000+
  - 请求速率: 10,000+ req/min
  - 数据传输: 1GB+ per minute
- **Availability Requirements**:
  - 正常运行时间: 99.9%
  - 故障恢复: < 30 秒
  - 优雅关闭: 确保连接正确关闭
- **Growth Projections**:
  - 水平扩展: 支持多实例负载均衡
  - 垂直扩展: 支持 8GB+ 内存使用
  - 地理分布: 支持多地域部署

## Technical Decisions & Rationale

### Decision Log
1. **单文件架构选择**:
   - **理由**: 简化部署和维护，功能高度内聚，符合项目规模
   - **权衡**: 降低复杂度 vs 未来扩展性限制
   - **替代方案**: 模块化拆分 (当前规模不必要)

2. **FastAPI + httpx 技术栈**:
   - **理由**: 现代异步框架，原生支持流式响应，生态完善
   - **权衡**: 学习成本 vs 开发效率
   - **替代方案**: Flask + aiohttp (较重), Node.js (技术栈不一致)

3. **RFC 7230 严格遵循**:
   - **理由**: 确保与各种 HTTP 客户端的最大兼容性
   - **实现**: 自动过滤 hop-by-hop 头部，正确处理 Content-Length
   - **权衡**: 标准遵循 vs 实现复杂度

4. **System Prompt 路由限制**:
   - **理由**: 仅对 `/v1/messages` 处理，避免影响其他 API 路由
   - **实现**: 路由匹配 + 条件处理逻辑
   - **设计哲学**: 最小化干预原则

5. **BackgroundTask 资源管理**:
   - **理由**: 解决流式响应连接过早关闭问题
   - **实现**: `StreamingResponse` + `BackgroundTask(resp.aclose)`
   - **权衡**: 复杂度增加 vs 连接安全

## Known Limitations

### 当前技术限制
- **单进程模型**:
  - **影响**: CPU 利用率受限，无法充分利用多核
  - **未来解决方案**: 多进程部署 + 负载均衡

- **内存状态**:
  - **影响**: 连接池和内存缓存无法跨实例共享
  - **未来解决方案**: Redis 外部缓存，连接池分离

### 功能限制
- **协议支持**:
  - **影响**: 暂不支持 WebSocket 和 HTTP/2 代理
  - **计划时间**: 6 个月内实现 WebSocket 支持

- **监控能力**:
  - **影响**: 缺乏详细的性能指标和分析
  - **计划时间**: 3 个月内添加 Prometheus metrics

### 扩展性限制
- **配置管理**:
  - **影响**: 缺乏动态配置更新能力
  - **解决方案**: 实现配置热重载机制

- **安全功能**:
  - **影响**: 缺乏访问控制和审计功能
  - **解决方案**: 添加 API Key 验证和访问日志

### 部署限制
- **平台依赖**:
  - **影响**: 依赖 Python 环境，部署复杂度较高
  - **解决方案**: 提供静态编译版本或多阶段构建 Docker 镜像

- **网络配置**:
  - **影响**: 在复杂网络环境中的配置可能较为复杂
  - **解决方案**: 提供网络诊断工具和配置向导