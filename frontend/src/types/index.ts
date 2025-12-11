// API 响应类型
export interface ApiResponse<T = any> {
  data?: T
  message?: string
  success?: boolean
}

// 统计数据类型
export interface SystemStats {
  summary: {
    total_requests: number
    successful_requests: number
    failed_requests: number
    success_rate: number
    avg_response_time: number
    requests_per_second: number
    total_bytes_sent: number
    total_bytes_sent_formatted: string
    uptime_seconds: number
  }
  performance: {
    response_time_ms: {
      p50: number
      p95: number
      p99: number
    }
  }
  time_series: {
    requests_per_minute: Array<{ time: number; count: number }>  // time 为 Unix 时间戳（秒级）
    errors_per_minute: Array<{ time: number; count: number }>    // time 为 Unix 时间戳（秒级）
    bytes_per_minute: Array<{ time: number; count: number }>     // time 为 Unix 时间戳（秒级）
  }
  top_paths: Record<string, {
    count: number
    bytes: number
    errors: number
    avg_response_time: number
    success_rate: number
  }>
  recent_requests: Array<{
    request_id: string
    path: string
    method: string
    status_code: number
    status?: string
    bytes?: number
    response_time: number
    timestamp: number
    error?: string
    response_content?: string
  }>
}

// 错误日志类型
export interface ErrorLog {
  request_id: string
  path: string
  error: string
  timestamp: number
  formatted_time: string
  response_time: number
  response_content?: string
}

export interface ErrorLogsResponse {
  errors: ErrorLog[]
  pagination: {
    total: number
    limit: number
    offset: number
    has_more: boolean
  }
  statistics: {
    total_errors: number
    total_requests: number
    error_rate: number
    errors_by_path: Record<string, number>
  }
}

// 配置类型
export interface SystemConfig {
  target_base_url: string
  preserve_host: boolean
  system_prompt_replacement: string | null
  system_prompt_block_insert_if_not_exist: boolean
  debug_mode: boolean
  port: number
  custom_headers: Record<string, string>
  dashboard_enabled: boolean
}

export interface ConfigUpdateRequest {
  custom_headers?: Record<string, string>
}

// 日志流类型
export interface LogEntry {
  timestamp: number
  level: 'INFO' | 'WARNING' | 'ERROR'
  message: string
  path?: string
  request_id?: string
  formatted_time: string
  type?: string
  response_content?: string
  _expanded?: boolean
}

export interface LogHistoryResponse {
  logs: LogEntry[]
  pagination: {
    total: number
    limit: number
    offset: number
    has_more: boolean
  }
}

// 路由类型
export interface RouteMeta {
  title: string
  icon?: string
}

// 菜单项类型
export interface MenuItem {
  name: string
  path: string
  icon: string
  badge?: string | number
}
