import { defineStore } from 'pinia'
import { ref, computed, nextTick } from 'vue'
import { configApi } from '@/services/api'
import type { SystemConfig, ConfigEntry, ConfigMetadata, ConfigUpdateRequest, ConfigUpdateResponse } from '@/types'

// 主题存储
export const useThemeStore = defineStore('theme', () => {
  // 状态
  const systemPreference = ref<'light' | 'dark' | 'auto'>('auto')
  let mediaQuery: MediaQueryList | null = null
  let mediaQueryListener: ((event: MediaQueryListEvent) => void) | null = null
  let initialized = false

  const ensureMediaQuery = () => {
    if (typeof window === 'undefined') return null
    if (!mediaQuery) {
      mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
    }
    return mediaQuery
  }

  // 计算属性
  const currentTheme = computed(() => {
    const prefersDark = ensureMediaQuery()?.matches ?? false
    if (systemPreference.value === 'auto') {
      return prefersDark ? 'dark' : 'light'
    }
    return systemPreference.value
  })

  const isDarkMode = computed(() => currentTheme.value === 'dark')

  // 方法
  const setTheme = async (theme: 'light' | 'dark' | 'auto') => {
    systemPreference.value = theme
    // 等待 Vue 响应式系统更新计算属性
    await nextTick()
    updateThemeClass()
    saveToStorage()
  }

  const toggleDarkMode = async () => {
    const nextTheme: 'light' | 'dark' = isDarkMode.value ? 'light' : 'dark'
    await setTheme(nextTheme)
  }

  const updateThemeClass = () => {
    if (typeof document === 'undefined') return
    const html = document.documentElement
    const theme = currentTheme.value
    html.classList.toggle('dark', theme === 'dark')
    html.dataset.theme = theme
  }

  const saveToStorage = () => {
    if (typeof localStorage === 'undefined') return
    localStorage.setItem('theme_preference', systemPreference.value)
  }

  const loadFromStorage = () => {
    if (typeof localStorage === 'undefined') return
    const saved = localStorage.getItem('theme_preference')
    if (saved && ['light', 'dark', 'auto'].includes(saved)) {
      systemPreference.value = saved as 'light' | 'dark' | 'auto'
    }
  }

  const bindSystemPreferenceListener = () => {
    const mq = ensureMediaQuery()
    if (!mq || mediaQueryListener) return

    mediaQueryListener = (_event: MediaQueryListEvent) => {
      if (systemPreference.value === 'auto') {
        updateThemeClass()
      }
    }

    if (mq.addEventListener) {
      mq.addEventListener('change', mediaQueryListener)
    } else if (mq.addListener) {
      mq.addListener(mediaQueryListener)
    }
  }

  const init = () => {
    if (initialized) {
      updateThemeClass()
      return
    }

    loadFromStorage()
    bindSystemPreferenceListener()
    updateThemeClass()
    initialized = true
  }

  return {
    // 状态
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

// 工具函数：深拷贝对象
function deepClone<T>(obj: T): T {
  return JSON.parse(JSON.stringify(obj))
}

// 工具函数：稳定序列化（用于比较）
function stableStringify(obj: any): string {
  if (obj === null || obj === undefined) return 'null'
  if (typeof obj !== 'object') return JSON.stringify(obj)
  if (Array.isArray(obj)) return JSON.stringify(obj.map(stableStringify))

  const keys = Object.keys(obj).sort()
  const sorted: Record<string, any> = {}
  for (const key of keys) {
    sorted[key] = obj[key]
  }
  return JSON.stringify(sorted)
}

// 配置管理存储
export const useConfigStore = defineStore('config', () => {
  // 核心配置数据
  const configEntries = ref<ConfigEntry[]>([])
  const originalEntries = ref<ConfigEntry[]>([])
  const metadataMap = ref<Record<string, ConfigMetadata>>({})

  // 加载状态
  const loading = ref(false)
  const loadingMetadata = ref(false)
  const error = ref<string | null>(null)
  const lastUpdated = ref<number>(0)

  // 编辑工作流状态
  const isEditing = ref(false)
  const isSaving = ref(false)
  const validationErrors = ref<Record<string, string | null>>({})

  // 重启提示状态
  const showRestartConfirm = ref(false)
  const requiresRestart = ref(false)

  // 兼容旧接口
  const config = ref<SystemConfig | null>(null)

  // 计算属性
  const isLoaded = computed(() => configEntries.value.length > 0)

  const hasChanges = computed(() => {
    if (!isEditing.value) return false
    if (configEntries.value.length !== originalEntries.value.length) return true
    return stableStringify(configEntries.value) !== stableStringify(originalEntries.value)
  })

  const changedEntries = computed(() => {
    if (!hasChanges.value) return []
    return configEntries.value.filter(entry => {
      const original = originalEntries.value.find(o => o.key === entry.key)
      if (!original) return true
      return stableStringify(original.value) !== stableStringify(entry.value)
    })
  })

  const hasValidationErrors = computed(() =>
    Object.values(validationErrors.value).some(err => err !== null && err !== undefined)
  )

  const canSave = computed(() => {
    const authStore = useAuthStore()
    return (
      hasChanges.value &&
      !hasValidationErrors.value &&
      !isSaving.value &&
      authStore.isConfigEditingAuthenticated
    )
  })

  // 将 ConfigEntry[] 转换为 SystemConfig
  const entriesToConfig = (entries: ConfigEntry[]): SystemConfig => {
    const result: Partial<SystemConfig> = {
      target_base_url: '',
      preserve_host: false,
      system_prompt_replacement: null,
      system_prompt_block_insert_if_not_exist: false,
      debug_mode: false,
      port: 8088,
      custom_headers: {},
      dashboard_enabled: false
    }
    const mapped = result as Record<string, any>

    for (const entry of entries) {
      if (entry.key === 'enable_dashboard' || entry.key === 'dashboard_enabled') {
        result.dashboard_enabled = Boolean(entry.value)
        continue
      }
      mapped[entry.key] = entry.value
    }

    return result as SystemConfig
  }

  // 方法：加载配置
  const loadConfig = async () => {
    if (loading.value) return

    loading.value = true
    error.value = null

    try {
      const response = await configApi.getConfigFull()

      // 保存原始 entries 和元数据
      const entries = response.entries || []
      configEntries.value = deepClone(entries)
      originalEntries.value = deepClone(entries)

      // 构建元数据映射
      const map: Record<string, ConfigMetadata> = {}
      for (const entry of entries) {
        map[entry.key] = entry.metadata
      }
      metadataMap.value = map

      // 兼容旧接口
      config.value = entriesToConfig(entries)

      lastUpdated.value = Date.now()
    } catch (err) {
      error.value = err instanceof Error ? err.message : '加载配置失败'
      throw err
    } finally {
      loading.value = false
    }
  }

  // 方法：加载元数据（如果需要单独加载）
  const loadMetadata = async () => {
    if (loadingMetadata.value) return

    loadingMetadata.value = true

    try {
      const response = await configApi.getConfigMetadata()
      const map: Record<string, ConfigMetadata> = {}
      for (const entry of response.metadata) {
        map[entry.key] = entry.metadata
      }
      metadataMap.value = map
    } catch (err) {
      console.error('加载元数据失败:', err)
    } finally {
      loadingMetadata.value = false
    }
  }

  // 方法：进入编辑模式
  const enterEditMode = () => {
    const authStore = useAuthStore()
    if (!authStore.isConfigEditingAuthenticated) {
      console.warn('未授权，无法进入编辑模式')
      error.value = '需要先通过 API Key 认证才能编辑配置'
      return false
    }

    originalEntries.value = deepClone(configEntries.value)
    isEditing.value = true
    validationErrors.value = {}
    return true
  }

  // 方法：更新单个配置项
  const updateEntry = (key: string, value: any) => {
    if (!isEditing.value) {
      console.warn('未进入编辑模式，无法更新配置')
      return
    }

    const index = configEntries.value.findIndex(e => e.key === key)
    if (index === -1) {
      console.warn(`配置项 ${key} 不存在`)
      return
    }

    configEntries.value[index].value = value

    // 更新兼容的 config 对象
    if (config.value) {
      config.value = { ...config.value, [key]: value }
    }

    // 记录编辑活动以延长会话
    const authStore = useAuthStore()
    authStore.recordConfigActivity()
  }

  // 方法：批量更新配置项
  const updateEntries = (entries: ConfigEntry[]) => {
    if (!isEditing.value) {
      console.warn('未进入编辑模式，无法更新配置')
      return
    }

    configEntries.value = deepClone(entries)
    config.value = entriesToConfig(entries)

    // 记录编辑活动
    const authStore = useAuthStore()
    authStore.recordConfigActivity()
  }

  // 方法：设置验证错误
  const setValidationError = (key: string, errorMsg: string | null) => {
    validationErrors.value[key] = errorMsg
  }

  // 方法：保存配置
  const saveConfig = async (): Promise<ConfigUpdateResponse | false> => {
    if (!canSave.value) {
      if (!hasChanges.value) {
        error.value = '没有需要保存的更改'
      } else if (hasValidationErrors.value) {
        error.value = '存在验证错误，请先修正'
      } else {
        const authStore = useAuthStore()
        if (!authStore.isConfigEditingAuthenticated) {
          error.value = '会话已过期，请重新认证'
        }
      }
      return false
    }

    isSaving.value = true
    error.value = null
    requiresRestart.value = false
    showRestartConfirm.value = false

    try {
      // 构建更新请求（仅包含可编辑且已更改的字段）
      const updates: ConfigUpdateRequest = {}
      const changed = changedEntries.value

      for (const entry of changed) {
        const meta = entry.metadata ?? metadataMap.value[entry.key]
        if (meta?.editable) {
          (updates as any)[entry.key] = entry.value
        }
      }

      // 调用 API 保存
      const response = await configApi.updateConfig(updates)

      // 更新成功，刷新本地状态
      const entries = response.entries || []
      configEntries.value = deepClone(entries)
      originalEntries.value = deepClone(entries)
      config.value = entriesToConfig(entries)

      lastUpdated.value = Date.now()

      // 检查是否需要重启
      const restartScheduled = response.restart_scheduled === true
      const needsRestart = changed.some(e => {
        const meta = e.metadata ?? metadataMap.value[e.key]
        return meta?.requires_restart
      })
      if (needsRestart && !restartScheduled) {
        requiresRestart.value = true
        showRestartConfirm.value = true
      } else {
        requiresRestart.value = false
        showRestartConfirm.value = false
      }

      // 退出编辑模式
      isEditing.value = false
      validationErrors.value = {}

      // 记录活动
      const authStore = useAuthStore()
      authStore.recordConfigActivity()

      return response
    } catch (err: any) {
      const message = err?.body?.message || err?.message || '保存配置失败'
      error.value = `配置保存失败: ${message}`
      throw err
    } finally {
      isSaving.value = false
    }
  }

  // 方法：重置更改（恢复到原始状态）
  const resetChanges = () => {
    if (!isEditing.value) return

    configEntries.value = deepClone(originalEntries.value)
    config.value = entriesToConfig(originalEntries.value)
    validationErrors.value = {}
  }

  // 方法：取消编辑
  const cancelEditing = () => {
    if (isEditing.value) {
      resetChanges()
      isEditing.value = false
    }
  }

  // 方法：关闭重启确认对话框
  const closeRestartConfirm = () => {
    showRestartConfirm.value = false
  }

  // 方法：重置错误
  const resetError = () => {
    error.value = null
  }

  // 兼容旧接口：更新配置（已废弃，建议使用新接口）
  const updateConfig = async (updates: Partial<SystemConfig>) => {
    console.warn('updateConfig 已废弃，请使用 enterEditMode + updateEntry + saveConfig')

    if (!config.value) {
      throw new Error('配置未加载')
    }

    loading.value = true
    error.value = null

    try {
      const mergedConfig = { ...config.value, ...updates }
      await configApi.updateConfig({ custom_headers: mergedConfig.custom_headers })
      config.value = mergedConfig
      lastUpdated.value = Date.now()
    } catch (err) {
      error.value = err instanceof Error ? err.message : '更新配置失败'
      throw err
    } finally {
      loading.value = false
    }
  }

  return {
    // 核心状态
    configEntries,
    originalEntries,
    metadataMap,
    loading,
    loadingMetadata,
    error,
    lastUpdated,

    // 编辑工作流状态
    isEditing,
    isSaving,
    validationErrors,
    showRestartConfirm,
    requiresRestart,

    // 兼容旧接口
    config,

    // 计算属性
    isLoaded,
    hasChanges,
    changedEntries,
    hasValidationErrors,
    canSave,

    // 方法
    loadConfig,
    loadMetadata,
    enterEditMode,
    updateEntry,
    updateEntries,
    setValidationError,
    saveConfig,
    resetChanges,
    cancelEditing,
    closeRestartConfirm,
    resetError,

    // 兼容旧接口（已废弃）
    updateConfig
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

// 认证常量
const DASHBOARD_TOKEN_KEY = 'dashboard_api_key'
const CONFIG_SESSION_KEY = 'config_edit_session'
const DEFAULT_CONFIG_SESSION_DURATION = 15 * 60 * 1000

interface ConfigSession {
  expiresAt: number
  lastActive: number
}

// localStorage 安全操作封装
const safeLocalStorage = {
  getItem(key: string): string | null {
    try {
      if (typeof localStorage === 'undefined') return null
      return localStorage.getItem(key)
    } catch {
      return null
    }
  },
  setItem(key: string, value: string): boolean {
    try {
      if (typeof localStorage === 'undefined') return false
      localStorage.setItem(key, value)
      return true
    } catch {
      return false
    }
  },
  removeItem(key: string): boolean {
    try {
      if (typeof localStorage === 'undefined') return false
      localStorage.removeItem(key)
      return true
    } catch {
      return false
    }
  }
}

// 认证状态存储
export const useAuthStore = defineStore('auth', () => {
  // 主认证状态
  const isAuthenticated = ref(false)
  const token = ref<string | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)
  const initializing = ref(true)

  // 配置编辑会话状态
  const configSession = ref<ConfigSession | null>(null)
  const configSessionDuration = ref(DEFAULT_CONFIG_SESSION_DURATION)
  const configUnlockLoading = ref(false)
  let configAutoLockTimer: number | null = null

  // 计算属性
  const hasToken = computed(() => !!token.value)

  const isConfigEditingAuthenticated = computed(() => {
    if (!configSession.value) return false
    return configSession.value.expiresAt > Date.now()
  })

  const configSessionRemaining = computed(() => {
    if (!configSession.value) return 0
    return Math.max(configSession.value.expiresAt - Date.now(), 0)
  })

  // 配置编辑会话管理
  const persistConfigSession = () => {
    if (!configSession.value) {
      safeLocalStorage.removeItem(CONFIG_SESSION_KEY)
      return
    }

    safeLocalStorage.setItem(
      CONFIG_SESSION_KEY,
      JSON.stringify({
        expiresAt: configSession.value.expiresAt,
        lastActive: configSession.value.lastActive,
        duration: configSessionDuration.value
      })
    )
  }

  const clearAutoLockTimer = () => {
    if (configAutoLockTimer !== null) {
      clearTimeout(configAutoLockTimer)
      configAutoLockTimer = null
    }
  }

  const scheduleAutoLock = () => {
    clearAutoLockTimer()

    if (!configSession.value) return

    const remaining = configSession.value.expiresAt - Date.now()
    if (remaining > 0) {
      configAutoLockTimer = window.setTimeout(() => {
        lockConfigEditing()
      }, remaining)
    } else {
      lockConfigEditing()
    }
  }

  const lockConfigEditing = () => {
    clearAutoLockTimer()
    if (activityThrottleTimer !== null) {
      clearTimeout(activityThrottleTimer)
      activityThrottleTimer = null
    }
    configSession.value = null
    persistConfigSession()
    // 清除本地存储的临时授权，防止未授权请求继续携带旧 key
    configApi.clearToken()
  }

  const startConfigSession = (durationMs: number) => {
    const now = Date.now()
    configSessionDuration.value = durationMs
    configSession.value = {
      expiresAt: now + durationMs,
      lastActive: now
    }
    persistConfigSession()
    scheduleAutoLock()
  }

  const refreshConfigSession = (durationMs?: number) => {
    if (!configSession.value) return

    const now = Date.now()
    const duration = durationMs ?? configSessionDuration.value
    configSessionDuration.value = duration
    configSession.value = {
      expiresAt: now + duration,
      lastActive: now
    }
    persistConfigSession()
    scheduleAutoLock()
  }

  const loadPersistedConfigSession = () => {
    const saved = safeLocalStorage.getItem(CONFIG_SESSION_KEY)
    if (!saved) return

    try {
      const parsed = JSON.parse(saved) as {
        expiresAt: number
        lastActive: number
        duration?: number
      }

      const now = Date.now()
      if (parsed.expiresAt > now) {
        configSessionDuration.value = parsed.duration ?? DEFAULT_CONFIG_SESSION_DURATION
        configSession.value = {
          expiresAt: parsed.expiresAt,
          lastActive: parsed.lastActive
        }
        scheduleAutoLock()
      } else {
        safeLocalStorage.removeItem(CONFIG_SESSION_KEY)
      }
    } catch {
      safeLocalStorage.removeItem(CONFIG_SESSION_KEY)
    }
  }

  const unlockConfigEditing = async (
    apiKey: string,
    durationMs: number = DEFAULT_CONFIG_SESSION_DURATION
  ) => {
    configUnlockLoading.value = true
    error.value = null

    try {
      const result = await configApi.verifyTokenWithKey(apiKey)

      if (!result.valid) {
        const errorMessages = {
          unauthorized: 'API Key 无效或权限不足',
          network: '网络连接失败，请检查网络',
          timeout: '请求超时，请稍后重试',
          server_error: '服务器错误，请稍后重试'
        }
        throw new Error(errorMessages[result.reason || 'unauthorized'])
      }

      // 校验成功后写入 Token，后续受保护接口（保存配置等）才能携带认证
      configApi.setToken(apiKey)
      startConfigSession(durationMs)
    } catch (err) {
      error.value = err instanceof Error ? err.message : '配置编辑认证失败'
      throw err
    } finally {
      configUnlockLoading.value = false
    }
  }

  let activityThrottleTimer: number | null = null
  const ACTIVITY_THROTTLE_INTERVAL = 5000

  const recordConfigActivity = () => {
    if (!isConfigEditingAuthenticated.value) return

    if (activityThrottleTimer !== null) return

    activityThrottleTimer = window.setTimeout(() => {
      activityThrottleTimer = null
    }, ACTIVITY_THROTTLE_INTERVAL)

    refreshConfigSession()
  }

  // 主认证方法
  const login = async (apiKey: string) => {
    loading.value = true
    error.value = null

    try {
      configApi.setToken(apiKey)
      token.value = apiKey

      const result = await configApi.verifyToken()
      if (result.valid) {
        isAuthenticated.value = true
        safeLocalStorage.setItem(DASHBOARD_TOKEN_KEY, apiKey)
      } else {
        throw new Error('API Key 无效')
      }
    } catch (err) {
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
    safeLocalStorage.removeItem(DASHBOARD_TOKEN_KEY)
    if (activityThrottleTimer !== null) {
      clearTimeout(activityThrottleTimer)
      activityThrottleTimer = null
    }
    lockConfigEditing()
  }

  const checkAuth = async () => {
    try {
      const savedToken = safeLocalStorage.getItem(DASHBOARD_TOKEN_KEY)
      if (savedToken) {
        token.value = savedToken
        configApi.setToken(savedToken)
      } else {
        // 确保请求时不带过期/空 token
        configApi.clearToken()
      }

      const result = await configApi.verifyToken()
      // 没有 token 也允许只读访问；有 token 则必须验证通过才视为登录
      isAuthenticated.value = result.valid || !savedToken
      if (!result.valid && savedToken) {
        logout()
      }
      return isAuthenticated.value
    } catch {
      if (safeLocalStorage.getItem(DASHBOARD_TOKEN_KEY)) {
        logout()
      }
      // 兜底允许匿名只读
      isAuthenticated.value = true
      return true
    }
  }

  const initAuth = async () => {
    initializing.value = true
    try {
      await checkAuth()
      loadPersistedConfigSession()
      initializing.value = false
    } catch (err) {
      error.value = err instanceof Error ? err.message : '认证初始化失败'
      initializing.value = false
    }
  }

  return {
    // 主认证状态
    isAuthenticated,
    token,
    loading,
    error,
    initializing,
    // 配置编辑状态
    configSession,
    configSessionRemaining,
    configUnlockLoading,
    // 计算属性
    hasToken,
    isConfigEditingAuthenticated,
    // 主认证方法
    login,
    logout,
    checkAuth,
    initAuth,
    // 配置编辑方法
    unlockConfigEditing,
    lockConfigEditing,
    recordConfigActivity,
    refreshConfigSession
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
