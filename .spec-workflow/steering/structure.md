# Project Structure

## Directory Organization

```
AnyRouter-Transparent-Proxy/
├── app.py                          # 核心代理逻辑 (403行)
├── requirements.txt                # Python 依赖清单
├── .env.example                    # 环境变量配置模板
├── .env                            # 本地环境变量 (不提交到版本控制)
├── Dockerfile                      # Docker 镜像构建配置
├── docker-compose.yml              # Docker Compose 编排配置
├── README.md                       # 中文项目文档
├── README_en.md                    # 英文项目文档
├── CLAUDE.md                       # AI 上下文索引
├── .claudeignore                   # Claude Code 忽略文件配置
├── .spec-workflow/                 # 规范工作流目录
│   ├── templates/                  # 规范模板目录
│   │   ├── product-template.md     # 产品规范模板
│   │   ├── tech-template.md        # 技术规范模板
│   │   └── structure-template.md   # 结构规范模板
│   └── steering/                   # 指导文档目录
│       ├── product.md              # 产品指导文档
│       ├── tech.md                 # 技术指导文档
│       └── structure.md            # 项目结构文档 (本文件)
└── env/                            # 环境配置目录
    ├── .env.headers.json           # 自定义请求头配置
    └── .env.headers.example        # 自定义请求头模板
```

### 结构设计原则
- **单文件核心架构**: 所有业务逻辑集中在 `app.py`，降低部署复杂度
- **配置外部化**: 环境变量和 JSON 配置文件，支持不同部署环境
- **文档驱动**: 完整的中英文文档和 AI 上下文索引
- **容器优先**: Docker 和 Docker Compose 作为主要部署方式
- **规范化**: 使用 `.spec-workflow` 进行项目规范管理

## Naming Conventions

### Files
- **Python 文件**: `snake_case` (例: `app.py`)
- **配置文件**: 点开头+描述性名称 (例: `.env.example`)
- **文档文件**: `kebab-case` (例: `README.md`, `README_en.md`)
- **Docker 文件**: 标准命名 (例: `Dockerfile`, `docker-compose.yml`)
- **环境文件**: `UPPER_SNAKE_CASE` (例: `.env.headers.json`)

### Code
- **类**: `PascalCase` (例: `AsyncHttpClient`)
- **函数/方法**: `snake_case` (例: `filter_request_headers`)
- **常量**: `UPPER_SNAKE_CASE` (例: `API_BASE_URL`, `SYSTEM_PROMPT_REPLACEMENT`)
- **变量**: `snake_case` (例: `http_client`, `forward_headers`)
- **环境变量**: `UPPER_SNAKE_CASE` (例: `DEBUG_MODE`, `PORT`)

## Import Patterns

### Import Order (Python 标准顺序)
1. 标准库导入 (`os`, `json`, `asyncio`, 等)
2. 第三方库导入 (`fastapi`, `httpx`, `uvicorn`, 等)
3. 本地模块导入 (本项目内部，当前单文件架构下较少)
4. 类型提示导入 (`from typing import ...`)

### 导入示例
```python
# 标准库
import os
import json
import asyncio
from typing import Dict, List, Optional

# 第三方库
from fastapi import FastAPI, Request, Response
from fastapi.responses import StreamingResponse
from httpx import AsyncClient
import uvicorn

# 项目常量
API_BASE_URL = os.getenv("API_BASE_URL", "https://anyrouter.top")
```

## Code Structure Patterns

### app.py 文件组织结构
```python
# 1. 导入和依赖
#    - 标准库导入
#    - 第三方库导入
#    - 类型提示导入
#    - 环境变量和常量定义

# 2. 全局变量和配置
#    - 环境变量加载
#    - 全局 AsyncClient 实例
#    - 配置验证

# 3. 核心函数定义
#    - lifespan() - 应用生命周期管理
#    - load_custom_headers() - 配置加载
#    - filter_request_headers() - 请求处理
#    - filter_response_headers() - 响应处理
#    - process_request_body() - 业务逻辑

# 4. API 端点定义
#    - health_check() - 健康检查
#    - proxy() - 主代理函数

# 5. FastAPI 应用初始化
#    - app = FastAPI(lifespan=lifespan)
#    - 路由注册

# 6. 主程序入口
#    - if __name__ == "__main__": 启动逻辑
```

### 函数组织模式
```python
def function_name(param1: Type1, param2: Type2) -> ReturnType:
    """
    函数文档字符串 (中文)

    Args:
        param1: 参数描述
        param2: 参数描述

    Returns:
        返回值描述

    Raises:
        Exception: 异常情况描述
    """
    # 1. 输入验证
    if not param1:
        raise ValueError("参数错误")

    try:
        # 2. 核心逻辑
        result = process_logic(param1, param2)

        # 3. 结果处理
        return format_result(result)

    except Exception as e:
        # 4. 错误处理
        logger.error(f"操作失败: {e}")
        raise
```

## Code Organization Principles

### 1. **简洁至上 (Simplicity First)**
- 单文件架构，避免过度工程化
- 每个函数职责单一明确
- 代码行数控制：单个函数不超过 50 行

