"""
Admin 路由模块

负责处理 Web 管理面板的所有路由，包括静态文件服务、API 端点和认证
"""

import asyncio
import json
import os
import time
import mimetypes
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Depends, Response, Request, Query
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from .. import config as config_module
from ..schemas.config import (
    ConfigUpdateRequest,
    ConfigResponse,
    ConfigEntry,
    CONFIG_METADATA
)
from ..services.config_service import config_service, ConfigServiceError
from ..services.stats import (
    request_stats,
    path_stats,
    stats_lock,
    format_bytes,
    calculate_percentiles,
    get_time_filtered_data
)
from ..services.auth_service import verify_dashboard_api_key
from ..services.restart_service import schedule_restart

def _normalize_status_code(entry: dict) -> dict:
    """确保 status_code 为数字，避免前端出现 "--" 与错误颜色不一致"""
    status_code = entry.get("status_code")
    # 保留原始值，便于调试定位
    entry["status_code_raw"] = status_code

    if isinstance(status_code, str):
        try:
            entry["status_code"] = int(status_code)
        except ValueError:
            # 转换失败时保留 None，让上层按未知处理，但 raw 里还能看到来源
            entry["status_code"] = None
    return entry

# 创建路由器
router = APIRouter()


# ===== 辅助函数 =====

def _bool_to_env(value: bool) -> str:
    """将布尔值转换为 .env 友好的字符串"""
    return "true" if value else "false"


def _collect_runtime_config() -> Dict[str, Any]:
    """收集最新的运行时配置值"""
    return {
        "target_base_url": config_module.TARGET_BASE_URL,
        "preserve_host": config_module.PRESERVE_HOST,
        "system_prompt_replacement": config_module.SYSTEM_PROMPT_REPLACEMENT,
        "system_prompt_block_insert_if_not_exist": config_module.SYSTEM_PROMPT_BLOCK_INSERT_IF_NOT_EXIST,
        "debug_mode": config_module.DEBUG_MODE,
        "port": config_module.PORT,
        "enable_dashboard": config_module.ENABLE_DASHBOARD,
        "dashboard_api_key": config_module.DASHBOARD_API_KEY,
        "custom_headers": config_module.CUSTOM_HEADERS,
        "dashboard_enabled": config_module.ENABLE_DASHBOARD
    }


def _build_config_response(redact_sensitive: bool = False) -> ConfigResponse:
    """构建兼容旧版扁平字段与新版 entries 的响应"""
    runtime_config = _collect_runtime_config()
    api_key = runtime_config.get("dashboard_api_key", "")
    api_key_configured = bool(api_key and api_key.strip())

    if redact_sensitive:
        runtime_config = dict(runtime_config)
        runtime_config["dashboard_api_key"] = ""
        runtime_config["custom_headers"] = {}

    entries: List[ConfigEntry] = []

    for meta in CONFIG_METADATA:
        entries.append(
            ConfigEntry(
                key=meta.key,
                value=runtime_config.get(meta.key, meta.value),
                metadata=meta.metadata
            )
        )

    return ConfigResponse(
        entries=entries,
        api_key_configured=api_key_configured,
        read_only=False,
        needs_restart=False,
        target_base_url=runtime_config.get("target_base_url"),
        preserve_host=runtime_config.get("preserve_host"),
        system_prompt_replacement=runtime_config.get("system_prompt_replacement"),
        system_prompt_block_insert_if_not_exist=runtime_config.get("system_prompt_block_insert_if_not_exist"),
        debug_mode=runtime_config.get("debug_mode"),
        port=runtime_config.get("port"),
        enable_dashboard=runtime_config.get("enable_dashboard"),
        dashboard_api_key=runtime_config.get("dashboard_api_key"),
        custom_headers=runtime_config.get("custom_headers")
    )


# ===== 静态文件路由 =====

