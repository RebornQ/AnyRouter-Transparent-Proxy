import ky, { type KyInstance, TimeoutError as KyTimeoutError, HTTPError } from 'ky'
import type {
  SystemStats,
  ErrorLogsResponse,
  SystemConfig,
  ConfigUpdateRequest,
  ConfigUpdateResponse,
  ConfigResponse,
  ConfigEntry
} from '@/types'

// API 配置
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api'
const API_TIMEOUT = 15000

// Token 存储键
const AUTH_TOKEN_KEY = 'dashboard_api_key'

/**
 * 认证失败事件，允许 UI 优雅处理会话过期
 *
 * 用法示例：
 * window.addEventListener(AUTH_FAILURE_EVENT, () => { router.push('/login') })
 */
export const AUTH_FAILURE_EVENT = 'auth:failure'

// 认证 Token 管理
const getAuthToken = (): string | null => localStorage.getItem(AUTH_TOKEN_KEY)

// 创建 ky 实例，带有认证、重试和错误处理
const createApiClient = (): KyInstance => {
  return ky.create({
    prefixUrl: API_BASE_URL,
    timeout: API_TIMEOUT,
    retry: {
      limit: 2,
      methods: ['get', 'head'],
      statusCodes: [408, 429, 502, 503, 504],
      backoffLimit: 3000
    },
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
          if (!response.ok) {
            const body = await response.clone().json().catch(() => ({}))
            const detail = body?.detail
            const detailMessage = detail
              ? (typeof detail === 'string' ? detail : JSON.stringify(detail))
              : null
            const message = body.message || detailMessage || `HTTP Error: ${response.statusText}`

            if (response.status === 401) {
              localStorage.removeItem(AUTH_TOKEN_KEY)
              window.dispatchEvent(new CustomEvent(AUTH_FAILURE_EVENT))
              throw new ApiError('认证失败或会话已过期', 401, body)
            }

            throw new ApiError(message, response.status, body)
          }
        }
      ],
      beforeError: [
        (error: HTTPError) => {
          if (error instanceof KyTimeoutError) {
            throw new ApiError('请求超时，请检查您的网络连接', 408)
          }
          if (error instanceof TypeError && error.message.toLowerCase().includes('failed to fetch')) {
            throw new ApiError('网络错误，无法连接到服务器', 0)
          }
          return error
        }
      ]
    }
  })
}

// API 客户端实例
const api = createApiClient()

// 自定义错误类
export class ApiError extends Error {
  status: number
  body?: any

  constructor(message: string, status: number, body?: any) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.body = body
  }
}

// 配置管理 API
export const configApi = {
  // 获取系统配置（旧接口,返回扁平结构）
  async getConfig(): Promise<SystemConfig> {
    const endpoint = getAuthToken() ? 'admin/config/private' : 'admin/config'
    const response = await api.get(endpoint).json<SystemConfig>()
    return response
  },

  // 获取完整配置响应（新接口,包含 entries 和元数据）
  async getConfigFull(): Promise<ConfigResponse> {
    const endpoint = getAuthToken() ? 'admin/config/private' : 'admin/config'
    const response = await api.get(endpoint).json<ConfigResponse>()
    return response
  },

  // 获取配置元数据
  async getConfigMetadata(): Promise<{ metadata: ConfigEntry[] }> {
    const response = await api.get('admin/config/metadata').json<{ metadata: ConfigEntry[] }>()
    return response
  },

  // 更新系统配置
  async updateConfig(config: ConfigUpdateRequest): Promise<ConfigUpdateResponse> {
    const response = await api.put('admin/config', {
      json: config
    }).json<ConfigUpdateResponse>()
    return response
  },

  // 设置认证 Token
  setToken(token: string): void {
    localStorage.setItem(AUTH_TOKEN_KEY, token)
  },

  // 清除认证 Token
  clearToken(): void {
    localStorage.removeItem(AUTH_TOKEN_KEY)
  },

  // 验证当前存储的 Token
  async verifyToken(): Promise<{ valid: boolean; reason?: string }> {
    const token = getAuthToken()
    if (!token) {
      return { valid: false, reason: 'unauthorized' }
    }
    try {
      await api.head('admin/config')
      return { valid: true }
    } catch (error) {
      if (error instanceof ApiError) {
        return {
          valid: false,
          reason: error.status === 401 ? 'unauthorized' : `server_error: ${error.status}`
        }
      }
      return { valid: false, reason: 'network' }
    }
  },

  // 验证指定的 Token（无副作用）
  async verifyTokenWithKey(apiKey: string): Promise<{
    valid: boolean
    reason?: 'unauthorized' | 'network' | 'timeout' | 'server_error'
  }> {
    try {
      const tempClient = ky.create({
        prefixUrl: API_BASE_URL,
        timeout: API_TIMEOUT,
        headers: {
          Authorization: `Bearer ${apiKey}`
        }
      })
      // 使用受保护的 HEAD 接口校验 DASHBOARD_API_KEY，避免公有接口绕过
      await tempClient.head('admin/config')
      return { valid: true }
    } catch (err: any) {
      if (err instanceof HTTPError) {
        const status = err.response.status
        if (status === 401 || status === 403) {
          return { valid: false, reason: 'unauthorized' }
        }
        if (status >= 500) {
          return { valid: false, reason: 'server_error' }
        }
      }

      if (err instanceof KyTimeoutError) {
        return { valid: false, reason: 'timeout' }
      }

      return { valid: false, reason: 'network' }
    }
  }
}

// 统计监控 API
export const statsApi = {
  // 获取系统统计
  async getStats(timeRange?: string): Promise<SystemStats> {
    const searchParams: Record<string, string | number> = {}

    if (timeRange) {
      const match = /^(\d+)([mh])$/i.exec(timeRange)
      const nowSeconds = Math.floor(Date.now() / 1000)
      if (match) {
        const value = Number(match[1])
        const unit = match[2].toLowerCase()
        const offsetSeconds = unit === 'm' ? value * 60 : value * 3600
        searchParams.end_time = nowSeconds
        searchParams.start_time = nowSeconds - offsetSeconds
      } else {
        // 兼容未匹配格式，直接透传
        searchParams.time_range = timeRange
      }
    }

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

// 健康检查 API
export const healthApi = {
  // 检查后端健康状态（不带认证，直接访问 /health）
  async checkHealth(): Promise<{ status: string; service: string; boot_id: string; started_at: number }> {
    const response = await fetch('/health', { cache: 'no-store' })
    if (!response.ok) {
      throw new Error('Health check failed')
    }
    return response.json()
  }
}

// 导出统一的 API 客户端
export default api
