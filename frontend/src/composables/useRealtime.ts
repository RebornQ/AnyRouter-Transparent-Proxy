import { ref, onUnmounted, computed } from 'vue'
import { useLogsStore, useStatsStore } from '@/stores'
import { logsApi, statsApi } from '@/services/api'
import type { LogEntry } from '@/types'

// 连接状态枚举
export const ConnectionState = {
  DISCONNECTED: 'disconnected',
  CONNECTING: 'connecting',
  CONNECTED: 'connected',
  RECONNECTING: 'reconnecting',
  ERROR: 'error'
} as const

export type ConnectionState = typeof ConnectionState[keyof typeof ConnectionState]

// 重连配置
interface ReconnectConfig {
  maxRetries: number
  initialDelay: number
  maxDelay: number
  backoffFactor: number
}

// 实时数据配置
interface RealtimeConfig {
  autoReconnect?: boolean
  reconnectConfig?: ReconnectConfig
  heartbeatInterval?: number
}

// 默认重连配置
const DEFAULT_RECONNECT_CONFIG: ReconnectConfig = {
  maxRetries: 10,
  initialDelay: 1000,
  maxDelay: 30000,
  backoffFactor: 2
}

// 日志流组合函数
export function useLogStream(options: {
  level?: LogEntry['level'][]
  search?: string
  config?: RealtimeConfig
} = {}) {
  // 状态
  const connectionState = ref<ConnectionState>(ConnectionState.DISCONNECTED)
  const error = ref<string | null>(null)
  const retryCount = ref(0)
  const lastConnected = ref<number>(0)

  // 配置
  const config = ref<RealtimeConfig>({
    autoReconnect: true,
    reconnectConfig: DEFAULT_RECONNECT_CONFIG,
    heartbeatInterval: 30000,
    ...options.config
  })

  // Store
  const logsStore = useLogsStore()

  // EventSource 实例
  let eventSource: EventSource | null = null
  let reconnectTimer: number | null = null
  let heartbeatTimer: number | null = null

  // 计算属性
  const isConnected = computed(() => connectionState.value === ConnectionState.CONNECTED)
  const isConnecting = computed(() =>
    connectionState.value === ConnectionState.CONNECTING ||
    connectionState.value === ConnectionState.RECONNECTING
  )
  const hasError = computed(() => connectionState.value === ConnectionState.ERROR)

  // 计算重连延迟
  const calculateReconnectDelay = (retryNumber: number): number => {
    const { initialDelay, maxDelay, backoffFactor } = config.value.reconnectConfig!
    const delay = initialDelay * Math.pow(backoffFactor, retryNumber)
    return Math.min(delay, maxDelay)
  }

  // 清理连接
  const cleanup = () => {
    if (eventSource) {
      eventSource.close()
      eventSource = null
    }

    if (reconnectTimer) {
      clearTimeout(reconnectTimer)
      reconnectTimer = null
    }

    if (heartbeatTimer) {
      clearInterval(heartbeatTimer)
      heartbeatTimer = null
    }
  }

  // 处理连接打开
  const handleOpen = () => {
    console.log('[LogStream] 连接已建立')
    connectionState.value = ConnectionState.CONNECTED
    error.value = null
    retryCount.value = 0
    lastConnected.value = Date.now()

    // 启动心跳检测
    startHeartbeat()
  }

  // 处理连接错误
  const handleError = (event: Event) => {
    console.error('[LogStream] 连接错误:', event)

    if (connectionState.value === ConnectionState.CONNECTED) {
      // 连接中断，尝试重连
      connectionState.value = ConnectionState.ERROR
      error.value = '连接意外中断'

      if (config.value.autoReconnect) {
        scheduleReconnect()
      }
    }
  }

  // 处理消息接收
  const handleMessage = (event: MessageEvent) => {
    try {
      const log: LogEntry = JSON.parse(event.data)
      logsStore.addLog(log)
    } catch (err) {
      console.error('[LogStream] 解析日志消息失败:', err)
    }
  }

  // 处理心跳
  const handleHeartbeat = () => {
    // 心跳响应，连接正常
    console.debug('[LogStream] 心跳响应')
  }

  // 启动心跳检测
  const startHeartbeat = () => {
    if (heartbeatTimer) {
      clearInterval(heartbeatTimer)
    }

    heartbeatTimer = window.setInterval(() => {
      if (eventSource?.readyState === EventSource.OPEN) {
        // 连接正常，发送心跳（如果支持的话）
        console.debug('[LogStream] 心跳检测')
      } else {
        console.warn('[LogStream] 心跳检测失败，触发重连')
        connectionState.value = ConnectionState.ERROR
        if (config.value.autoReconnect) {
          scheduleReconnect()
        }
      }
    }, config.value.heartbeatInterval!)
  }

  // 安排重连
  const scheduleReconnect = () => {
    const { maxRetries } = config.value.reconnectConfig!

    if (retryCount.value >= maxRetries) {
      console.error('[LogStream] 已达到最大重试次数，停止重连')
      connectionState.value = ConnectionState.ERROR
      error.value = `连接失败，已重试 ${maxRetries} 次`
      return
    }

    const delay = calculateReconnectDelay(retryCount.value)

    console.log(`[LogStream] 将在 ${delay}ms 后进行第 ${retryCount.value + 1} 次重连`)

    connectionState.value = ConnectionState.RECONNECTING
    error.value = `正在重连... (${retryCount.value + 1}/${maxRetries})`

    reconnectTimer = window.setTimeout(() => {
      retryCount.value++
      connect()
    }, delay)
  }

  // 建立连接
  const connect = () => {
    if (eventSource) {
      cleanup()
    }

    console.log('[LogStream] 正在建立连接...')
    connectionState.value = ConnectionState.CONNECTING

    try {
      eventSource = logsApi.createLogStream({
        level: options.level,
        search: options.search
      })

      eventSource.addEventListener('open', handleOpen)
      eventSource.addEventListener('error', handleError)
      eventSource.addEventListener('message', handleMessage)
      eventSource.addEventListener('heartbeat', handleHeartbeat)

      // 监听特定日志级别
      if (options.level?.length) {
        options.level.forEach(level => {
          eventSource?.addEventListener(level.toLowerCase(), handleMessage)
        })
      }
    } catch (err) {
      console.error('[LogStream] 创建连接失败:', err)
      connectionState.value = ConnectionState.ERROR
      error.value = err instanceof Error ? err.message : '创建连接失败'

      if (config.value.autoReconnect) {
        scheduleReconnect()
      }
    }
  }

  // 断开连接
  const disconnect = () => {
    console.log('[LogStream] 断开连接')
    cleanup()
    connectionState.value = ConnectionState.DISCONNECTED
  }

  // 手动重连
  const reconnect = () => {
    retryCount.value = 0
    error.value = null
    connect()
  }

  // 更新过滤器
  const updateFilters = (filters: {
    level?: LogEntry['level'][]
    search?: string
  }) => {
    // 更新选项
    Object.assign(options, filters)

    // 如果连接正常，重新连接以应用新过滤器
    if (isConnected.value) {
      disconnect()
      connect()
    }
  }

  // 组件卸载时清理
  onUnmounted(() => {
    cleanup()
  })

  // 初始化连接
  if (typeof window !== 'undefined') {
    connect()
  }

  return {
    // 状态
    connectionState,
    error,
    retryCount,
    lastConnected,
    // 计算属性
    isConnected,
    isConnecting,
    hasError,
    // 方法
    connect,
    disconnect,
    reconnect,
    updateFilters
  }
}

