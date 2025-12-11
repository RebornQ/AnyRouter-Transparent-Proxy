"""
AnyRouter 透明代理 - 主应用模块

基于 FastAPI 的轻量级透明 HTTP 代理服务
"""

from fastapi import FastAPI, Request, Response
from fastapi.responses import StreamingResponse, RedirectResponse
from contextlib import asynccontextmanager
from starlette.background import BackgroundTask
import httpx
import json
import os
import time
import asyncio

# 导入配置
from .config import (
    TARGET_BASE_URL,
    DEBUG_MODE,
    PORT,
    ENABLE_DASHBOARD,
    DASHBOARD_API_KEY,
    CUSTOM_HEADERS
)

# 导入统计服务
from .services.stats import (
    record_request_start,
    record_request_success,
    record_request_error,
    broadcast_log_message,
    periodic_stats_update,
    log_producer
)

# 导入代理服务
from .services.proxy import (
    process_request_body,
    filter_response_headers,
    prepare_forward_headers
)

# 导入编码工具
from .utils.encoding import ensure_unicode

# 导入 Admin 路由
from .routers.admin import router as admin_router

# Shared HTTP client for connection pooling and proper lifecycle management
http_client: httpx.AsyncClient = None  # type: ignore


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Manage application lifespan events"""
    global http_client

    # 启动定时统计更新任务
    stats_task = asyncio.create_task(periodic_stats_update())

    # 启动日志生产者任务
    log_producer_task = asyncio.create_task(log_producer())

    # 输出应用配置信息（只在 worker 进程启动时输出一次）
    print("=" * 60)
    print("Application Configuration:")
    print(f"  Base URL: {TARGET_BASE_URL}")
    print(f"  Server Port: {PORT}")
    print(f"  Custom Headers: {len(CUSTOM_HEADERS)} headers loaded")
    if CUSTOM_HEADERS:
        print(f"  Custom Headers Keys: {list(CUSTOM_HEADERS.keys())}")
    print(f"  Debug Mode: {DEBUG_MODE}")
    print(f"  Hot Reload: {DEBUG_MODE}")
    print(f"  Dashboard Enabled: {ENABLE_DASHBOARD}")
    if ENABLE_DASHBOARD:
        print(f"  Dashboard API Key Configured: {'Yes' if DASHBOARD_API_KEY else 'No'}")
        if DASHBOARD_API_KEY:
            print(f"  Dashboard Access: http://localhost:{PORT}/admin")
    print("=" * 60)

    # 读取代理配置
    http_proxy = os.getenv("HTTP_PROXY")
    https_proxy = os.getenv("HTTPS_PROXY")

    # 构建 mounts 配置（httpx 0.28.0+ 的新语法）
    mounts = {}

    if http_proxy:
        # 确保代理 URL 包含协议
        if "://" not in http_proxy:
            http_proxy = f"http://{http_proxy}"
        mounts["http://"] = httpx.AsyncHTTPTransport(proxy=http_proxy)
        print(f"HTTP Proxy configured: {http_proxy}")

    if https_proxy:
        # 注意：HTTPS 代理通常也使用 http:// 协议（这不是错误！）
        if "://" not in https_proxy:
            https_proxy = f"http://{https_proxy}"
        mounts["https://"] = httpx.AsyncHTTPTransport(proxy=https_proxy)
        print(f"HTTPS Proxy configured: {https_proxy}")

    try:
        # 使用新的 mounts 参数初始化客户端
        if mounts:
            http_client = httpx.AsyncClient(
                follow_redirects=False,
                timeout=60.0,
                mounts=mounts
            )
            print(f"HTTP client initialized with proxy mounts: {list(mounts.keys())}")
        else:
            http_client = httpx.AsyncClient(
                follow_redirects=False,
                timeout=60.0
            )
            print("HTTP client initialized without proxy")
    except Exception as e:
        print(f"Failed to initialize HTTP client: {e}")
        raise

    print("=" * 60)

    yield

    # Shutdown: Close HTTP client and stop background tasks
    stats_task.cancel()
    log_producer_task.cancel()

    try:
        await stats_task
    except asyncio.CancelledError:
        pass

    try:
        await log_producer_task
    except asyncio.CancelledError:
        pass

    await http_client.aclose()


app = FastAPI(
    title="Anthropic Transparent Proxy",
    version="1.1",
    lifespan=lifespan
)

# 注册 Admin 路由
app.include_router(admin_router)


# ===== 健康检查端点 =====

@app.get("/health")
async def health_check():
    """
    健康检查端点，用于容器健康检查和服务状态监控
    不依赖上游服务，仅检查代理服务本身是否正常运行
    """
    return {
        "status": "healthy",
        "service": "anthropic-transparent-proxy"
    }


@app.api_route("/", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"])
async def root_redirect(request: Request):
    """
    根路径：浏览器访问时重定向到 /admin，API 访问保持代理行为
    """
    accept_header = request.headers.get("accept", "")
    wants_html = "text/html" in accept_header or "application/xhtml+xml" in accept_header

    if wants_html:
        return RedirectResponse(url="/admin", status_code=307)

    return await proxy("", request)


# ===== 主代理逻辑 =====

@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"])
async def proxy(path: str, request: Request):
    # 记录请求开始
    start_time = time.time()
    body = await request.body()

    # 跳过 Dashboard 相关路径的统计
    if not path.startswith("api/admin") and not path.startswith("admin"):
        request_id = await record_request_start(path, request.method, len(body))
    else:
        request_id = None

    # 构造目标 URL
    query = request.url.query
    target_url = f"{TARGET_BASE_URL}/{path}"
    if query:
        target_url += f"?{query}"

    # 仅测试环境打印详细日志
    if DEBUG_MODE:
        try:
            data = json.loads(body.decode('utf-8'))
            print(f"[Proxy] Original body ({len(body)} bytes): {json.dumps(data, indent=4)}")
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            print(f"[Proxy] Failed to parse JSON: {e}")
    else:
        print(f"[Proxy] Request: {request.method} {path}")
        print(f"[Proxy] Original body ({len(body)} bytes): {body[:200]}..." if len(body) > 200 else f"[Proxy] Original body: {body}")

    # 处理请求体（替换 system prompt）
    # 仅在路由为 /v1/messages 时执行处理
    print(f"[Proxy] Processing request for path: {path}")
    if path == "v1/messages" or path == "v1/messages/":
        body = process_request_body(body)

    # 准备转发的请求头
    incoming_headers = list(request.headers.items())
    client_host = request.client.host if request.client else None
    forward_headers = prepare_forward_headers(incoming_headers, client_host)

    # 发起上游请求并流式处理响应
    response_time = 0
    bytes_received = 0
    error_response_content = b""  # 新增：缓存错误响应内容（仅当状态码 >= 400 时）
    try:
        # 构建请求但不使用 context manager
        req = http_client.build_request(
            method=request.method,
            url=target_url,
            headers=forward_headers,
            content=body,
        )

        # 记录请求开始日志
        if request_id:
            await broadcast_log_message(
                "INFO",
                f"Request started: {request.method} {path}",
                path,
                request_id
            )

        # 发送请求并开启流式模式 (不使用 async with)
        resp = await http_client.send(req, stream=True)

        # 过滤响应头
        response_headers = filter_response_headers(resp.headers.items())

        # 统计响应时间
        response_time = time.time() - start_time

        # 异步生成器:流式读取响应内容并统计字节数
        async def iter_response():
            nonlocal bytes_received
            nonlocal error_response_content
            try:
                async for chunk in resp.aiter_bytes():
                    bytes_received += len(chunk)
                    # 如果是错误响应，缓存内容（限制 50KB）
                    if resp.status_code >= 400 and len(error_response_content) < 50*1024:
                        error_response_content += chunk
                    yield chunk
            except Exception as e:
                # 优雅处理客户端断开连接
                if DEBUG_MODE:
                    print(f"[Stream Error] {e}")
                if request_id:
                    await broadcast_log_message(
                        "WARNING",
                        f"Client disconnected during response: {e}",
                        path,
                        request_id
                    )
                # 静默处理,避免日志污染
            finally:
                # 确保资源被释放 (作为备份,主要由 BackgroundTask 处理)
                pass

        # 创建响应完成后的统计任务
        async def close_and_record():
            await resp.aclose()
            if request_id:
                if resp.status_code < 400:
                    await record_request_success(
                        request_id,
                        path,
                        request.method,
                        bytes_received,
                        response_time,
                        resp.status_code
                    )
                    await broadcast_log_message(
                        "INFO",
                        f"Request completed: {request.method} {path} - {resp.status_code} ({bytes_received} bytes, {response_time*1000:.1f}ms)",
                        path,
                        request_id
                    )
                else:
                    # 使用缓存的响应内容
                    response_content = ensure_unicode(error_response_content) if error_response_content else None
                    if DEBUG_MODE:
                        print(f"[Proxy] Response: {response_content}")
                    else:
                        err_content_len = len(error_response_content)
                        print(f"[Proxy] Response ({err_content_len} bytes): {response_content[:200]}..." if err_content_len > 200 else f"[Proxy] Response: {response_content}")

                    # 记录错误到统计服务
                    await record_request_error(
                        request_id,
                        path,
                        request.method,
                        f"HTTP {resp.status_code}: {resp.reason_phrase}",
                        response_time,
                        response_content,  # 新增参数
                        resp.status_code
                    )
                    # 广播错误日志到 SSE
                    await broadcast_log_message(
                        "ERROR",
                        f"Request failed: {request.method} {path} - {resp.status_code} {resp.reason_phrase}",
                        path,
                        request_id,
                        response_content  # 新增参数
                    )

        # 使用 BackgroundTask 在响应完成后关闭连接和记录统计
        return StreamingResponse(
            iter_response(),
            status_code=resp.status_code,
            headers=response_headers,
            background=BackgroundTask(close_and_record),
        )

    except httpx.RequestError as e:
        # 记录请求错误
        if request_id:
            await record_request_error(
                request_id,
                path,
                request.method,
                str(e),
                time.time() - start_time,
                None,
                502
            )
            await broadcast_log_message(
                "ERROR",
                f"Upstream request failed: {request.method} {path} - {str(e)}",
                path,
                request_id
            )
        return Response(content=f"Upstream request failed: {e}", status_code=502)


if __name__ == "__main__":
    import uvicorn
    # 开发模式启用热重载，生产模式禁用（通过 DEBUG_MODE 环境变量控制）
    # 注意：使用模块路径而非文件路径，以支持相对导入
    uvicorn.run("backend.app:app", host="0.0.0.0", port=PORT, reload=DEBUG_MODE)
