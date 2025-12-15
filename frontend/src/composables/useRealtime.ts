import { ref, onUnmounted, computed } from 'vue'
import { useStatsStore } from '@/stores'
import { statsApi } from '@/services/api'

// 连接状态枚举
export const ConnectionState = {
  DISCONNECTED: 'disconnected',
  CONNECTING: 'connecting',
  CONNECTED: 'connected',
  RECONNECTING: 'reconnecting',
  ERROR: 'error'
} as const

export type ConnectionState = typeof ConnectionState[keyof typeof ConnectionState]

// 实时统计数据组合函数
export function useRealtimeStats(options: {
  interval?: number
  autoRefresh?: boolean
} = {}) {
  // 状态
  const loading = ref(false)
  const error = ref<string | null>(null)
  const lastUpdated = ref<number>(0)
  const currentTimeRange = ref<string | undefined>(undefined)

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
    // 注意：不在开头清空 error，只在加载成功时清空，避免错误提示闪烁

    try {
      const rangeToUse = typeof timeRange === 'string' ? timeRange : currentTimeRange.value
      await statsStore.loadStats(rangeToUse)
      currentTimeRange.value = rangeToUse
      lastUpdated.value = Date.now()
      // 只在加载成功时清空错误状态
      error.value = null
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
        loadStats(currentTimeRange.value).catch(console.error)
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
    return loadStats(currentTimeRange.value)
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
