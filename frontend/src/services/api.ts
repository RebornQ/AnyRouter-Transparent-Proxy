import ky, { type KyInstance } from 'ky'
import type {
  SystemStats,
  ErrorLogsResponse,
  SystemConfig,
  ConfigUpdateRequest,
  LogEntry,
  LogHistoryResponse
} from '@/types'

// API 配置
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api'
const API_TIMEOUT = 30000

// 认证 Token 管理
const getAuthToken = (): string | null => {
  return localStorage.getItem('dashboard_api_key')
}

// 创建 ky 实例，带有认证和错误处理
const createApiClient = (): KyInstance => {
  return ky.create({
    prefixUrl: API_BASE_URL,
    timeout: API_TIMEOUT,
    hooks: {
      beforeRequest: [
        (request) => {
          const token = getAuthToken()
          if (token) {
            request.headers.set('Authorization', `Bearer ${token}`)
          }
        }
      ],
      afterResponse: [
        async (_request, _options, response) => {
          if (response.status === 401) {
            // Token 无效，清除并跳转到登录
            localStorage.removeItem('dashboard_api_key')
            window.location.href = '/admin/login'
            throw new Error('认证失败，请重新登录')
          }

          if (!response.ok) {
            const body = await response.clone().json().catch(() => ({}))
            throw new ApiErrorClass(
              body.message || `HTTP ${response.status}: ${response.statusText}`,
              response.status,
              body
            )
          }
        }
      ],
      beforeError: [
        (error: any) => {
          console.error('[API Error]', error)

          // 网络错误重试逻辑
          if (error instanceof TypeError && error.message.includes('fetch')) {
            console.warn('[API] 网络错误，请检查连接')
          }

          throw error
        }
      ]
    }
  })
}

// 自定义错误类
class ApiErrorClass extends Error {
  status: number
  body?: any

  constructor(message: string, status: number, body?: any) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.body = body
  }
}

// 导出 ApiError 类型
export type ApiError = ApiErrorClass

// API 客户端实例
const api = createApiClient()

// 配置管理 API
export const configApi = {
  // 获取系统配置
  async getConfig(): Promise<SystemConfig> {
    const response = await api.get('admin/config').json<SystemConfig>()
    return response
  },

  // 更新系统配置
  async updateConfig(config: ConfigUpdateRequest): Promise<SystemConfig> {
    const response = await api.put('admin/config', {
      json: config
    }).json<SystemConfig>()
    return response
  },

  // 设置认证 Token
  setToken(token: string): void {
    localStorage.setItem('dashboard_api_key', token)
  },

  // 清除认证 Token
  clearToken(): void {
    localStorage.removeItem('dashboard_api_key')
  },

  // 验证 Token
  async verifyToken(): Promise<boolean> {
    try {
      await this.getConfig()
      return true
    } catch {
      return false
    }
  }
}

// 统计监控 API
export const statsApi = {
  // 获取系统统计
  async getStats(timeRange?: string): Promise<SystemStats> {
    const searchParams = timeRange ? { time_range: timeRange } : undefined
    const response = await api.get('admin/stats', {
      searchParams
    }).json<SystemStats>()
    return response
  },

  // 获取错误日志
  async getErrors(options: {
    limit?: number
    offset?: number
    timeRange?: string
  } = {}): Promise<ErrorLogsResponse> {
    const searchParams: Record<string, string> = {}

    if (options.limit) searchParams.limit = options.limit.toString()
    if (options.offset) searchParams.offset = options.offset.toString()
    if (options.timeRange) searchParams.time_range = options.timeRange

    const response = await api.get('admin/errors', {
      searchParams
    }).json<ErrorLogsResponse>()
    return response
  }
}

// 日志流 API
export const logsApi = {
  // 创建日志流 SSE 连接
  createLogStream(options: {
    level?: LogEntry['level'][]
    search?: string
  } = {}): EventSource {
    const searchParams = new URLSearchParams()

    if (options.level?.length) {
      searchParams.set('level', options.level.join(','))
    }

    if (options.search) {
      searchParams.set('search', options.search)
    }

    const token = getAuthToken()
    if (token) {
      searchParams.set('token', token)
    }

    const url = `${API_BASE_URL}/admin/logs/stream?${searchParams.toString()}`

    return new EventSource(url, {
      withCredentials: true
    })
  },

  // 获取历史日志
  async getHistoryLogs(params: {
    start_time?: string
    end_time?: string
    level?: string
    path_filter?: string
    limit?: number
    offset?: number
  } = {}): Promise<LogHistoryResponse> {
    const searchParams: Record<string, string> = {}

    if (params.start_time) searchParams.start_time = params.start_time
    if (params.end_time) searchParams.end_time = params.end_time
    if (params.level) searchParams.level = params.level
    if (params.path_filter) searchParams.path_filter = params.path_filter
    if (typeof params.limit === 'number') searchParams.limit = params.limit.toString()
    if (typeof params.offset === 'number') searchParams.offset = params.offset.toString()

    const response = await api.get('admin/logs/history', {
      searchParams
    }).json<LogHistoryResponse>()
    return response
  },

  async clearLogs(): Promise<{ success: boolean; message?: string }> {
    return api.post('admin/logs/clear').json<{ success: boolean; message?: string }>()
  }
}

// 健康检查 API
export const healthApi = {
  // 检查后端健康状态
  async checkHealth(): Promise<{ status: string; timestamp: number }> {
    return api.get('health').json()
  }
}

// 导出统一的 API 客户端
export default api
