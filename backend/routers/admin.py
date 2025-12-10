"""
Admin 路由模块

负责处理 Web 管理面板的所有路由，包括静态文件服务、API 端点和认证
"""

import asyncio
import json
import os
import time
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, Response, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from ..config import (
    ENABLE_DASHBOARD,
    DASHBOARD_API_KEY,
    TARGET_BASE_URL,
    PRESERVE_HOST,
    SYSTEM_PROMPT_REPLACEMENT,
    SYSTEM_PROMPT_BLOCK_INSERT_IF_NOT_EXIST,
    DEBUG_MODE,
    PORT,
    CUSTOM_HEADERS
)
from ..services.stats import (
    request_stats,
    path_stats,
    stats_lock,
    log_subscribers,
    log_queue,
    format_bytes,
    calculate_percentiles,
    get_time_filtered_data,
    broadcast_log_message
)

# 创建路由器
router = APIRouter()

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


# ===== 静态文件路由 =====

@router.get("/admin")
@router.get("/admin/{path:path}")
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
        # SPA fallback 机制：如果请求的路径不包含文件扩展名（即前端路由），返回 index.html
        # 这样前端路由可以接管并正确处理路由
        if '.' not in os.path.basename(path):
            # 这是一个前端路由路径（如 /admin/dashboard），返回 index.html
            file_path = os.path.join("static", "index.html")
            if not os.path.exists(file_path):
                raise HTTPException(status_code=500, detail="index.html not found")
        else:
            # 这是一个静态资源请求（如 /admin/assets/xxx.js），但文件不存在
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


# ===== Dashboard API 端点 =====

@router.get("/api/admin/health")
async def admin_health(authenticated: bool = Depends(verify_dashboard_api_key)):
    """Dashboard 健康检查端点"""
    return {
        "status": "ok",
        "dashboard_enabled": ENABLE_DASHBOARD,
        "timestamp": time.time()
    }


@router.get("/api/admin/config")
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


@router.put("/api/admin/config")
async def update_config(config_data: ConfigUpdateRequest, authenticated: bool = Depends(verify_dashboard_api_key)):
    """更新配置信息（仅支持运行时动态配置）"""
    try:
        updated_fields = []

        # 更新自定义请求头
        if config_data.custom_headers is not None:
            if isinstance(config_data.custom_headers, dict):
                # 导入全局配置
                from .. import config as config_module
                config_module.CUSTOM_HEADERS = config_data.custom_headers
                updated_fields.append("custom_headers")

                # 保存到文件
                headers_file = "env/.env.headers.json"
                try:
                    os.makedirs("env", exist_ok=True)
                    with open(headers_file, 'w', encoding='utf-8') as f:
                        json.dump(config_data.custom_headers, f, ensure_ascii=False, indent=2)
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


@router.get("/api/admin/stats")
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


@router.get("/api/admin/errors")
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


@router.get("/api/admin/logs/stream")
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


@router.post("/api/admin/logs/broadcast")
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
