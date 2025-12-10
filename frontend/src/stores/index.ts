import { defineStore } from 'pinia'
import { ref, computed, nextTick } from 'vue'
import { configApi } from '@/services/api'
import type { SystemConfig } from '@/types'

// 主题存储
export const useThemeStore = defineStore('theme', () => {
  // 状态
  const isDark = ref(false)
  const systemPreference = ref<'light' | 'dark' | 'auto'>('auto')

  // 计算属性
  const currentTheme = computed(() => {
    if (systemPreference.value === 'auto') {
      return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
    }
    return systemPreference.value
  })

  const isDarkMode = computed(() => {
    return systemPreference.value === 'dark' ||
           (systemPreference.value === 'auto' && window.matchMedia('(prefers-color-scheme: dark)').matches)
  })

  // 方法
  const setTheme = async (theme: 'light' | 'dark' | 'auto') => {
    systemPreference.value = theme
    // 等待 Vue 响应式系统更新计算属性
    await nextTick()
    updateThemeClass()
    saveToStorage()
  }

  const toggleDarkMode = async () => {
    if (systemPreference.value === 'auto') {
      await setTheme('dark')
    } else if (systemPreference.value === 'dark') {
      await setTheme('light')
    } else {
      await setTheme('auto')
    }
  }

  const updateThemeClass = () => {
    const html = document.documentElement
    if (isDarkMode.value) {
      html.classList.add('dark')
    } else {
      html.classList.remove('dark')
    }
  }

  const saveToStorage = () => {
    localStorage.setItem('theme_preference', systemPreference.value)
  }

  const loadFromStorage = () => {
    const saved = localStorage.getItem('theme_preference')
    if (saved && ['light', 'dark', 'auto'].includes(saved)) {
      systemPreference.value = saved as 'light' | 'dark' | 'auto'
    }
  }

  const init = () => {
    loadFromStorage()
    updateThemeClass()

    // 监听系统主题变化
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
    mediaQuery.addEventListener('change', updateThemeClass)
  }

  return {
    // 状态
    isDark,
    systemPreference,
    // 计算属性
    currentTheme,
    isDarkMode,
    // 方法
    setTheme,
    toggleDarkMode,
    init
  }
})

// 配置管理存储
export const useConfigStore = defineStore('config', () => {
  // 状态
  const config = ref<SystemConfig | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)
  const lastUpdated = ref<number>(0)

  // 计算属性
  const isLoaded = computed(() => config.value !== null)
  const hasChanges = computed(() => {
    if (!config.value) return false
    // TODO: 实现变更检测逻辑
    return false
  })

  // 方法
  const loadConfig = async () => {
    if (loading.value) return

    loading.value = true
    error.value = null

    try {
      config.value = await configApi.getConfig()
      lastUpdated.value = Date.now()
    } catch (err) {
      error.value = err instanceof Error ? err.message : '加载配置失败'
      throw err
    } finally {
      loading.value = false
    }
  }

  const updateConfig = async (updates: Partial<SystemConfig>) => {
    if (!config.value) {
      throw new Error('配置未加载')
    }

    loading.value = true
    error.value = null

    try {
      // 合并更新
      const mergedConfig = { ...config.value, ...updates }

      // 发送到后端
      await configApi.updateConfig({ custom_headers: mergedConfig.custom_headers })

      // 更新本地状态
      config.value = mergedConfig
      lastUpdated.value = Date.now()
    } catch (err) {
      error.value = err instanceof Error ? err.message : '更新配置失败'
      throw err
    } finally {
      loading.value = false
    }
  }

  const resetError = () => {
    error.value = null
  }

  return {
    // 状态
    config,
    loading,
    error,
    lastUpdated,
    // 计算属性
    isLoaded,
    hasChanges,
    // 方法
    loadConfig,
    updateConfig,
    resetError
  }
})

// 统计数据存储
export const useStatsStore = defineStore('stats', () => {
  // 状态
  const stats = ref<any>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)
  const lastUpdated = ref<number>(0)
  const autoRefresh = ref(true)
  const refreshInterval = ref(5000) // 5秒

  // 计算属性
  const isLoaded = computed(() => stats.value !== null)
  const isStale = computed(() => {
    if (!lastUpdated.value) return true
    const age = Date.now() - lastUpdated.value
    return age > refreshInterval.value * 2 // 数据过期阈值
  })

  // 定时器引用
  let refreshTimer: number | null = null

  // 方法
  const loadStats = async (timeRange?: string) => {
    if (loading.value) return

    loading.value = true
    error.value = null

    try {
      const { statsApi } = await import('@/services/api')
      stats.value = await statsApi.getStats(timeRange)
      lastUpdated.value = Date.now()
    } catch (err) {
      error.value = err instanceof Error ? err.message : '加载统计数据失败'
      throw err
    } finally {
      loading.value = false
    }
  }

  const startAutoRefresh = (interval?: number) => {
    if (interval) {
      refreshInterval.value = interval
    }

    autoRefresh.value = true
    scheduleRefresh()
  }

  const stopAutoRefresh = () => {
    autoRefresh.value = false
    if (refreshTimer) {
      clearInterval(refreshTimer)
      refreshTimer = null
    }
  }

  const scheduleRefresh = () => {
    if (refreshTimer) {
      clearInterval(refreshTimer)
    }

    refreshTimer = window.setInterval(() => {
      if (autoRefresh.value && !document.hidden) {
        loadStats().catch(console.error)
      }
    }, refreshInterval.value)
  }

  const forceRefresh = () => {
    return loadStats()
  }

  // 清理方法
  const $dispose = () => {
    stopAutoRefresh()
  }

  return {
    // 状态
    stats,
    loading,
    error,
    lastUpdated,
    autoRefresh,
    refreshInterval,
    // 计算属性
    isLoaded,
    isStale,
    // 方法
    loadStats,
    startAutoRefresh,
    stopAutoRefresh,
    forceRefresh,
    $dispose
  }
})