@router.get("/admin")
@router.get("/admin/{path:path}")
async def admin_static(path: str = ""):
    """处理静态文件请求"""
    if not config_module.ENABLE_DASHBOARD:
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
        # 二进制读取，避免图片/图标被错误解码
        with open(file_path, 'rb') as f:
            content = f.read()

        # 猜测 MIME 类型，保证图标与二进制资源的正确 Content-Type
        mime_type, _ = mimetypes.guess_type(file_path)
        return Response(content=content, media_type=mime_type or "application/octet-stream")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading file: {e}")


# ===== Dashboard API 端点 =====

@router.get("/api/admin/health")
async def admin_health(authenticated: bool = Depends(verify_dashboard_api_key)):
    """Dashboard 健康检查端点"""
    return {
        "status": "ok",
        "dashboard_enabled": config_module.ENABLE_DASHBOARD,
        "timestamp": time.time()
    }


@router.get("/api/admin/config")
async def get_config():
    """获取当前配置信息（允许匿名查看，隐藏敏感信息）"""
    return _build_config_response(redact_sensitive=True)


@router.get("/api/admin/config/private")
async def get_config_private(authenticated: bool = Depends(verify_dashboard_api_key)):
    """获取完整配置信息（需要认证）"""
    return _build_config_response()


@router.head("/api/admin/config")
async def head_config(authenticated: bool = Depends(verify_dashboard_api_key)):
    """HEAD 探测，用于前端快速验证会话可用性"""
    return Response(status_code=204)


@router.get("/api/admin/config/metadata")
async def get_config_metadata():
    """获取配置元数据（前端可用以渲染表单，允许匿名查看）"""
    return {
        "metadata": [entry.dict() for entry in CONFIG_METADATA]
    }