### 2. **可读性优先 (Readability Priority)**
- 中文注释，便于团队理解
- 一致的命名规范
- 逻辑分层清晰

### 3. **异步优先 (Async-First)**
- 所有 I/O 操作使用 async/await
- 流式响应处理
- 非阻塞错误处理

### 4. **配置驱动 (Configuration-Driven)**
- 环境变量控制行为
- JSON 配置文件支持复杂配置
- 默认值合理

## Module Boundaries

### 核心模块边界
```
┌─────────────────────────────────────────────────────────────┐
│                        app.py                              │
│  ┌─────────────────┬─────────────────┬──────────────────┐  │
│  │   配置管理      │    核心业务      │    API 端点      │  │
│  │   Configuration │   Business      │   Endpoints      │  │
│  │                 │   Logic         │                  │  │
│  │ • 环境变量       │ • 请求头过滤     │ • 健康检查       │  │
│  │ • JSON 配置     │ • System Prompt │ • 代理端点       │  │
│  │ • 常量定义      │ • 响应处理       │ • 错误处理       │  │
│  └─────────────────┴─────────────────┴──────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### 接口边界
- **公共 API**: FastAPI 路由端点 (`/health`, `{proxy_path}`)
- **内部函数**: 以下划线开头或无导出的辅助函数
- **配置接口**: 环境变量和 JSON 文件

### 依赖方向
- **核心逻辑** → **配置系统** (读取配置)
- **API 端点** → **核心逻辑** (调用业务函数)
- **所有模块** → **HTTP 客户端** (网络通信)

## Code Size Guidelines

### 文件大小限制
- **主文件 (app.py)**: 建议 < 500 行 (当前 403 行)
- **配置文件**: < 100 行
- **文档文件**: 不限制，但建议结构清晰

### 函数大小限制
- **简单函数**: < 20 行 (如 `filter_request_headers`)
- **复杂函数**: < 50 行 (如 `proxy`, `process_request_body`)
- **工具函数**: < 15 行 (如 `load_custom_headers`)

### 复杂度限制
- **嵌套深度**: 最大 4 层
- **圈复杂度**: 单个函数 < 10
- **参数个数**: 最多 5 个位置参数，超出使用关键字参数

### 示例：函数大小控制
```python
# ✅ 好的例子 - 简洁明确
def filter_request_headers(headers: Dict[str, str]) -> Dict[str, str]:
    """过滤 HTTP 请求头，移除 hop-by-hop 头部"""
    hop_by_hop_headers = {
        "connection", "keep-alive", "proxy-authenticate",
        "proxy-authorization", "te", "trailers", "transfer-encoding", "upgrade"
    }

    return {
        k: v for k, v in headers.items()
        if k.lower() not in hop_by_hop_headers
    }
```

## Configuration Structure

### 环境变量结构
```bash
# 核心配置
API_BASE_URL=https://anyrouter.top
PORT=8088
DEBUG_MODE=false

# 功能开关
SYSTEM_PROMPT_REPLACEMENT=
SYSTEM_PROMPT_BLOCK_INSERT_IF_NOT_EXIST=false

# 网络配置
HTTP_PROXY=
HTTPS_PROXY=
```

### JSON 配置结构
```json
// env/.env.headers.json
{
  "User-Agent": "claude-cli/2.0.8 (external, cli)",
  "__comment": "以 __ 开头的字段会被忽略",
  "__description": "自定义请求头配置文件"
}
```

## Documentation Standards

### 代码注释规范
- **文件头部注释**: 描述文件用途和主要功能
- **函数文档字符串**: 使用 Google 风格，中文描述
- **复杂逻辑注释**: 解释算法和业务逻辑
- **TODO/FIXME**: 标记待完成和待修复项

### 文档文件标准
- **README.md**: 完整的项目说明，包含安装、配置、使用指南
- **CLAUDE.md**: AI 上下文索引，包含架构图和技术细节
- **代码注释**: 与代码语言保持一致 (中文)

### API 文档
- **FastAPI 自动生成**: `/docs` 端点提供 Swagger UI
- **中文注释**: 确保自动文档的中文显示
- **类型提示**: 完整的类型注解支持文档生成

## Testing Structure (未来扩展)

### 测试文件组织 (规划)
```
tests/
├── test_app.py              # 主应用测试
├── test_filters.py          # 请求/响应过滤测试
├── test_config.py           # 配置加载测试
├── conftest.py              # pytest 配置
└── fixtures/                # 测试数据
    └── sample_requests.json
```

### 测试命名规范
- **测试文件**: `test_*.py`
- **测试类**: `TestClassName`
- **测试方法**: `test_function_name_scenario`

## Deployment Structure

### Docker 层次结构
```
Dockerfile 构建层次:
1. 基础层: python:3.12-slim
2. 依赖层: requirements.txt
3. 应用层: app.py + 配置
4. 运行时层: 健康检查 + 启动命令
```

### 运行时环境
- **开发环境**: 直接 Python 运行
- **测试环境**: Docker Compose
- **生产环境**: Docker + 外部负载均衡