// 实时统计数据组合函数
export function useRealtimeStats(options: {
  interval?: number
  autoRefresh?: boolean
} = {}) {
  // 状态
  const loading = ref(false)
  const error = ref<string | null>(null)
  const lastUpdated = ref<number>(0)

  // 配置
  const interval = ref(options.interval || 5000) // 5秒刷新
  const autoRefresh = ref(options.autoRefresh !== false)

  // Store
  const statsStore = useStatsStore()

  // 定时器引用
  let refreshTimer: number | null = null

  // 加载统计数据
  const loadStats = async (timeRange?: string) => {
    if (loading.value) return

    loading.value = true
    error.value = null

    try {
      await statsStore.loadStats(timeRange)
      lastUpdated.value = Date.now()
    } catch (err) {
      error.value = err instanceof Error ? err.message : '加载统计数据失败'
      console.error('[RealtimeStats] 加载失败:', err)
    } finally {
      loading.value = false
    }
  }

  // 开始自动刷新
  const startAutoRefresh = (newInterval?: number) => {
    if (newInterval) {
      interval.value = newInterval
    }

    if (refreshTimer) {
      clearInterval(refreshTimer)
    }

    autoRefresh.value = true

    refreshTimer = window.setInterval(() => {
      if (autoRefresh.value && !document.hidden) {
        loadStats().catch(console.error)
      }
    }, interval.value)
  }

  // 停止自动刷新
  const stopAutoRefresh = () => {
    if (refreshTimer) {
      clearInterval(refreshTimer)
      refreshTimer = null
    }
    autoRefresh.value = false
  }

  // 强制刷新
  const forceRefresh = () => {
    return loadStats()
  }

  // 组件卸载时清理
  onUnmounted(() => {
    stopAutoRefresh()
  })

  // 初始化
  if (autoRefresh.value) {
    // 初始加载
    loadStats()
    // 开始自动刷新
    startAutoRefresh()
  }

  return {
    // 状态
    loading,
    error,
    lastUpdated,
    interval,
    autoRefresh,
    // 计算属性（从 Store 获取）
    stats: computed(() => statsStore.stats),
    isLoaded: computed(() => statsStore.isLoaded),
    isStale: computed(() => statsStore.isStale),
    // 方法
    loadStats,
    startAutoRefresh,
    stopAutoRefresh,
    forceRefresh
  }
}