// 日志存储
export const useLogsStore = defineStore('logs', () => {
  // 状态
  const logs = ref<any[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)
  const filters = ref({
    level: [] as string[],
    search: ''
  })
  const maxLogs = ref(1000) // 最大日志数量

  // 方法
  const addLog = (log: any) => {
    logs.value.unshift(log)

    // 限制日志数量
    if (logs.value.length > maxLogs.value) {
      logs.value = logs.value.slice(0, maxLogs.value)
    }
  }

  const clearLogs = () => {
    logs.value = []
  }

  const setFilters = (newFilters: Partial<typeof filters.value>) => {
    filters.value = { ...filters.value, ...newFilters }
  }

  const filteredLogs = computed(() => {
    let filtered = logs.value

    // 级别过滤
    if (filters.value.level.length > 0) {
      filtered = filtered.filter(log => filters.value.level.includes(log.level))
    }

    // 搜索过滤
    if (filters.value.search) {
      const searchLower = filters.value.search.toLowerCase()
      filtered = filtered.filter(log =>
        log.message.toLowerCase().includes(searchLower) ||
        log.path?.toLowerCase().includes(searchLower) ||
        log.request_id?.toLowerCase().includes(searchLower)
      )
    }

    return filtered
  })

  return {
    // 状态
    logs,
    loading,
    error,
    filters,
    maxLogs,
    // 计算属性
    filteredLogs,
    // 方法
    addLog,
    clearLogs,
    setFilters
  }
})

// 通知存储
export const useNotificationStore = defineStore('notification', () => {
  // 状态
  const notifications = ref<Array<{
    id: string
    type: 'success' | 'error' | 'warning' | 'info'
    title: string
    message: string
    duration?: number
    timestamp: number
  }>>([])

  // 方法
  const addNotification = (notification: Omit<typeof notifications.value[0], 'id' | 'timestamp'>) => {
    const id = Date.now().toString() + Math.random().toString(36).substr(2, 9)
    const timestamp = Date.now()

    notifications.value.push({
      ...notification,
      id,
      timestamp
    })

    // 自动移除通知（如果有持续时间）
    if (notification.duration && notification.duration > 0) {
      setTimeout(() => {
        removeNotification(id)
      }, notification.duration)
    }
  }

  const removeNotification = (id: string) => {
    const index = notifications.value.findIndex(n => n.id === id)
    if (index > -1) {
      notifications.value.splice(index, 1)
    }
  }

  const clearNotifications = () => {
    notifications.value = []
  }

  // 便捷方法
  const success = (title: string, message: string, duration = 5000) => {
    addNotification({ type: 'success', title, message, duration })
  }

  const error = (title: string, message: string, duration = 0) => {
    addNotification({ type: 'error', title, message, duration })
  }

  const warning = (title: string, message: string, duration = 5000) => {
    addNotification({ type: 'warning', title, message, duration })
  }

  const info = (title: string, message: string, duration = 3000) => {
    addNotification({ type: 'info', title, message, duration })
  }

  return {
    // 状态
    notifications,
    // 方法
    addNotification,
    removeNotification,
    clearNotifications,
    // 便捷方法
    success,
    error,
    warning,
    info
  }
})

// 认证状态存储
export const useAuthStore = defineStore('auth', () => {
  // 状态
  const isAuthenticated = ref(false)
  const token = ref<string | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)
  const initializing = ref(true)

  // 计算属性
  const hasToken = computed(() => !!token.value)

  // 方法
  const login = async (apiKey: string) => {
    loading.value = true
    error.value = null

    try {
      // 设置 Token
      configApi.setToken(apiKey)
      token.value = apiKey

      // 验证 Token
      const isValid = await configApi.verifyToken()
      if (isValid) {
        isAuthenticated.value = true
        // 将 Token 保存到 localStorage
        localStorage.setItem('dashboard_api_key', apiKey)
      } else {
        throw new Error('API Key 无效')
      }
    } catch (err) {
      // 清除无效 Token
      logout()
      error.value = err instanceof Error ? err.message : '登录失败'
      throw err
    } finally {
      loading.value = false
    }
  }

  const logout = () => {
    configApi.clearToken()
    token.value = null
    isAuthenticated.value = false
    error.value = null
    localStorage.removeItem('dashboard_api_key')
  }

  const checkAuth = async () => {
    const savedToken = localStorage.getItem('dashboard_api_key')
    if (!savedToken) return false

    try {
      token.value = savedToken
      configApi.setToken(savedToken)
      const isValid = await configApi.verifyToken()
      isAuthenticated.value = isValid
      return isValid
    } catch {
      logout()
      return false
    }
  }

  const initAuth = async () => {
    initializing.value = true
    try {
      // 由于我们已经移除了认证，这里直接设置为已认证
      isAuthenticated.value = true
      initializing.value = false
    } catch (err) {
      error.value = err instanceof Error ? err.message : '认证初始化失败'
      initializing.value = false
    }
  }

  return {
    // 状态
    isAuthenticated,
    token,
    loading,
    error,
    initializing,
    // 计算属性
    hasToken,
    // 方法
    login,
    logout,
    checkAuth,
    initAuth
  }
})

// 导出所有 store
export default {
  useThemeStore,
  useConfigStore,
  useStatsStore,
  useLogsStore,
  useAuthStore,
  useNotificationStore
}