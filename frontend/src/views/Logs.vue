<template>
  <div class="h-full flex flex-col p-4 lg:p-6 space-y-6">
    <!-- 页面标题和控制栏 -->
    <div class="flex flex-col lg:flex-row justify-between items-start lg:items-center gap-4">
      <div>
        <h1 class="text-2xl font-bold text-gray-900 dark:text-white">日志查看器</h1>
        <p class="text-sm text-gray-600 dark:text-gray-400 mt-1">实时查看系统日志流</p>
      </div>
      <div class="flex flex-col sm:flex-row items-start sm:items-center gap-3 w-full lg:w-auto">
        <!-- 搜索框 -->
        <div class="relative w-full sm:w-64">
          <input
            v-model="searchTerm"
            type="text"
            placeholder="搜索日志..."
            class="w-full pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          />
          <svg
            class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
            />
          </svg>
        </div>

        <!-- 日志级别过滤 -->
        <div class="flex items-center space-x-3 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800">
          <label class="flex items-center cursor-pointer">
            <input
              type="checkbox"
              value="INFO"
              v-model="selectedLevels"
              class="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500 dark:focus:ring-blue-600 dark:ring-offset-gray-800 focus:ring-2 dark:bg-gray-700 dark:border-gray-600"
            />
            <span class="ml-2 text-sm font-medium text-gray-900 dark:text-gray-300">INFO</span>
          </label>
          <label class="flex items-center cursor-pointer">
            <input
              type="checkbox"
              value="WARNING"
              v-model="selectedLevels"
              class="w-4 h-4 text-yellow-600 border-gray-300 rounded focus:ring-yellow-500 dark:focus:ring-yellow-600 dark:ring-offset-gray-800 focus:ring-2 dark:bg-gray-700 dark:border-gray-600"
            />
            <span class="ml-2 text-sm font-medium text-gray-900 dark:text-gray-300">WARNING</span>
          </label>
          <label class="flex items-center cursor-pointer">
            <input
              type="checkbox"
              value="ERROR"
              v-model="selectedLevels"
              class="w-4 h-4 text-red-600 border-gray-300 rounded focus:ring-red-500 dark:focus:ring-red-600 dark:ring-offset-gray-800 focus:ring-2 dark:bg-gray-700 dark:border-gray-600"
            />
            <span class="ml-2 text-sm font-medium text-gray-900 dark:text-gray-300">ERROR</span>
          </label>
        </div>

        <!-- 控制按钮 -->
        <div class="flex items-center space-x-2">
          <button
            @click="toggleAutoScroll"
            :class="[
              'px-3 py-2 text-sm font-medium rounded-lg transition-colors',
              autoScroll
                ? 'bg-blue-600 text-white hover:bg-blue-700'
                : 'bg-gray-200 text-gray-700 dark:bg-gray-700 dark:text-gray-300 hover:bg-gray-300 dark:hover:bg-gray-600'
            ]"
          >
            {{ autoScroll ? '自动滚动' : '暂停滚动' }}
          </button>
          <button
            @click="clearLogs"
            class="px-3 py-2 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 transition-colors"
          >
            清空
          </button>
        </div>
      </div>
    </div>

    <!-- 连接状态（使用 v-show 避免 DOM 创建/销毁导致的闪烁） -->
    <div
      v-show="displayConnectionStatus !== 'connected'"
      :class="[
        'p-4 rounded-lg flex items-center justify-between transition-opacity duration-300',
        displayConnectionStatus === 'connecting'
          ? 'bg-yellow-50 dark:bg-yellow-900/20 text-yellow-800 dark:text-yellow-200'
          : 'bg-red-50 dark:bg-red-900/20 text-red-800 dark:text-red-200'
      ]"
    >
      <div class="flex items-center">
        <div
          :class="[
            'w-3 h-3 rounded-full mr-3 animate-pulse',
            displayConnectionStatus === 'connecting' ? 'bg-yellow-500' : 'bg-red-500'
          ]"
        />
        <span class="text-sm font-medium">
          {{ displayConnectionStatus === 'connecting' ? '连接中...' : '连接断开，正在重试...' }}
        </span>
      </div>
      <button
        @click="reconnect"
        class="px-3 py-1 text-sm font-medium bg-white dark:bg-gray-800 rounded hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
      >
        重连
      </button>
    </div>

    <!-- 日志统计 -->
    <div class="grid grid-cols-2 sm:grid-cols-4 gap-4">
      <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
        <div class="flex items-center justify-between">
          <span class="text-sm font-medium text-gray-600 dark:text-gray-400">总日志数</span>
          <span class="text-lg font-semibold text-gray-900 dark:text-white">
            {{ displayStats.totalValidLogsCount }}
          </span>
        </div>
      </div>
      <div class="bg-blue-50 dark:bg-blue-900/20 rounded-lg shadow p-4">
        <div class="flex items-center justify-between">
          <span class="text-sm font-medium text-blue-600 dark:text-blue-400">INFO</span>
          <span class="text-lg font-semibold text-blue-900 dark:text-blue-100">
            {{ displayStats.totalLevelCounts.INFO }}
          </span>
        </div>
      </div>
      <div class="bg-yellow-50 dark:bg-yellow-900/20 rounded-lg shadow p-4">
        <div class="flex items-center justify-between">
          <span class="text-sm font-medium text-yellow-600 dark:text-yellow-400">WARNING</span>
          <span class="text-lg font-semibold text-yellow-900 dark:text-yellow-100">
            {{ displayStats.totalLevelCounts.WARNING }}
          </span>
        </div>
      </div>
      <div class="bg-red-50 dark:bg-red-900/20 rounded-lg shadow p-4">
        <div class="flex items-center justify-between">
          <span class="text-sm font-medium text-red-600 dark:text-red-400">ERROR</span>
          <span class="text-lg font-semibold text-red-900 dark:text-red-100">
            {{ displayStats.totalLevelCounts.ERROR }}
          </span>
        </div>
      </div>
    </div>

    <!-- 状态提示（常驻显示，消除闪烁） -->
    <div class="text-sm text-gray-600 dark:text-gray-400 text-center">
      {{ statusMessage }}
    </div>

    <!-- 日志列表容器 -->
    <div class="flex-1 bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden flex flex-col">
      <div
        ref="logContainer"
        class="flex-1 relative overflow-y-auto"
        @scroll="handleScroll"
      >
        <div class="relative">
          <!-- 虚拟滚动占位 -->
          <div :style="{ height: `${totalHeight}px` }">
            <!-- 可见日志条目 -->
            <div
              v-for="log in visibleLogs"
              :key="log._key"
              :style="{ position: 'absolute', top: `${log._position}px`, width: '100%' }"
              class="px-4 py-3 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors border-b border-gray-100 dark:border-gray-700"
            >
              <!-- 日志条目头部 -->
              <div class="flex items-start justify-between mb-2">
                <div class="flex items-center space-x-3">
                  <span
                    :class="[
                      'inline-flex items-center px-2 py-1 rounded-full text-xs font-medium',
                      log.level === 'INFO'
                        ? 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200'
                        : log.level === 'WARNING'
                        ? 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200'
                        : 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
                    ]"
                  >
                    {{ log.level }}
                  </span>
                  <span class="text-xs text-gray-500 dark:text-gray-400">
                    {{ log.formatted_time }}
                  </span>
                  <span v-if="log.path" class="text-xs font-mono text-gray-600 dark:text-gray-400">
                    {{ log.path }}
                  </span>
                </div>
                <button
                  @click="toggleLogDetail(log)"
                  class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
                >
                  <svg
                    :class="[
                      'w-4 h-4 transform transition-transform',
                      log._expanded ? 'rotate-180' : ''
                    ]"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
                  </svg>
                </button>
              </div>

              <!-- 日志消息 -->
              <div class="text-sm text-gray-900 dark:text-gray-100 break-all">
                {{ log.message }}
              </div>

              <!-- 详细信息（展开时显示） -->
              <div v-if="log._expanded" class="mt-2 space-y-1">
                <div v-if="log.request_id" class="text-xs text-gray-500 dark:text-gray-400">
                  <span class="font-medium">请求ID:</span> {{ log.request_id }}
                </div>
                <div v-if="log.type" class="text-xs text-gray-500 dark:text-gray-400">
                  <span class="font-medium">类型:</span> {{ log.type }}
                </div>
              </div>
            </div>
          </div>

          <!-- 无日志提示 -->
          <div
            v-if="filteredLogs.length === 0"
            class="flex items-center justify-center h-96 text-gray-500 dark:text-gray-400"
          >
            <div class="text-center">
              <svg
                class="w-16 h-16 mx-auto mb-4 text-gray-300 dark:text-gray-600"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                />
              </svg>
              <p class="text-lg font-medium">暂无日志</p>
              <p class="text-sm">等待系统产生日志...</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { logsApi } from '@/services/api'
