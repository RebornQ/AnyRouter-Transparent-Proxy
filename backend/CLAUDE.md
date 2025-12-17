# Backend 模块文档

> 📍 **导航**: [根目录](../CLAUDE.md) > **backend**

---

## 📋 模块概述

**Backend** 是基于 FastAPI 的异步 HTTP 代理服务，负责请求转发、System Prompt 处理、统计收集和管理面板 API。

**技术栈**: FastAPI + httpx + Uvicorn + sse-starlette

---

## 📁 目录结构

```
backend/
├── app.py                    # 主应用入口
├── config.py                 # 配置管理
├── requirements.txt          # 依赖清单
├── services/                 # 业务逻辑
│   ├── proxy.py             # 代理处理
│   ├── stats.py             # 统计收集
│   └── log_storage.py       # 日志持久化
├── routers/                  # 路由层
│   └── admin.py             # 管理面板 API
└── utils/                    # 工具函数
    └── encoding.py          # 编码处理
```

---

## 🧩 核心模块

### 1. 主应用 ([app.py](app.py))

**职责**: FastAPI 应用定义、生命周期管理、主代理路由

**关键函数**:
| 函数 | 行号 | 功能 |
|------|------|------|
| `lifespan()` | 54-128 | 生命周期管理，初始化 HTTP 客户端和后台任务 |
| `health_check()` | ~145 | 健康检查端点 |
| `proxy()` | ~190+ | **核心**: 捕获所有路由并转发请求，支持流式响应 |

**代理流程**:
1. 读取请求体
2. 过滤请求头（移除 hop-by-hop 头部）
3. 对 `/v1/messages` 执行 System Prompt 处理
4. 构建并发送上游请求（`httpx.build_request()` + `send(stream=True)`）
5. 返回流式响应（`BackgroundTask` 管理连接关闭）

---

### 2. 配置管理 ([config.py](config.py))

**职责**: 加载环境变量、管理全局配置、自定义请求头加载

**主要配置**:
| 配置 | 类型 | 说明 |
|------|------|------|
| `TARGET_BASE_URL` | str | 上游 API 地址 |
| `SYSTEM_PROMPT_REPLACEMENT` | str\|None | System Prompt 替换文本 |
| `SYSTEM_PROMPT_BLOCK_INSERT_IF_NOT_EXIST` | bool | 启用插入模式 |
| `HOP_BY_HOP_HEADERS` | set[str] | RFC 7230 hop-by-hop 头部列表 |
| `CUSTOM_HEADERS` | dict | 自定义请求头（从 `env/.env.headers.json` 加载） |

---

### 3. 代理处理 ([services/proxy.py](services/proxy.py))

**职责**: 请求/响应过滤、System Prompt 处理

**关键函数**:
| 函数 | 功能 |
|------|------|
| `filter_request_headers()` | 过滤请求头，移除 hop-by-hop 头部 |
| `filter_response_headers()` | 过滤响应头 |
| `process_request_body()` | 处理请求体，替换/插入 System Prompt |
| `prepare_forward_headers()` | 准备转发请求头，注入自定义头部 |

**System Prompt 处理逻辑** (仅 `/v1/messages` 路由):
```python
# 插入模式
if SYSTEM_PROMPT_BLOCK_INSERT_IF_NOT_EXIST:
    if "Claude Code" not in original_text:
        data["system"].insert(0, new_element)
    else:
        data["system"][0]["text"] = SYSTEM_PROMPT_REPLACEMENT
# 替换模式（默认）
else:
    data["system"][0]["text"] = SYSTEM_PROMPT_REPLACEMENT
```

---

### 4. 统计收集 ([services/stats.py](services/stats.py))

**职责**: 收集请求统计、性能指标、错误日志，提供实时日志流

**全局数据**:
| 变量 | 类型 | 用途 |
|------|------|------|
| `request_stats` | dict | 全局统计（请求数、成功数、失败数、流量） |
| `recent_requests` | deque | 最近 1000 个请求的性能数据 |
| `error_logs` | deque | 最近 500 个错误日志 |
| `log_queue` | asyncio.Queue | 日志消息队列（SSE 推送） |

**关键函数**:
- `record_request_start()`: 记录请求开始
- `record_request_success()`: 记录请求成功
- `record_request_error()`: 记录请求错误
- `broadcast_log_message()`: 广播日志到所有 SSE 订阅者
- `periodic_stats_update()`: 后台任务，定期更新统计
- `log_producer()`: 后台任务，消费日志队列并广播

---

### 5. 日志持久化 ([services/log_storage.py](services/log_storage.py))

**职责**: 日志按日期持久化存储、查询、清理

**类结构**:
```python
class LogStorage:
    def store_log(self, log_entry: dict) -> bool
    def query_logs(self, start_date, end_date, filters) -> list
    def get_recent_logs(self, limit) -> list
    def clear_all_logs() -> bool
```

**文件格式**: `{storage_path}/YYYY-MM-DD.jsonl` (JSON Lines)

---

### 6. 管理面板路由 ([routers/admin.py](routers/admin.py))

**职责**: Web 管理面板 RESTful API

**API 端点**:
| 端点 | 方法 | 功能 |
|------|------|------|
| `/api/stats` | GET | 获取系统统计 |
| `/api/errors` | GET | 获取错误日志 |
| `/api/config` | GET/POST | 获取/更新配置 |
| `/api/logs/stream` | GET | 实时日志流 (SSE) |
| `/api/logs/history` | GET | 查询历史日志 |
| `/api/logs/clear` | DELETE | 清空日志 |

---

## 🔧 依赖管理

```txt
fastapi==0.115.5
uvicorn==0.32.1
httpx==0.28.1
python-dotenv==1.0.1
sse-starlette==2.2.1
```

---

## 🚀 启动方式

### 开发模式
```bash
python backend/app.py
```

### 生产模式
```bash
uvicorn backend.app:app --host 0.0.0.0 --port 8088 --workers 1
```

**注意**: 使用全局状态管理统计，建议单 worker 模式。

---

**返回**: [根目录文档](../CLAUDE.md)