// 实时错误监控组合函数
export function useRealtimeErrors(options: {
  interval?: number
  autoRefresh?: boolean
} = {}) {
  // 状态
  const loading = ref(false)
  const error = ref<string | null>(null)
  const errors = ref<any[]>([])
  const lastUpdated = ref<number>(0)

  // 配置
  const interval = ref(options.interval || 10000) // 10秒刷新
  const autoRefresh = ref(options.autoRefresh !== false)

  // 定时器引用
  let refreshTimer: number | null = null

  // 加载错误数据
  const loadErrors = async (limit = 100) => {
    if (loading.value) return

    loading.value = true
    error.value = null

    try {
      const response = await statsApi.getErrors({ limit })
      errors.value = response.errors
      lastUpdated.value = Date.now()
    } catch (err) {
      error.value = err instanceof Error ? err.message : '加载错误数据失败'
      console.error('[RealtimeErrors] 加载失败:', err)
    } finally {
      loading.value = false
    }
  }

  // 开始自动刷新
  const startAutoRefresh = (newInterval?: number) => {
    if (newInterval) {
      interval.value = newInterval
    }

    if (refreshTimer) {
      clearInterval(refreshTimer)
    }

    autoRefresh.value = true

    refreshTimer = window.setInterval(() => {
      if (autoRefresh.value && !document.hidden) {
        loadErrors().catch(console.error)
      }
    }, interval.value)
  }

  // 停止自动刷新
  const stopAutoRefresh = () => {
    if (refreshTimer) {
      clearInterval(refreshTimer)
      refreshTimer = null
    }
    autoRefresh.value = false
  }

  // 清除错误
  const clearErrors = () => {
    errors.value = []
  }

  // 组件卸载时清理
  onUnmounted(() => {
    stopAutoRefresh()
  })

  // 初始化
  if (autoRefresh.value) {
    // 初始加载
    loadErrors()
    // 开始自动刷新
    startAutoRefresh()
  }

  return {
    // 状态
    loading,
    error,
    errors,
    lastUpdated,
    interval,
    autoRefresh,
    // 方法
    loadErrors,
    startAutoRefresh,
    stopAutoRefresh,
    clearErrors
  }
}