import type { LogEntry } from '@/types'

// 防抖函数
const debounce = (func: Function, wait: number) => {
  let timeout: NodeJS.Timeout
  return function executedFunction(...args: any[]) {
    const later = () => {
      clearTimeout(timeout)
      func(...args)
    }
    clearTimeout(timeout)
    timeout = setTimeout(later, wait)
  }
}

// 响应式数据
const logContainer = ref<HTMLDivElement>()
const searchTerm = ref('')
const selectedLevels = ref<string[]>(['INFO', 'WARNING', 'ERROR'])
const autoScroll = ref(true)
const logs = ref<LogEntry[]>([])  // 改回普通 ref
const connectionStatus = ref<'connected' | 'connecting' | 'disconnected'>('connecting')
const eventSource = ref<EventSource | null>(null)
const reconnectTimeout = ref<NodeJS.Timeout>()

// 延迟的连接状态，避免闪烁
const displayConnectionStatus = ref<'connected' | 'connecting' | 'disconnected'>('connecting')
const connectionStatusTimeout = ref<NodeJS.Timeout>()

// 更新显示的连接状态（带延迟）
const updateDisplayConnectionStatus = (status: 'connected' | 'connecting' | 'disconnected', delay: number = 0) => {
  if (connectionStatusTimeout.value) {
    clearTimeout(connectionStatusTimeout.value)
  }

  if (delay === 0) {
    displayConnectionStatus.value = status
  } else {
    connectionStatusTimeout.value = setTimeout(() => {
      displayConnectionStatus.value = status
    }, delay)
  }
}

