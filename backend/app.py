from fastapi import FastAPI, Request, Response, HTTPException, Depends
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from contextlib import asynccontextmanager
from starlette.background import BackgroundTask
from sse_starlette.sse import EventSourceResponse
from dotenv import load_dotenv
import httpx
import json
import os
import time
import asyncio
from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import Iterable, Optional
from urllib.parse import urlparse

# Shared HTTP client for connection pooling and proper lifecycle management
http_client: httpx.AsyncClient = None  # type: ignore

# ===== 统计数据收集器 =====
# 全局统计数据（线程安全）
stats_lock = asyncio.Lock()
request_stats = {
    "total_requests": 0,
    "successful_requests": 0,
    "failed_requests": 0,
    "total_bytes_sent": 0,
    "total_bytes_received": 0,
    "start_time": time.time()
}

# 性能指标（最近的请求）
recent_requests = deque(maxlen=1000)  # 保存最近1000个请求的性能数据
error_logs = deque(maxlen=500)  # 保存最近500个错误

# 按路径分组的统计
path_stats = defaultdict(lambda: {
    "count": 0,
    "bytes": 0,
    "errors": 0,
    "avg_response_time": 0
})

# 按时间窗口的统计（用于图表）
time_window_stats = {
    "requests_per_minute": deque(maxlen=1440),  # 24小时的分钟数据
    "errors_per_minute": deque(maxlen=1440),
    "bytes_per_minute": deque(maxlen=1440)
}

# 日志流相关
log_subscribers = set()  # SSE连接订阅者
log_queue = asyncio.Queue(maxsize=1000)  # 日志消息队列


async def record_request_start(path: str, method: str, bytes_sent: int) -> str:
    """记录请求开始，返回请求ID"""
    request_id = f"{int(time.time() * 1000)}-{id(asyncio.current_task())}"

    async with stats_lock:
        request_stats["total_requests"] += 1
        request_stats["total_bytes_sent"] += bytes_sent
        path_stats[path]["count"] += 1
        path_stats[path]["bytes"] += bytes_sent

    return request_id


async def record_request_success(request_id: str, path: str, bytes_received: int, response_time: float):
    """记录成功请求"""
    async with stats_lock:
        request_stats["successful_requests"] += 1
        request_stats["total_bytes_received"] += bytes_received

        # 更新路径统计
        current_avg = path_stats[path]["avg_response_time"]
        count = path_stats[path]["count"]
        path_stats[path]["avg_response_time"] = (current_avg * (count - 1) + response_time) / count

        # 记录最近请求
        recent_requests.append({
            "request_id": request_id,
            "path": path,
            "status": "success",
            "bytes": bytes_received,
            "response_time": response_time,
            "timestamp": time.time()
        })


async def record_request_error(request_id: str, path: str, error_msg: str, response_time: float = 0):
    """记录请求错误"""
    async with stats_lock:
        request_stats["failed_requests"] += 1
        path_stats[path]["errors"] += 1

        # 记录错误日志
        error_logs.append({
            "request_id": request_id,
            "path": path,
            "error": error_msg,
            "timestamp": time.time(),
            "response_time": response_time
        })

        # 记录最近请求
        recent_requests.append({
            "request_id": request_id,
            "path": path,
            "status": "error",
            "error": error_msg,
            "response_time": response_time,
            "timestamp": time.time()
        })


async def update_time_window_stats():
    """更新时间窗口统计（每分钟调用一次）"""
    current_time = time.time()
    current_minute = datetime.fromtimestamp(current_time).strftime("%Y-%m-%d %H:%M")

    async with stats_lock:
        # 计算本分钟的请求数
        minute_requests = sum(1 for req in recent_requests
                            if req["timestamp"] > current_time - 60)
        minute_errors = sum(1 for req in recent_requests
                          if req["status"] == "error" and req["timestamp"] > current_time - 60)
        minute_bytes = sum(req.get("bytes", 0) for req in recent_requests
                         if req["timestamp"] > current_time - 60)

        time_window_stats["requests_per_minute"].append({
            "time": current_minute,
            "count": minute_requests
        })
        time_window_stats["errors_per_minute"].append({
            "time": current_minute,
            "count": minute_errors
        })
        time_window_stats["bytes_per_minute"].append({
            "time": current_minute,
            "count": minute_bytes
        })