@router.put("/api/admin/config")
async def update_config(config_data: ConfigUpdateRequest, authenticated: bool = Depends(verify_dashboard_api_key)):
    """更新配置信息（支持所有配置字段）"""
    try:
        updated_fields: List[str] = []
        env_updates: Dict[str, str] = {}

        # target_base_url
        if config_data.target_base_url is not None:
            config_module.TARGET_BASE_URL = str(config_data.target_base_url)
            env_updates["API_BASE_URL"] = str(config_data.target_base_url)
            updated_fields.append("target_base_url")

        # preserve_host
        if config_data.preserve_host is not None:
            config_module.PRESERVE_HOST = config_data.preserve_host
            env_updates["PRESERVE_HOST"] = _bool_to_env(config_data.preserve_host)
            updated_fields.append("preserve_host")

        # system_prompt_replacement
        if config_data.system_prompt_replacement is not None:
            config_module.SYSTEM_PROMPT_REPLACEMENT = config_data.system_prompt_replacement
            env_updates["SYSTEM_PROMPT_REPLACEMENT"] = config_data.system_prompt_replacement
            updated_fields.append("system_prompt_replacement")

        # system_prompt_block_insert_if_not_exist
        if config_data.system_prompt_block_insert_if_not_exist is not None:
            config_module.SYSTEM_PROMPT_BLOCK_INSERT_IF_NOT_EXIST = config_data.system_prompt_block_insert_if_not_exist
            env_updates["SYSTEM_PROMPT_BLOCK_INSERT_IF_NOT_EXIST"] = _bool_to_env(
                config_data.system_prompt_block_insert_if_not_exist
            )
            updated_fields.append("system_prompt_block_insert_if_not_exist")

        # debug_mode
        if config_data.debug_mode is not None:
            config_module.DEBUG_MODE = config_data.debug_mode
            env_updates["DEBUG_MODE"] = _bool_to_env(config_data.debug_mode)
            updated_fields.append("debug_mode")

        # port
        if config_data.port is not None:
            config_module.PORT = config_data.port
            env_updates["PORT"] = str(config_data.port)
            updated_fields.append("port")

        # enable_dashboard / dashboard_enabled
        if config_data.enable_dashboard is not None:
            config_module.ENABLE_DASHBOARD = config_data.enable_dashboard
            env_updates["ENABLE_DASHBOARD"] = _bool_to_env(config_data.enable_dashboard)
            updated_fields.append("dashboard_enabled")

        # dashboard_api_key
        if config_data.dashboard_api_key is not None:
            config_module.DASHBOARD_API_KEY = config_data.dashboard_api_key
            env_updates["DASHBOARD_API_KEY"] = config_data.dashboard_api_key
            updated_fields.append("dashboard_api_key")

        # custom_headers
        if config_data.custom_headers is not None:
            if not isinstance(config_data.custom_headers, dict):
                raise HTTPException(status_code=400, detail="custom_headers 必须是字典类型")

            config_module.CUSTOM_HEADERS.clear()
            config_module.CUSTOM_HEADERS.update(config_data.custom_headers)
            updated_fields.append("custom_headers")

            headers_file = "env/.env.headers.json"
            try:
                os.makedirs("env", exist_ok=True)
                with open(headers_file, 'w', encoding='utf-8') as f:
                    json.dump(config_data.custom_headers, f, ensure_ascii=False, indent=2)
                print(f"[Config] Saved custom headers to {headers_file}")
            except Exception as e:
                print(f"[Config] Failed to save custom headers: {e}")
                raise HTTPException(status_code=500, detail=f"保存配置失败: {e}")

        # 持久化 .env
        if env_updates:
            try:
                await config_service.update_env(env_updates)
            except ConfigServiceError as e:
                raise HTTPException(status_code=500, detail=f"保存 .env 失败: {str(e)}")

        # 判断是否需要重启（env 配置变更需要重启生效）
        needs_restart = bool(env_updates)
        response = _build_config_response()

        if needs_restart:
            schedule_restart(delay=1.0)
            return {
                "success": True,
                "updated_fields": updated_fields,
                "message": "配置更新成功，服务将在 1 秒后自动重启。",
                "restart_scheduled": True,
                "restart_after_ms": 1000,
                "entries": response.entries
            }

        return {
            "success": True,
            "updated_fields": updated_fields,
            "message": "配置更新成功。",
            "restart_scheduled": False,
            "entries": response.entries
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新配置失败: {str(e)}")


@router.get("/api/admin/stats")
async def get_stats(
    start_time: Optional[float] = None,
    end_time: Optional[float] = None,
    limit: Optional[int] = 100
):
    """获取系统统计信息"""
    try:
        filtered_requests, filtered_errors, filtered_time_series = await get_time_filtered_data(start_time, end_time)
        normalized_requests = [_normalize_status_code(dict(req)) for req in filtered_requests]

        # 计算基本统计
        total_filtered_requests = len(normalized_requests)
        successful_filtered_requests = len([
            r for r in normalized_requests
            if (
                (r.get("status_code") is not None and r.get("status_code", 0) < 400) or
                (r.get("status_code") is None and r.get("status") not in ("error", "pending"))
            )
        ])
        error_filtered_requests = len([
            r for r in normalized_requests
            if (
                (r.get("status_code") is not None and r.get("status_code", 0) >= 400) or
                r.get("status") == "error"
            )
        ])

        # 计算响应时间统计
        response_times = [r["response_time"] * 1000 for r in normalized_requests if r["response_time"] > 0]  # 转换为毫秒
        response_time_stats = calculate_percentiles(response_times, [50, 95, 99])

        # 计算QPS（每秒请求数）
        time_range = (end_time or time.time()) - (start_time or (time.time() - 3600))
        qps = total_filtered_requests / time_range if time_range > 0 else 0

        # 计算总字节数
        total_bytes_sent = sum(r.get("bytes", 0) for r in normalized_requests)

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
            "recent_requests": normalized_requests[-limit:] if limit > 0 else normalized_requests
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取统计数据失败: {str(e)}")


@router.get("/api/admin/errors")
async def get_errors(
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
                "response_time": round(error["response_time"] * 1000, 2),  # 毫秒
                "response_content": error.get("response_content")  # 添加响应内容
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