// 虚拟滚动配置
const ITEM_HEIGHT = 80 // 估算的每个日志条目高度
const BUFFER_SIZE = 10 // 上下缓冲区大小
const MAX_LOGS = 5000 // 最大保留日志数量

// 计算属性 - 使用 shallowRef 和缓存优化
const filteredLogs = computed(() => {
  let result = logs.value

  // 首先排除系统消息（connection 和 heartbeat）
  result = result.filter(log =>
    !log.type || !['connection', 'heartbeat'].includes(log.type)
  )

  // 级别过滤
  if (selectedLevels.value.length > 0) {
    result = result.filter(log => selectedLevels.value.includes(log.level))
  }

  // 搜索过滤
  if (searchTerm.value) {
    const searchLower = searchTerm.value.toLowerCase()
    result = result.filter(log =>
      log.message.toLowerCase().includes(searchLower) ||
      (log.path && log.path.toLowerCase().includes(searchLower))
    )
  }

  return result
})

// 统计计算 - 使用 computed 的自动缓存
const levelCounts = computed(() => {
  return filteredLogs.value.reduce(
    (acc, log) => {
      acc[log.level] = (acc[log.level] || 0) + 1
      return acc
    },
    { INFO: 0, WARNING: 0, ERROR: 0 }
  )
})