async def broadcast_log_message(level: str, message: str, path: str = "", request_id: str = ""):
    """广播日志消息到所有订阅者"""
    log_entry = {
        "timestamp": time.time(),
        "level": level,
        "message": message,
        "path": path,
        "request_id": request_id,
        "formatted_time": datetime.fromtimestamp(time.time()).strftime("%Y-%m-%d %H:%M:%S")
    }

    try:
        # 添加到队列（如果队列满了，丢弃最旧的消息）
        if log_queue.full():
            await log_queue.get_nowait()
        await log_queue.put(log_entry)

        # 广播给订阅者
        for subscriber_queue in log_subscribers.copy():
            try:
                await subscriber_queue.put(log_entry)
            except Exception:
                # 订阅者断开连接，移除
                log_subscribers.discard(subscriber_queue)

    except Exception as e:
        print(f"[Log Stream] Failed to broadcast log message: {e}")


async def log_producer():
    """日志生产者 - 将代理函数的日志转换为流式日志"""
    # 这里可以根据需要添加更多日志来源
    while True:
        try:
            # 定期发送系统状态日志
            await asyncio.sleep(30)  # 每30秒发送一次系统状态
            async with stats_lock:
                current_requests = request_stats["total_requests"]
                current_errors = request_stats["failed_requests"]

            system_log = {
                "timestamp": time.time(),
                "level": "INFO",
                "message": f"System status: {current_requests} total requests, {current_errors} errors",
                "type": "system_status",
                "formatted_time": datetime.fromtimestamp(time.time()).strftime("%Y-%m-%d %H:%M:%S")
            }

            for subscriber_queue in log_subscribers.copy():
                try:
                    await subscriber_queue.put(system_log)
                except Exception:
                    log_subscribers.discard(subscriber_queue)

        except Exception as e:
            print(f"[Log Stream] Error in log producer: {e}")
            await asyncio.sleep(5)  # 出错后等待5秒再继续


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
    print(f"  System Prompt Replacement: {SYSTEM_PROMPT_REPLACEMENT}")
    print(f"  System Prompt Insert Mode: {SYSTEM_PROMPT_BLOCK_INSERT_IF_NOT_EXIST}")
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


async def periodic_stats_update():
    """定期更新统计数据"""
    while True:
        try:
            await update_time_window_stats()
        except Exception as e:
            print(f"[Stats] Failed to update time window stats: {e}")

        # 每分钟更新一次
        await asyncio.sleep(60)

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

# Dashboard 配置
# 是否启用 Web 管理面板
ENABLE_DASHBOARD = os.getenv("ENABLE_DASHBOARD", "false").lower() in ("true", "1", "yes")
# Dashboard API Key 用于认证
DASHBOARD_API_KEY = os.getenv("DASHBOARD_API_KEY", "")

app = FastAPI(
    title="Anthropic Transparent Proxy",
    version="1.1",
    lifespan=lifespan
)

# Dashboard 认证方案
security = HTTPBearer(auto_error=False)

# 配置更新请求模型
class ConfigUpdateRequest(BaseModel):
    custom_headers: Optional[dict] = None

