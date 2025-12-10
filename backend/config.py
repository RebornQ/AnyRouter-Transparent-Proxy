"""
配置管理模块

负责加载和管理所有应用配置，包括环境变量和自定义请求头
"""

from dotenv import load_dotenv
import json
import os

# 加载环境变量
load_dotenv()

# ===== 基础配置 =====
# 主站：https://anyrouter.top
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

# Hop-by-hop 头部列表（RFC 7230）
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


# 加载自定义请求头
CUSTOM_HEADERS = load_custom_headers()