// 防抖的统计显示
const displayStats = ref({
  totalValidLogsCount: 0,
  totalLevelCounts: { INFO: 0, WARNING: 0, ERROR: 0 },
  filteredLogsCount: 0
})

// 更新统计显示（防抖）
const updateDisplayStats = debounce(() => {
  displayStats.value.totalValidLogsCount = logs.value.filter(log =>
    !log.type || !['connection', 'heartbeat'].includes(log.type)
  ).length

  displayStats.value.totalLevelCounts = logs.value.reduce(
    (acc, log) => {
      if (log.level && ['INFO', 'WARNING', 'ERROR'].includes(log.level)) {
        acc[log.level] = (acc[log.level] || 0) + 1
      }
      return acc
    },
    { INFO: 0, WARNING: 0, ERROR: 0 }
  )

  // 计算过滤后的数量
  let filtered = logs.value.filter(log =>
    !log.type || !['connection', 'heartbeat'].includes(log.type)
  )

  if (selectedLevels.value.length > 0) {
    filtered = filtered.filter(log => selectedLevels.value.includes(log.level))
  }

  if (searchTerm.value) {
    const searchLower = searchTerm.value.toLowerCase()
    filtered = filtered.filter(log =>
      log.message.toLowerCase().includes(searchLower) ||
      (log.path && log.path.toLowerCase().includes(searchLower))
    )
  }

  displayStats.value.filteredLogsCount = filtered.length
}, 200)

// 状态消息计算（常驻显示，消除闪烁）
const statusMessage = computed(() => {
  if (displayStats.value.filteredLogsCount === displayStats.value.totalValidLogsCount) {
    if (displayStats.value.totalValidLogsCount === 0) {
      return `暂无日志记录`
    } else {
      return `显示全部 ${displayStats.value.totalValidLogsCount} 条日志`
    }
  } else {
    return `显示 ${displayStats.value.filteredLogsCount} / ${displayStats.value.totalValidLogsCount} 条日志（已应用过滤条件）`
  }
})

// 监听数据变化，更新显示
watch([logs, selectedLevels, searchTerm], updateDisplayStats, { deep: true })

// 虚拟滚动计算
const scrollTop = ref(0)
const containerHeight = ref(0) // 初始值为 0,会在 onMounted 中更新

const totalHeight = computed(() => filteredLogs.value.length * ITEM_HEIGHT)

const visibleRange = computed(() => {
  const startIndex = Math.max(0, Math.floor(scrollTop.value / ITEM_HEIGHT) - BUFFER_SIZE)
  const endIndex = Math.min(
    filteredLogs.value.length,
    startIndex + Math.ceil(containerHeight.value / ITEM_HEIGHT) + BUFFER_SIZE * 2
  )
  return { startIndex, endIndex }
})

// 生成稳定的唯一 key
const getLogKey = (log: LogEntry) => {
  return `${log.timestamp}_${log.level}_${log.request_id || 'no-id'}_${log.type || 'no-type'}`
}

const visibleLogs = computed(() => {
  return filteredLogs.value
    .slice(visibleRange.value.startIndex, visibleRange.value.endIndex)
    .map((log, index) => ({
      ...log,
      _position: visibleRange.value.startIndex * ITEM_HEIGHT + index * ITEM_HEIGHT,
      _key: getLogKey(log)
    }))
})

// 方法
const handleScroll = () => {
  if (logContainer.value) {
    scrollTop.value = logContainer.value.scrollTop
    containerHeight.value = logContainer.value.clientHeight

    // 自动滚动检测
    const { scrollTop, scrollHeight, clientHeight } = logContainer.value
    const isAtBottom = scrollHeight - scrollTop <= clientHeight + 100
    autoScroll.value = isAtBottom
  }
}