async def verify_dashboard_api_key(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> bool:
    """
    验证 Dashboard API Key
    已移除认证检查，允许直接访问

    Args:
        credentials: HTTP Bearer Token 凭据（忽略）

    Returns:
        bool: 总是返回 True
    """
    # 如果未启用 Dashboard，直接拒绝访问
    if not ENABLE_DASHBOARD:
        raise HTTPException(status_code=403, detail="Dashboard is disabled")

    # 直接返回 True，不再检查 API Key
    return True

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

# 专门处理 /admin 路径的路由（必须在代理路由之前）
@app.get("/admin")
@app.get("/admin/{path:path}")
async def admin_static(path: str = ""):
    """处理静态文件请求"""
    if not ENABLE_DASHBOARD:
        raise HTTPException(status_code=403, detail="Dashboard is disabled")

    # 构建静态文件路径
    file_path = os.path.join("static", path if path else "index.html")

    # 如果路径为空，返回 index.html
    if not path:
        file_path = os.path.join("static", "index.html")

    # 检查文件是否存在
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    # 返回文件内容
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 根据文件扩展名设置 Content-Type
        if file_path.endswith('.html'):
            return Response(content=content, media_type="text/html")
        elif file_path.endswith('.css'):
            return Response(content=content, media_type="text/css")
        elif file_path.endswith('.js'):
            return Response(content=content, media_type="application/javascript")
        else:
            return Response(content=content)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading file: {e}")

# ===== 工具函数 =====

def format_bytes(bytes_count: int) -> str:
    """格式化字节数为友好显示"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_count < 1024.0:
            return f"{bytes_count:.1f} {unit}"
        bytes_count /= 1024.0
    return f"{bytes_count:.1f} PB"

def calculate_percentiles(values: list, percentiles: list = [50, 95, 99]) -> dict:
    """计算百分位数"""
    if not values:
        return {p: 0 for p in percentiles}

    sorted_values = sorted(values)
    n = len(sorted_values)
    return {p: sorted_values[int(p * n / 100)] for p in percentiles}

async def get_time_filtered_data(start_time: float = None, end_time: float = None) -> tuple:
    """获取时间过滤的数据"""
    current_time = time.time()

    # 默认时间范围：最近1小时
    if not start_time:
        start_time = current_time - 3600
    if not end_time:
        end_time = current_time

    async with stats_lock:
        # 过滤最近的请求
        filtered_requests = [
            req for req in recent_requests
            if start_time <= req["timestamp"] <= end_time
        ]

        # 过滤错误日志
        filtered_errors = [
            error for error in error_logs
            if start_time <= error["timestamp"] <= end_time
        ]

        # 过滤时间窗口统计
        filtered_time_series = {
            "requests_per_minute": [
                data for data in time_window_stats["requests_per_minute"]
                if start_time <= datetime.strptime(data["time"], "%Y-%m-%d %H:%M").timestamp() <= end_time
            ],
            "errors_per_minute": [
                data for data in time_window_stats["errors_per_minute"]
                if start_time <= datetime.strptime(data["time"], "%Y-%m-%d %H:%M").timestamp() <= end_time
            ],
            "bytes_per_minute": [
                data for data in time_window_stats["bytes_per_minute"]
                if start_time <= datetime.strptime(data["time"], "%Y-%m-%d %H:%M").timestamp() <= end_time
            ]
        }

    return filtered_requests, filtered_errors, filtered_time_series


# ===== Dashboard API 端点 =====

@app.get("/api/admin/health")
async def admin_health(authenticated: bool = Depends(verify_dashboard_api_key)):
    """Dashboard 健康检查端点"""
    return {
        "status": "ok",
        "dashboard_enabled": ENABLE_DASHBOARD,
        "timestamp": time.time()
    }


@app.get("/api/admin/config")
async def get_config(authenticated: bool = Depends(verify_dashboard_api_key)):
    """获取当前配置信息"""
    return {
        "target_base_url": TARGET_BASE_URL,
        "preserve_host": PRESERVE_HOST,
        "system_prompt_replacement": SYSTEM_PROMPT_REPLACEMENT,
        "system_prompt_block_insert_if_not_exist": SYSTEM_PROMPT_BLOCK_INSERT_IF_NOT_EXIST,
        "debug_mode": DEBUG_MODE,
        "port": PORT,
        "custom_headers": CUSTOM_HEADERS,
        "dashboard_enabled": ENABLE_DASHBOARD
    }


@app.put("/api/admin/config")
async def update_config(config_data: ConfigUpdateRequest, authenticated: bool = Depends(verify_dashboard_api_key)):
    """更新配置信息（仅支持运行时动态配置）"""
    try:
        updated_fields = []

        # 更新自定义请求头
        if config_data.custom_headers is not None:
            if isinstance(config_data.custom_headers, dict):
                global CUSTOM_HEADERS
                CUSTOM_HEADERS = config_data.custom_headers
                updated_fields.append("custom_headers")

                # 保存到文件
                headers_file = "env/.env.headers.json"
                try:
                    os.makedirs("env", exist_ok=True)
                    with open(headers_file, 'w', encoding='utf-8') as f:
                        json.dump(CUSTOM_HEADERS, f, ensure_ascii=False, indent=2)
                    print(f"[Config] Saved custom headers to {headers_file}")
                except Exception as e:
                    print(f"[Config] Failed to save custom headers: {e}")
                    raise HTTPException(status_code=500, detail=f"保存配置失败: {e}")
            else:
                raise HTTPException(status_code=400, detail="custom_headers 必须是字典类型")

        # 注意：System Prompt 等核心配置需要环境变量修改，这里仅返回说明
        return {
            "success": True,
            "updated_fields": updated_fields,
            "message": "配置更新成功。注意：某些核心配置需要重启服务后生效。",
            "current_config": await get_config(authenticated)
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新配置失败: {str(e)}")


@app.get("/api/admin/stats")
async def get_stats(
    authenticated: bool = Depends(verify_dashboard_api_key),
    start_time: Optional[float] = None,
    end_time: Optional[float] = None,
    limit: Optional[int] = 100
):
    """获取系统统计信息"""
    try:
        filtered_requests, filtered_errors, filtered_time_series = await get_time_filtered_data(start_time, end_time)

        # 计算基本统计
        total_filtered_requests = len(filtered_requests)
        successful_filtered_requests = len([r for r in filtered_requests if r["status"] == "success"])
        error_filtered_requests = len([r for r in filtered_requests if r["status"] == "error"])

        # 计算响应时间统计
        response_times = [r["response_time"] * 1000 for r in filtered_requests if r["response_time"] > 0]  # 转换为毫秒
        response_time_stats = calculate_percentiles(response_times, [50, 95, 99])

        # 计算QPS（每秒请求数）
        time_range = (end_time or time.time()) - (start_time or (time.time() - 3600))
        qps = total_filtered_requests / time_range if time_range > 0 else 0

        # 计算总字节数
        total_bytes_sent = sum(r.get("bytes", 0) for r in filtered_requests)

        # 获取路径统计
        path_stats_filtered = {}
        async with stats_lock:
            for path, stats in path_stats.items():
                if stats["count"] > 0:  # 只显示有请求的路径
                    path_stats_filtered[path] = {
                        "count": stats["count"],
                        "bytes": stats["bytes"],
                        "errors": stats["errors"],
                        "avg_response_time": round(stats["avg_response_time"] * 1000, 2),  # 毫秒
                        "success_rate": (stats["count"] - stats["errors"]) / stats["count"] if stats["count"] > 0 else 1.0
                    }

        # 按请求数排序路径
        top_paths = sorted(path_stats_filtered.items(), key=lambda x: x[1]["count"], reverse=True)[:10]

        return {
            "summary": {
                "total_requests": total_filtered_requests,
                "successful_requests": successful_filtered_requests,
                "failed_requests": error_filtered_requests,
                "success_rate": successful_filtered_requests / total_filtered_requests if total_filtered_requests > 0 else 1.0,
                "avg_response_time": sum(response_times) / len(response_times) if response_times else 0,
                "requests_per_second": qps,
                "total_bytes_sent": total_bytes_sent,
                "total_bytes_sent_formatted": format_bytes(total_bytes_sent),
                "uptime_seconds": time.time() - request_stats["start_time"]
            },
            "performance": {
                "response_time_ms": {
                    "p50": response_time_stats.get(50, 0),
                    "p95": response_time_stats.get(95, 0),
                    "p99": response_time_stats.get(99, 0)
                }
            },
            "time_series": filtered_time_series,
            "top_paths": dict(top_paths),
            "recent_requests": filtered_requests[-limit:] if limit > 0 else filtered_requests
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取统计数据失败: {str(e)}")


@app.get("/api/admin/errors")
async def get_errors(
    authenticated: bool = Depends(verify_dashboard_api_key),
    start_time: Optional[float] = None,
    end_time: Optional[float] = None,
    limit: Optional[int] = 50,
    offset: Optional[int] = 0,
    path_filter: Optional[str] = None
):
    """获取错误信息"""
    try:
        filtered_requests, filtered_errors, _ = await get_time_filtered_data(start_time, end_time)

        # 应用路径过滤
        if path_filter:
            filtered_errors = [e for e in filtered_errors if path_filter.lower() in e["path"].lower()]

        # 计算总数
        total_errors = len(filtered_errors)

        # 应用分页
        paginated_errors = filtered_errors[offset:offset + limit] if limit > 0 else filtered_errors

        # 格式化错误数据
        formatted_errors = []
        for error in paginated_errors:
            formatted_errors.append({
                "request_id": error["request_id"],
                "path": error["path"],
                "error": error["error"],
                "timestamp": error["timestamp"],
                "formatted_time": datetime.fromtimestamp(error["timestamp"]).strftime("%Y-%m-%d %H:%M:%S"),
                "response_time": round(error["response_time"] * 1000, 2)  # 毫秒
            })

        # 计算错误统计
        error_by_path = {}
        for error in filtered_errors:
            path = error["path"]
            if path not in error_by_path:
                error_by_path[path] = 0
            error_by_path[path] += 1

        total_requests = len(filtered_requests)
        error_rate = len(filtered_errors) / total_requests if total_requests > 0 else 0

        return {
            "errors": formatted_errors,
            "pagination": {
                "total": total_errors,
                "limit": limit,
                "offset": offset,
                "has_more": offset + limit < total_errors
            },
            "statistics": {
                "total_errors": total_errors,
                "total_requests": total_requests,
                "error_rate": error_rate,
                "errors_by_path": dict(sorted(error_by_path.items(), key=lambda x: x[1], reverse=True)[:10])
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取错误信息失败: {str(e)}")


@app.get("/api/admin/logs/stream")
async def stream_logs(
    authenticated: bool = Depends(verify_dashboard_api_key),
    level_filter: Optional[str] = None,
    path_filter: Optional[str] = None
):
    """实时日志流SSE端点"""

    async def event_generator():
        # 为这个连接创建专用队列
        subscriber_queue = asyncio.Queue(maxsize=100)
        log_subscribers.add(subscriber_queue)

        try:
            # 发送连接确认消息
            yield json.dumps({
                "type": "connection",
                "message": "Connected to log stream",
                "timestamp": time.time(),
                "formatted_time": datetime.fromtimestamp(time.time()).strftime("%Y-%m-%d %H:%M:%S")
            }, ensure_ascii=False)

            # 发送最近的历史日志（最近20条）
            try:
                recent_logs = []
                # 从log_queue获取最近的消息
                temp_queue = asyncio.Queue()

                # 获取队列中的现有消息
                while not log_queue.empty():
                    try:
                        log_entry = await asyncio.wait_for(log_queue.get_nowait(), timeout=0.1)
                        recent_logs.append(log_entry)
                        await temp_queue.put(log_entry)
                    except asyncio.TimeoutError:
                        break

                # 恢复队列
                while not temp_queue.empty():
                    await log_queue.put(await temp_queue.get_nowait())

                # 发送最近的历史日志
                for log_entry in recent_logs[-20:]:
                    if level_filter and log_entry.get("level") != level_filter.upper():
                        continue
                    if path_filter and path_filter.lower() not in log_entry.get("path", "").lower():
                        continue

                    yield json.dumps(log_entry, ensure_ascii=False)

            except Exception as e:
                print(f"[Log Stream] Error sending historical logs: {e}")

            # 持续监听新日志
            while True:
                try:
                    # 等待新日志消息
                    log_entry = await asyncio.wait_for(subscriber_queue.get(), timeout=30.0)

                    # 应用过滤器
                    if level_filter and log_entry.get("level") != level_filter.upper():
                        continue
                    if path_filter and path_filter.lower() not in log_entry.get("path", "").lower():
                        continue

                    # 发送日志消息
                    yield json.dumps(log_entry, ensure_ascii=False)

                except asyncio.TimeoutError:
                    # 发送心跳消息保持连接
                    yield json.dumps({
                        "type": "heartbeat",
                        "timestamp": time.time(),
                        "formatted_time": datetime.fromtimestamp(time.time()).strftime("%Y-%m-%d %H:%M:%S")
                    }, ensure_ascii=False)

                except Exception as e:
                    print(f"[Log Stream] Error in event generator: {e}")
                    break

        finally:
            # 清理订阅者
            log_subscribers.discard(subscriber_queue)
            print(f"[Log Stream] Subscriber disconnected, remaining: {len(log_subscribers)}")

    return EventSourceResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Cache-Control"
        }
    )


@app.post("/api/admin/logs/broadcast")
async def broadcast_log(
    log_data: dict,
    authenticated: bool = Depends(verify_dashboard_api_key)
):
    """广播自定义日志消息（用于测试或手动日志）"""
    try:
        level = log_data.get("level", "INFO").upper()
        message = log_data.get("message", "")
        path = log_data.get("path", "")
        request_id = log_data.get("request_id", "")

        if not message:
            raise HTTPException(status_code=400, detail="Message is required")

        await broadcast_log_message(level, message, path, request_id)

        return {
            "success": True,
            "message": "Log message broadcasted successfully",
            "timestamp": time.time()
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to broadcast log: {str(e)}")


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
    response_time = 0
    bytes_received = 0
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
            try:
                async for chunk in resp.aiter_bytes():
                    bytes_received += len(chunk)
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
                    await record_request_success(request_id, path, bytes_received, response_time)
                    await broadcast_log_message(
                        "INFO",
                        f"Request completed: {request.method} {path} - {resp.status_code} ({bytes_received} bytes, {response_time*1000:.1f}ms)",
                        path,
                        request_id
                    )
                else:
                    await record_request_error(
                        request_id, path,
                        f"HTTP {resp.status_code}: {resp.reason_phrase}",
                        response_time
                    )
                    await broadcast_log_message(
                        "ERROR",
                        f"Request failed: {request.method} {path} - {resp.status_code} {resp.reason_phrase}",
                        path,
                        request_id
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
            await record_request_error(request_id, path, str(e), time.time() - start_time)
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
    uvicorn.run("app:app", host="0.0.0.0", port=PORT, reload=DEBUG_MODE)