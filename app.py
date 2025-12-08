from fastapi import FastAPI, Request, Response
from fastapi.responses import StreamingResponse
from contextlib import asynccontextmanager
from starlette.background import BackgroundTask
from dotenv import load_dotenv
import httpx
import json
import os
from typing import Iterable
from urllib.parse import urlparse

# Shared HTTP client for connection pooling and proper lifecycle management
http_client: httpx.AsyncClient = None  # type: ignore


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Manage application lifespan events"""
    global http_client

    # 输出应用配置信息（只在 worker 进程启动时输出一次）
    print("=" * 60)
    print("Application Configuration:")
    print(f"  Base URL: {TARGET_BASE_URL}")
    print(f"  System Prompt Replacement: {SYSTEM_PROMPT_REPLACEMENT}")
    print(f"  System Prompt Insert Mode: {SYSTEM_PROMPT_BLOCK_INSERT_IF_NOT_EXIST}")
    print(f"  Server Port: {PORT}")
    print(f"  Custom Headers: {len(CUSTOM_HEADERS)} headers loaded")
    if CUSTOM_HEADERS:
        print(f"  Custom Headers Keys: {list(CUSTOM_HEADERS.keys())}")
    print(f"  Debug Mode: {DEBUG_MODE}")
    print(f"  Hot Reload: {DEBUG_MODE}")
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

    # Shutdown: Close HTTP client
    await http_client.aclose()

# ===== 基础配置 =====
# 主站：https://anyrouter.top
load_dotenv()
TARGET_BASE_URL = os.getenv("API_BASE_URL", "https://anyrouter.top")
PRESERVE_HOST = False  # 是否保留原始 Host

# System prompt 替换配置
# 设置为字符串以替换请求体中 system 数组的第一个元素的 text 内容
# 设置为 None 则保持原样不修改
# 通过环境变量 SYSTEM_PROMPT_REPLACEMENT 配置，默认为 None
SYSTEM_PROMPT_REPLACEMENT = os.getenv("SYSTEM_PROMPT_REPLACEMENT")  # 例如: "你是一个有用的AI助手"

# System prompt 插入模式配置
# 设置为 true/1/yes 时，启用插入模式而非替换模式
# 通过环境变量 SYSTEM_PROMPT_BLOCK_INSERT_IF_NOT_EXIST 配置，默认为 false
SYSTEM_PROMPT_BLOCK_INSERT_IF_NOT_EXIST = os.getenv("SYSTEM_PROMPT_BLOCK_INSERT_IF_NOT_EXIST", "false").lower() in ("true", "1", "yes")

# 关键字常量定义
# 用于判断是否需要执行替换操作
CLAUDE_CODE_KEYWORD = "Claude Code"

# 调试模式配置
DEBUG_MODE = os.getenv("DEBUG_MODE", "false").lower() in ("true", "1", "yes")

# 服务端口配置
PORT = int(os.getenv("PORT", "8088"))

app = FastAPI(
    title="Anthropic Transparent Proxy",
    version="1.1",
    lifespan=lifespan
)

# 自定义 Header 配置
# 从 env/.env.headers.json 文件加载，如果文件不存在或解析失败，则使用空字典 {}
def load_custom_headers() -> dict:
    """
    从 env/.env.headers.json 文件加载自定义请求头配置

    Returns:
        dict: 自定义请求头字典，如果加载失败则返回空字典 {}
    """
    headers_file = "env/.env.headers.json"

    # 检查文件是否存在
    if not os.path.exists(headers_file):
        print(f"[Custom Headers] Config file '{headers_file}' not found, using default empty dict {{}}")
        return {}

    # 尝试读取和解析 JSON 文件
    try:
        with open(headers_file, 'r', encoding='utf-8') as f:
            headers = json.load(f)

        # 验证是否为字典类型
        if not isinstance(headers, dict):
            print(f"[Custom Headers] Config file content is not a dict (type: {type(headers)}), using default empty dict {{}}")
            return {}

        # 过滤掉以 __ 开头的注释字段
        filtered_headers = {k: v for k, v in headers.items() if not k.startswith("__")}

        print(f"[Custom Headers] Successfully loaded {len(filtered_headers)} custom headers from '{headers_file}'")
        if filtered_headers:
            print(f"[Custom Headers] Loaded headers: {list(filtered_headers.keys())}")

        return filtered_headers

    except json.JSONDecodeError as e:
        print(f"[Custom Headers] Failed to parse JSON from '{headers_file}': {e}, using default empty dict {{}}")
        return {}
    except Exception as e:
        print(f"[Custom Headers] Failed to load '{headers_file}': {e}, using default empty dict {{}}")
        return {}


CUSTOM_HEADERS = load_custom_headers()

HOP_BY_HOP_HEADERS = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
}


# ===== 工具函数 =====

def filter_request_headers(headers: Iterable[tuple]) -> dict:
    out = {}
    for k, v in headers:
        lk = k.lower()
        if lk in HOP_BY_HOP_HEADERS:
            continue
        if lk == "host" and not PRESERVE_HOST:
            continue
        # 移除 Content-Length，让 httpx 根据实际内容自动计算
        # 因为我们可能会修改请求体，导致长度改变
        if lk == "content-length":
            continue
        out[k] = v
    return out


def filter_response_headers(headers: Iterable[tuple]) -> dict:
    out = {}
    for k, v in headers:
        lk = k.lower()
        if lk in HOP_BY_HOP_HEADERS:
            continue
        # 移除 Content-Length，避免流式响应时长度不匹配
        # StreamingResponse 会自动处理传输编码
        if lk == "content-length":
            continue
        out[k] = v
    return out


def process_request_body(body: bytes) -> bytes:
    """
    处理请求体,替换 system 数组中第一个元素的 text 内容

    注意：此函数仅在 proxy() 中处理 /v1/messages 路由时被调用
    其他路由（如 /v1/completions, /v1/models 等）跳过此处理

    Args:
        body: 原始请求体（bytes）

    Returns:
        处理后的请求体（bytes），如果无法处理则返回原始 body
    """
    # 如果未配置替换文本，直接返回原始 body
    if SYSTEM_PROMPT_REPLACEMENT is None:
        print("[System Replacement] Not configured, keeping original body")
        # try:
        #     print(f"[System Replacement None] Original system[0].text: {json.loads(body.decode('utf-8'))['system'][0]['text']}")
        # except (json.JSONDecodeError, UnicodeDecodeError, KeyError, IndexError, TypeError) as e:
        #     print(f"[System Replacement None] Failed to parse or access system prompt: {e}")
        return body

    # 尝试解析 JSON
    try:
        data = json.loads(body.decode('utf-8'))
        print("[System Replacement] Successfully parsed JSON body")
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        print(f"[System Replacement] Failed to parse JSON: {e}, keeping original body")
        return body

    # 检查 system 字段是否存在且为列表
    if "system" not in data:
        print("[System Replacement] No 'system' field found, keeping original body")
        return body

    if not isinstance(data["system"], list):
        print(f"[System Replacement] 'system' field is not a list (type: {type(data['system'])}), keeping original body")
        return body

    if len(data["system"]) == 0:
        print("[System Replacement] 'system' array is empty, keeping original body")
        return body

    # 获取第一个元素
    first_element = data["system"][0]

    # 检查第一个元素是否有 'text' 字段
    if not isinstance(first_element, dict) or "text" not in first_element:
        print(f"[System Replacement] First element doesn't have 'text' field, keeping original body")
        return body

    # 记录原始内容
    original_text = first_element["text"]
    print(f"[System Replacement] Original system[0].text: {original_text[:100]}..." if len(original_text) > 100 else f"[System Replacement] Original system[0].text: {original_text}")

    # 判断是否启用插入模式
    if SYSTEM_PROMPT_BLOCK_INSERT_IF_NOT_EXIST:
        # 插入模式：检查是否包含关键字（忽略大小写）
        if CLAUDE_CODE_KEYWORD.lower() in original_text.lower():
            # 包含关键字：执行替换
            first_element["text"] = SYSTEM_PROMPT_REPLACEMENT
            print(f"[System Replacement] Found '{CLAUDE_CODE_KEYWORD}', replacing with: {SYSTEM_PROMPT_REPLACEMENT[:100]}..." if len(SYSTEM_PROMPT_REPLACEMENT) > 100 else f"[System Replacement] Found '{CLAUDE_CODE_KEYWORD}', replacing with: {SYSTEM_PROMPT_REPLACEMENT}")
        else:
            # 不包含关键字：执行插入
            new_element = {
                "type": "text",
                "text": SYSTEM_PROMPT_REPLACEMENT,
                "cache_control": {
                    "type": "ephemeral"
                }
            }
            data["system"].insert(0, new_element)
            print(f"[System Replacement] '{CLAUDE_CODE_KEYWORD}' not found, inserting at position 0: {SYSTEM_PROMPT_REPLACEMENT[:100]}..." if len(SYSTEM_PROMPT_REPLACEMENT) > 100 else f"[System Replacement] '{CLAUDE_CODE_KEYWORD}' not found, inserting at position 0: {SYSTEM_PROMPT_REPLACEMENT}")
            print(f"[System Replacement] Array length changed: {len(data['system'])-1} -> {len(data['system'])}")
    else:
        # 原始模式：直接替换
        first_element["text"] = SYSTEM_PROMPT_REPLACEMENT
        print(f"[System Replacement] Replaced with: {SYSTEM_PROMPT_REPLACEMENT[:100]}..." if len(SYSTEM_PROMPT_REPLACEMENT) > 100 else f"[System Replacement] Replaced with: {SYSTEM_PROMPT_REPLACEMENT}")

    print(f"[System Replacement] original_text == SYSTEM_PROMPT_REPLACEMENT:{SYSTEM_PROMPT_REPLACEMENT == original_text}")

    # 转换回 JSON bytes
    try:
        # 这里必须加 separators 压缩空格，我也不知道为什么有空格不行。。。
        modified_body = json.dumps(data, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
        print(f"[System Replacement] Successfully modified body (original size: {len(body)} bytes, new size: {len(modified_body)} bytes)")
        return modified_body
    except Exception as e:
        print(f"[System Replacement] Failed to serialize modified JSON: {e}, keeping original body")
        return body


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


# ===== 主代理逻辑 =====

@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"])
async def proxy(path: str, request: Request):
    # 构造目标 URL
    query = request.url.query
    target_url = f"{TARGET_BASE_URL}/{path}"
    if query:
        target_url += f"?{query}"

    # 读取 body
    body = await request.body()
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

    # 复制并过滤请求头
    incoming_headers = list(request.headers.items())
    forward_headers = filter_request_headers(incoming_headers)

    # 设置 Host
    if not PRESERVE_HOST:
        parsed = urlparse(TARGET_BASE_URL)
        forward_headers["Host"] = parsed.netloc

    # 注入自定义 Header
    for k, v in CUSTOM_HEADERS.items():
        forward_headers[k] = v

    # 添加 X-Forwarded-For
    client_host = request.client.host if request.client else None
    if client_host:
        existing = forward_headers.get("X-Forwarded-For")
        forward_headers["X-Forwarded-For"] = f"{existing}, {client_host}" if existing else client_host

    # 发起上游请求并流式处理响应
    try:
        # 构建请求但不使用 context manager
        req = http_client.build_request(
            method=request.method,
            url=target_url,
            headers=forward_headers,
            content=body,
        )

        # 发送请求并开启流式模式 (不使用 async with)
        resp = await http_client.send(req, stream=True)

        # 过滤响应头
        response_headers = filter_response_headers(resp.headers.items())

        # 异步生成器:流式读取响应内容
        async def iter_response():
            try:
                async for chunk in resp.aiter_bytes():
                    yield chunk
            except Exception as e:
                # 优雅处理客户端断开连接
                if DEBUG_MODE:
                    print(f"[Stream Error] {e}")
                # 静默处理,避免日志污染
            finally:
                # 确保资源被释放 (作为备份,主要由 BackgroundTask 处理)
                pass

        # 使用 BackgroundTask 在响应完成后关闭连接
        return StreamingResponse(
            iter_response(),
            status_code=resp.status_code,
            headers=response_headers,
            background=BackgroundTask(resp.aclose),  # FastAPI 负责在合适时机关闭
        )

    except httpx.RequestError as e:
        return Response(content=f"Upstream request failed: {e}", status_code=502)


if __name__ == "__main__":
    import uvicorn
    # 开发模式启用热重载，生产模式禁用（通过 DEBUG_MODE 环境变量控制）
    uvicorn.run("app:app", host="0.0.0.0", port=PORT, reload=DEBUG_MODE)