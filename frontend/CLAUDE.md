# Frontend 模块文档

> 📍 **导航**: [根目录](../CLAUDE.md) > **frontend**

---

## 📋 模块概述

**Frontend** 是基于 Vue 3 + TypeScript 的 Web 管理面板，提供实时监控、日志查看和配置管理界面。

**技术栈**: Vue 3 + TypeScript + Vite + Pinia + TailwindCSS 4 + Chart.js

**核心特性**:
- 实时监控仪表板（请求统计、性能指标、图表）
- 实时日志流（SSE，支持过滤和搜索）
- 历史日志查询（按日期、路径、方法、状态码过滤）
- 配置管理（环境变量、自定义请求头）
- PWA 支持（离线访问、桌面安装）

---

## 📁 目录结构

```
frontend/
├── public/
│   └── icons/
│       └── pwa.svg              # PWA 图标
├── src/
│   ├── main.ts                  # 应用入口
│   ├── App.vue                  # 根组件
│   ├── router/
│   │   └── index.ts             # 路由配置
│   ├── stores/
│   │   └── index.ts             # Pinia 状态管理
│   ├── services/
│   │   └── api.ts               # API 服务层
│   ├── views/                   # 页面组件
│   │   ├── Dashboard.vue        # 仪表板
│   │   ├── Monitoring.vue       # 监控中心
│   │   ├── Logs.vue             # 日志查看
│   │   └── Config.vue           # 配置管理
│   ├── components/              # 公共组件
│   ├── composables/             # 组合式函数
│   └── types/
│       └── index.ts             # TypeScript 类型
├── package.json                 # 依赖配置
├── vite.config.ts               # Vite 构建配置
└── tsconfig.json                # TypeScript 配置
```

---

## 🧩 核心模块

### 1. 应用入口 ([src/main.ts](src/main.ts))

**职责**: 初始化 Vue 应用、注册插件、挂载应用

```typescript
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import router from './router'
import App from './App.vue'

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.mount('#app')
```

---

### 2. 路由配置 ([src/router/index.ts](src/router/index.ts))

**路由列表**:
| 路径 | 组件 | 功能 |
|------|------|------|
| `/` | - | 重定向到 `/dashboard` |
| `/dashboard` | Dashboard.vue | 仪表板页面 |
| `/monitoring` | Monitoring.vue | 监控中心 |
| `/logs` | Logs.vue | 日志查看 |
| `/config` | Config.vue | 配置管理 |

---

### 3. API 服务层 ([src/services/api.ts](src/services/api.ts))

**职责**: 封装后端 API 调用，统一错误处理

**API 方法**:
| 方法 | 端点 | 功能 |
|------|------|------|
| `fetchSystemStats()` | GET `/api/stats` | 获取系统统计 |
| `fetchErrorLogs()` | GET `/api/errors` | 获取错误日志 |
| `fetchSystemConfig()` | GET `/api/config` | 获取配置 |
| `updateSystemConfig()` | POST `/api/config` | 更新配置 |
| `subscribeToLogs()` | SSE `/api/logs/stream` | 订阅实时日志 |
| `fetchLogHistory()` | GET `/api/logs/history` | 查询历史日志 |
| `clearAllLogs()` | DELETE `/api/logs/clear` | 清空日志 |

---

### 4. 状态管理 ([src/stores/index.ts](src/stores/index.ts))

**职责**: 全局状态管理（使用 Pinia）

**Store 结构**:
```typescript
export const useMainStore = defineStore('main', {
  state: () => ({
    systemStats: null as SystemStats | null,
    errorLogs: [] as ErrorLog[],
    systemConfig: null as SystemConfig | null,
    logs: [] as LogEntry[],
    isLoading: false,
    notifications: [] as Notification[]
  }),
  actions: {
    async loadSystemStats(),
    async loadErrorLogs(),
    async loadSystemConfig(),
    async updateConfig(data),
    addNotification(notification),
    removeNotification(id)
  }
})
```

---

### 5. 页面组件

#### Dashboard ([src/views/Dashboard.vue](src/views/Dashboard.vue))
- 显示系统概览、统计卡片、快速操作
- 使用 Chart.js 绘制趋势图

#### Monitoring ([src/views/Monitoring.vue](src/views/Monitoring.vue))
- 实时监控、性能指标、路径统计
- 使用 `useRealtime()` 订阅实时数据

#### Logs ([src/views/Logs.vue](src/views/Logs.vue))
- 实时日志流（SSE）
- 历史日志查询（日期范围、路径、方法、状态码过滤）
- 日志操作（清空、导出 CSV）

#### Config ([src/views/Config.vue](src/views/Config.vue))
- 环境变量显示（只读）
- 自定义请求头编辑（可编辑）

---

### 6. TypeScript 类型 ([src/types/index.ts](src/types/index.ts))

**核心类型**:
```typescript
// 系统统计
export interface SystemStats {
  total_requests: number
  successful_requests: number
  failed_requests: number
  total_bytes_sent: number
  total_bytes_received: number
  uptime: number
  avg_response_time: number
}

// 日志条目
export interface LogEntry {
  id: string
  timestamp: string
  method: string
  path: string
  status_code: number
  response_time: number
  bytes_sent: number
  bytes_received: number
  error?: string
}

// 系统配置
export interface SystemConfig {
  api_base_url: string
  system_prompt_replacement: string | null
  system_prompt_block_insert_if_not_exist: boolean
  debug_mode: boolean
  port: number
  custom_headers: Record<string, string>
  log_persistence_enabled: boolean
  log_storage_path: string
  log_retention_days: number
}
```

---

## 🔧 依赖管理

```json
{
  "dependencies": {
    "vue": "^3.5.25",
    "vue-router": "^4.6.3",
    "pinia": "^3.0.4",
    "ky": "^1.14.1",
    "chart.js": "^4.5.1",
    "vue-chartjs": "^5.3.3",
    "workbox-window": "^7.4.0"
  },
  "devDependencies": {
    "@vitejs/plugin-vue": "^6.0.2",
    "vite": "^7.2.4",
    "typescript": "~5.9.3",
    "tailwindcss": "^4.0.0",
    "vite-plugin-pwa": "^0.21.1"
  }
}
```

---

## 🚀 构建和部署

### 开发模式
```bash
cd frontend
npm install
npm run dev
```

访问: `http://localhost:5173`

### 生产构建
```bash
npm run build
```

**构建输出**: `../static/`（由后端静态服务）

---

## 🎨 样式系统

### TailwindCSS 配置
```typescript
// tailwind.config.ts
export default {
  theme: {
    extend: {
      colors: {
        primary: '#0ea5e9',   // 天蓝色
        success: '#10b981',   // 绿色
        warning: '#f59e0b',   // 橙色
        error: '#ef4444',     // 红色
      }
    }
  }
}
```

---

## 📱 PWA 配置

**Service Worker 策略**:
- **静态资源**: CacheFirst（优先缓存）
- **API 请求**: NetworkFirst（优先网络）

---

**返回**: [根目录文档](../CLAUDE.md)
