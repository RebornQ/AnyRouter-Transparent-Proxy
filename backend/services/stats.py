"""
统计服务模块

负责收集和管理代理服务的统计数据，包括请求统计、性能指标、错误日志和实时日志流
"""

import asyncio
import time
from collections import defaultdict, deque
from datetime import datetime
from typing import Optional, Tuple

from ..config import LOG_PERSISTENCE_ENABLED, LOG_STORAGE_PATH, LOG_RETENTION_DAYS, LOG_DAILY_LIMIT
from .log_storage import LogStorage

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

# 持久化存储
log_storage: Optional[LogStorage] = None
if LOG_PERSISTENCE_ENABLED:
    try:
        log_storage = LogStorage(
            storage_path=LOG_STORAGE_PATH,
            daily_limit=LOG_DAILY_LIMIT,
            retention_days=LOG_RETENTION_DAYS
        )
        print(f"[Log Storage] Persistence enabled, path: {LOG_STORAGE_PATH}, retention: {LOG_RETENTION_DAYS} days")
    except Exception as e:
        print(f"[Log Storage] Failed to init: {e}")
        log_storage = None


async def record_request_start(path: str, method: str, bytes_sent: int) -> str:
    """记录请求开始，返回请求ID"""
    request_id = f"{int(time.time() * 1000)}-{id(asyncio.current_task())}"

    async with stats_lock:
        request_stats["total_requests"] += 1
        request_stats["total_bytes_sent"] += bytes_sent
        path_stats[path]["count"] += 1
        path_stats[path]["bytes"] += bytes_sent

    return request_id


async def record_request_success(
    request_id: str,
    path: str,
    method: str,
    bytes_received: int,
    response_time: float,
    status_code: int
):
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
            "method": method,
            "status_code": status_code,
            "bytes": bytes_received,
            "response_time": response_time,
            "timestamp": time.time()
        })


async def record_request_error(
    request_id: str,
    path: str,
    method: str,
    error_msg: str,
    response_time: float = 0,
    response_content: str = None,
    status_code: int | None = None
):
    """记录请求错误"""
    async with stats_lock:
        request_stats["failed_requests"] += 1
        path_stats[path]["errors"] += 1

        # 记录错误日志
        error_logs.append({
            "request_id": request_id,
            "path": path,
            "error": error_msg,
            "status_code": status_code,
            "response_content": response_content,
            "timestamp": time.time(),
            "response_time": response_time
        })

        # 记录最近请求
        recent_requests.append({
            "request_id": request_id,
            "path": path,
            "method": method,
            "status_code": status_code,
            "error": error_msg,
            "response_content": response_content,
            "response_time": response_time,
            "timestamp": time.time()
        })


async def update_time_window_stats():
    """更新时间窗口统计（每分钟调用一次）"""
    current_time = time.time()
    # 将当前时间戳向下取整到分钟级别（秒级时间戳）
    current_minute_timestamp = int(current_time // 60) * 60

    async with stats_lock:
        # 计算本分钟的请求数
        minute_requests = sum(1 for req in recent_requests
                            if req["timestamp"] > current_time - 60)
        minute_errors = sum(1 for req in recent_requests
                          if (
                              (req.get("status_code") is not None and req.get("status_code", 0) >= 400) or
                              req.get("status") == "error"
                          ) and req["timestamp"] > current_time - 60)
        minute_bytes = sum(req.get("bytes", 0) for req in recent_requests
                         if req["timestamp"] > current_time - 60)

        time_window_stats["requests_per_minute"].append({
            "time": current_minute_timestamp,  # 使用 Unix 时间戳（秒级）
            "count": minute_requests
        })
        time_window_stats["errors_per_minute"].append({
            "time": current_minute_timestamp,  # 使用 Unix 时间戳（秒级）
            "count": minute_errors
        })
        time_window_stats["bytes_per_minute"].append({
            "time": current_minute_timestamp,  # 使用 Unix 时间戳（秒级）
            "count": minute_bytes
        })


async def persist_log_entry(log_entry: dict) -> None:
    """写入持久化存储（可配置关闭）"""
    if not log_storage:
        return
    try:
        await log_storage.write_log(log_entry)
    except Exception as e:
        print(f"[Log Storage] Failed to write log: {e}")


async def get_recent_persisted_logs(limit: int = 20):
    if not log_storage:
        return []
    try:
        return await log_storage.get_recent_logs(limit=limit)
    except Exception as e:
        print(f"[Log Storage] Failed to load recent logs: {e}")
        return []


async def query_persisted_logs(
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    level: Optional[str] = None,
    path_filter: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
):
    if not log_storage:
        return [], 0
    try:
        filters = {}
        if level:
            filters["level"] = level
        if path_filter:
            filters["path_filter"] = path_filter
        return await log_storage.query_logs(
            start_time=start_time,
            end_time=end_time,
            filters=filters,
            limit=limit,
            offset=offset
        )
    except Exception as e:
        print(f"[Log Storage] Failed to query logs: {e}")
        return [], 0


async def clear_all_logs():
    """清空持久化与内存队列"""
    if log_storage:
        try:
            await log_storage.clear_all()
        except Exception as e:
            print(f"[Log Storage] Failed to clear files: {e}")

    # 清空内存日志队列
    try:
        while not log_queue.empty():
            log_queue.get_nowait()
            log_queue.task_done()
    except Exception:
        pass


async def broadcast_log_message(level: str, message: str, path: str = "", request_id: str = "", response_content: str = None):
    """广播日志消息到所有订阅者"""
    current_time = time.time()
    log_entry = {
        "timestamp": current_time,
        "level": level,
        "message": message,
        "path": path,
        "request_id": request_id,
        "formatted_time": datetime.fromtimestamp(current_time).strftime("%Y-%m-%d %H:%M:%S"),
        "response_content": response_content
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

    await persist_log_entry(log_entry)


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


async def periodic_stats_update():
    """定期更新统计数据"""
    while True:
        try:
            await update_time_window_stats()
        except Exception as e:
            print(f"[Stats] Failed to update time window stats: {e}")

        # 每分钟更新一次
        await asyncio.sleep(60)


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


async def get_time_filtered_data(start_time: float = None, end_time: float = None) -> Tuple:
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

        # 过滤时间窗口统计（time 字段现在是 Unix 时间戳）
        filtered_time_series = {
            "requests_per_minute": [
                data for data in time_window_stats["requests_per_minute"]
                if start_time <= data["time"] <= end_time
            ],
            "errors_per_minute": [
                data for data in time_window_stats["errors_per_minute"]
                if start_time <= data["time"] <= end_time
            ],
            "bytes_per_minute": [
                data for data in time_window_stats["bytes_per_minute"]
                if start_time <= data["time"] <= end_time
            ]
        }

    return filtered_requests, filtered_errors, filtered_time_series