const toggleLogDetail = (log: LogEntry) => {
  log._expanded = !log._expanded
}

const clearLogs = () => {
  logs.value = []
}

const reconnect = () => {
  disconnectSSE()
  connectSSE()
}

const connectSSE = () => {
  connectionStatus.value = 'connecting'
  updateDisplayConnectionStatus('connecting')

  try {
    eventSource.value = logsApi.createLogStream({
      level: selectedLevels.value as LogEntry['level'][],
      search: searchTerm.value
    })

    eventSource.value.onopen = () => {
      connectionStatus.value = 'connected'
      updateDisplayConnectionStatus('connected')
      console.log('[Logs] SSE 连接已建立')
    }

    eventSource.value.onmessage = (event) => {
      try {
        const logEntry: LogEntry = JSON.parse(event.data)

        // 添加展开状态标记
        logEntry._expanded = false

        // 检查是否已存在相同的日志（避免重复）
        const exists = logs.value.some(log =>
          log.timestamp === logEntry.timestamp &&
          log.message === logEntry.message
        )

        // 批量更新日志列表，减少响应式更新次数
        if (!exists) {
          // 创建新数组，触发一次性更新
          const newLogs = [logEntry, ...logs.value]
          if (newLogs.length > MAX_LOGS) {
            logs.value = newLogs.slice(0, MAX_LOGS)
          } else {
            logs.value = newLogs
          }
        }

        // 自动滚动到底部
        if (autoScroll.value && logContainer.value) {
          nextTick(() => {
            logContainer.value!.scrollTop = 0
          })
        }
      } catch (error) {
        console.error('[Logs] 解析日志数据失败:', error)
      }
    }

    eventSource.value.onerror = () => {
      connectionStatus.value = 'disconnected'
      // 延迟显示断开状态，避免短暂的网络波动导致闪烁
      updateDisplayConnectionStatus('disconnected', 1000) // 1秒后才显示断开状态
      console.error('[Logs] SSE 连接错误')

      // 自动重连
      if (reconnectTimeout.value) {
        clearTimeout(reconnectTimeout.value)
      }
      reconnectTimeout.value = setTimeout(() => {
        if (connectionStatus.value === 'disconnected') {
          connectSSE()
        }
      }, 5000) // 5秒后重试
    }
  } catch (error) {
    connectionStatus.value = 'disconnected'
    updateDisplayConnectionStatus('disconnected', 1000) // 1秒后才显示断开状态
    console.error('[Logs] 创建 SSE 连接失败:', error)
  }
}

const disconnectSSE = () => {
  if (eventSource.value) {
    eventSource.value.close()
    eventSource.value = null
  }
  if (reconnectTimeout.value) {
    clearTimeout(reconnectTimeout.value)
    reconnectTimeout.value = undefined
  }
  if (connectionStatusTimeout.value) {
    clearTimeout(connectionStatusTimeout.value)
    connectionStatusTimeout.value = undefined
  }
}

const toggleAutoScroll = () => {
  autoScroll.value = !autoScroll.value
}

// 注意: 不需要在过滤条件变化时重新连接 SSE
// 因为前端已经有了完整的过滤逻辑 (filteredLogs computed)
// 移除了重新连接的逻辑,避免连接状态闪烁

// 更新容器高度
const updateContainerHeight = () => {
  if (logContainer.value) {
    containerHeight.value = logContainer.value.clientHeight
  }
}

// 窗口大小变化监听
const handleResize = () => {
  updateContainerHeight()
}

// 生命周期
onMounted(() => {
  // 初始化统计数据
  updateDisplayStats()
  // 初始化容器高度
  nextTick(() => {
    updateContainerHeight()
  })
  // 监听窗口大小变化
  window.addEventListener('resize', handleResize)
  // 连接 SSE
  connectSSE()
})

onUnmounted(() => {
  disconnectSSE()
  window.removeEventListener('resize', handleResize)
})
</script>