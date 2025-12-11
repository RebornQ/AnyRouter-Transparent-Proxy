<template>
  <div class="space-y-6">
    <!-- 页面标题和刷新按钮 -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-gray-900 dark:text-white">
          系统仪表板
        </h1>
        <p class="mt-1 text-sm text-gray-600 dark:text-gray-400">
          实时监控代理服务状态
        </p>
      </div>
      <div class="flex items-center space-x-1 sm:space-x-2">
        <span
          v-if="lastUpdated"
          class="text-sm text-gray-500 dark:text-gray-400 whitespace-nowrap text-right leading-tight"
        >
          最后更新: {{ formatTime(lastUpdated) }}
        </span>
        <button
          @click="refreshData({ manual: true })"
          :disabled="manualRefreshing"
          aria-label="刷新"
          class="relative h-9 w-9 sm:h-10 sm:w-10 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-all duration-300 flex items-center justify-center disabled:opacity-60 disabled:cursor-not-allowed"
        >
          <!-- 刷新图标 -->
          <svg
            :class="[
              'h-5 w-5 text-white transition-transform duration-500',
              manualRefreshing ? 'animate-spin' : ''
            ]"
            fill="currentColor"
            viewBox="0 0 20 20"
          >
            <path fill-rule="evenodd" d="M4 2a1 1 0 011 1v2.101a7.002 7.002 0 0111.601 2.566 1 1 0 11-1.885.666A5.002 5.002 0 005.999 7H9a1 1 0 010 2H4a1 1 0 01-1-1V3a1 1 0 011-1zm.008 9.057a1 1 0 011.276.61A5.002 5.002 0 0014.001 13H11a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0v-2.101a7.002 7.002 0 01-11.601-2.566 1 1 0 01.61-1.276z" clip-rule="evenodd"/>
          </svg>
        </button>
      </div>
    </div>

    <!-- 错误提示 -->
    <div
      v-if="error"
      class="p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg"
    >
      <div class="flex items-center">
        <svg class="w-5 h-5 text-red-600 dark:text-red-400 mr-3" fill="currentColor" viewBox="0 0 20 20">
          <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"/>
        </svg>
        <div>
          <h3 class="text-sm font-medium text-red-800 dark:text-red-200">
            加载失败
          </h3>
          <p class="text-sm text-red-700 dark:text-red-300 mt-1">
            {{ error }}
          </p>
        </div>
        <button
          @click="refreshData"
          class="ml-auto text-red-600 dark:text-red-400 hover:text-red-800 dark:hover:text-red-200"
        >
          重试
        </button>
      </div>
    </div>

    <!-- 统计卡片网格 -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
      <!-- 请求数量卡片 -->
      <div class="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700">
        <div class="flex items-center">
          <div class="p-3 bg-blue-100 dark:bg-blue-900/30 rounded-lg">
            <svg class="w-6 h-6 text-blue-600 dark:text-blue-400" fill="currentColor" viewBox="0 0 20 20">
              <path d="M8 5a1 1 0 100 2h5.586l-1.293 1.293a1 1 0 001.414 1.414l3-3a1 1 0 000-1.414l-3-3a1 1 0 10-1.414 1.414L13.586 5H8zM12 15a1 1 0 100-2H6.414l1.293-1.293a1 1 0 10-1.414-1.414l-3 3a1 1 0 000 1.414l3 3a1 1 0 001.414-1.414L6.414 15H12z"/>
            </svg>
          </div>
          <div class="ml-4">
            <p class="text-sm font-medium text-gray-600 dark:text-gray-400">
              总请求数
            </p>
            <p class="text-2xl font-semibold text-gray-900 dark:text-white">
              {{ stats?.summary?.total_requests || 0 }}
            </p>
          </div>
        </div>
      </div>

      <!-- 成功率卡片 -->
      <div class="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700">
        <div class="flex items-center">
          <div class="p-3 bg-green-100 dark:bg-green-900/30 rounded-lg">
            <svg class="w-6 h-6 text-green-600 dark:text-green-400" fill="currentColor" viewBox="0 0 20 20">
              <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
            </svg>
          </div>
          <div class="ml-4">
            <p class="text-sm font-medium text-gray-600 dark:text-gray-400">
              成功率
            </p>
            <p class="text-2xl font-semibold text-gray-900 dark:text-white">
              {{ formatPercentage(stats?.summary?.success_rate) }}
            </p>
          </div>
        </div>
      </div>

      <!-- 平均响应时间卡片 -->
      <div class="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700">
        <div class="flex items-center">
          <div class="p-3 bg-yellow-100 dark:bg-yellow-900/30 rounded-lg">
            <svg class="w-6 h-6 text-yellow-600 dark:text-yellow-400" fill="currentColor" viewBox="0 0 20 20">
              <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z" clip-rule="evenodd"/>
            </svg>
          </div>
          <div class="ml-4">
            <p class="text-sm font-medium text-gray-600 dark:text-gray-400">
              平均响应时间
            </p>
            <p class="text-2xl font-semibold text-gray-900 dark:text-white">
              {{ formatResponseTime(stats?.summary?.avg_response_time) }}
            </p>
          </div>
        </div>
      </div>

      <!-- 错误数卡片 -->
      <div class="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700">
        <div class="flex items-center">
          <div class="p-3 bg-red-100 dark:bg-red-900/30 rounded-lg">
            <svg class="w-6 h-6 text-red-600 dark:text-red-400" fill="currentColor" viewBox="0 0 20 20">
              <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"/>
            </svg>
          </div>
          <div class="ml-4">
            <p class="text-sm font-medium text-gray-600 dark:text-gray-400">
              错误数
            </p>
            <p class="text-2xl font-semibold text-gray-900 dark:text-white">
              {{ stats?.summary?.failed_requests || 0 }}
            </p>
          </div>
        </div>
      </div>
    </div>

    <!-- 图表区域 -->
    <div class="grid grid-cols-1 gap-6">
      <!-- 请求趋势图 -->
      <div class="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700">
        <div class="flex items-center justify-between mb-4">
          <h3 class="text-lg font-medium text-gray-900 dark:text-white">
            请求趋势
          </h3>
          <select
            v-model="selectedTimeRange"
            @change="handleTimeRangeChange"
            class="text-sm border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white rounded-md px-3 py-2 focus:outline-none focus:ring-0 focus:border-gray-300 dark:focus:border-gray-600 focus:shadow-none focus-visible:outline-none focus-visible:ring-0 focus-visible:shadow-none"
          >
            <option value="1h">最近 1 小时</option>
            <option value="6h">最近 6 小时</option>
            <option value="24h">最近 24 小时</option>
          </select>
        </div>
        <div class="h-64">
          <canvas ref="requestChart" />
        </div>
      </div>
    </div>

    <!-- 最近请求 -->
    <div class="bg-white dark:bg-gray-800 shadow-sm border border-gray-200 dark:border-gray-700 rounded-lg">
      <div class="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
        <h3 class="text-lg font-medium text-gray-900 dark:text-white">
          最近请求
        </h3>
      </div>
      <div class="p-6">
        <div class="space-y-3">
          <div v-if="!recentRequests?.length" class="text-center py-8 text-gray-500 dark:text-gray-400">
            暂无最近请求
          </div>
          <div
            v-for="request in recentRequests"
            :key="request.request_id"
            :class="['p-3 rounded-lg', getStatusContainerClass(request.status_code, request.status)]"
          >
            <div class="flex items-center justify-between">
              <div class="flex items-center space-x-3">
                <div
                  :class="[
                    'w-2 h-2 rounded-full',
                    getStatusDotClass(request.status_code, request.status)
                  ]"
                />
                <div class="flex items-center space-x-2">
                  <span
                    :class="[
                      'inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold',
                      getMethodClass(request.method)
                    ]"
                  >
                    {{ request.method.toUpperCase() }}
                  </span>
                  <div>
                    <p class="text-sm font-medium text-gray-900 dark:text-white">
                      {{ formatPath(request.path) }}
                    </p>
                    <p class="text-xs text-gray-500 dark:text-gray-400">
                      {{ formatTime(request.timestamp) }}
                    </p>
                  </div>
                </div>
              </div>
              <div class="flex items-center space-x-4">
                <span class="text-sm text-gray-600 dark:text-gray-400">
                  {{ formatResponseTimeFromSeconds(request.response_time) }}
                </span>
                <span
                  :class="[
                    'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium',
                    getStatusBadgeClass(request.status_code, request.status)
                  ]"
                >
                  {{ formatStatusLabel(request.status_code, request.status) }}
                </span>
              </div>
            </div>
            <!-- 错误信息 -->
            <div v-if="isErrorStatus(request.status_code, request.status) && request.error" class="mt-2 pl-5">
              <p class="text-xs text-red-600 dark:text-red-400 font-mono">
                {{ request.error }}
              </p>
              <!-- 错误响应内容（新增） -->
              <div v-if="request.response_content" class="mt-3">
                <pre class="text-xs text-gray-600 dark:text-gray-400 overflow-x-auto whitespace-pre-wrap font-mono">{{ request.response_content }}</pre>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick, watch } from 'vue'
import {
  Chart,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  LineController,
  BarElement,
  BarController,
  Title,
  Tooltip,
  Legend,
  Filler
} from 'chart.js'
import { useRealtimeStats } from '@/composables/useRealtime'
import {
  formatStatusLabel,
  getStatusBadgeClass,
  getStatusContainerClass,
  getStatusDotClass,
  isErrorStatus
} from '@/utils/statusStyle'

// 注册 Chart.js 组件
Chart.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  LineController,
  BarElement,
  BarController,
  Title,
  Tooltip,
  Legend,
  Filler
)

// 响应式状态
const requestChart = ref<HTMLCanvasElement>()
const selectedTimeRange = ref('1h')

// 图表实例
let requestChartInstance: Chart | null = null

// 使用实时统计数据
const { stats, error, lastUpdated, loadStats } = useRealtimeStats({
  interval: 1000,
  autoRefresh: true
})
const manualRefreshing = ref(false)

// 计算属性
const recentRequests = computed(() => {
  // 按时间戳倒序排列（最新的在前）
  return stats.value?.recent_requests
    ?.slice()
    .sort((a, b) => b.timestamp - a.timestamp)
    .slice(0, 10) || []
})

// 格式化函数
const formatTime = (timestamp: number | string): string => {
  // 判断是秒级还是毫秒级时间戳
  // 如果是数字且大于 10000000000（2001-09-09），则认为是毫秒级
  let ms: number
  if (typeof timestamp === 'number') {
    ms = timestamp > 10000000000 ? timestamp : timestamp * 1000
  } else {
    ms = new Date(timestamp).getTime()
  }
  const date = new Date(ms)
  return date.toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}

// 格式化图表 X 轴时间（只显示到分钟）
const formatChartTime = (timestamp: number | string): string => {
  // 判断是秒级还是毫秒级时间戳
  let ms: number
  if (typeof timestamp === 'number') {
    ms = timestamp > 10000000000 ? timestamp : timestamp * 1000
  } else {
    ms = new Date(timestamp).getTime()
  }
  const date = new Date(ms)
  return date.toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit'
  })
}

// 将时间范围字符串转换为秒，默认 1 小时
const parseTimeRangeSeconds = (range?: string): number => {
  if (!range) return 3600
  const match = /^(\d+)([mh])$/i.exec(range)
  if (!match) return 3600
  const value = Number(match[1])
  const unit = match[2].toLowerCase()
  return unit === 'm' ? value * 60 : value * 3600
}

const formatPercentage = (value: number | undefined): string => {
  if (typeof value !== 'number') return '0%'
  return `${(value * 100).toFixed(1)}%`
}

// 格式化响应时间（输入单位：毫秒）
const formatResponseTime = (value: number | undefined): string => {
  if (typeof value !== 'number') return '0ms'
  return `${value.toFixed(0)}ms`
}

// 格式化响应时间（输入单位：秒，转换为毫秒）
const formatResponseTimeFromSeconds = (value: number | undefined): string => {
  if (typeof value !== 'number') return '0ms'
  const ms = value * 1000
  return `${ms.toFixed(0)}ms`
}

// 格式化路径（确保开头有 /）
const formatPath = (path: string): string => {
  return path.startsWith('/') ? path : `/${path}`
}

// 获取 HTTP 方法的样式类
const getMethodClass = (method: string): string => {
  const methodUpper = method.toUpperCase()
  switch (methodUpper) {
    case 'GET':
      return 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400'
    case 'POST':
      return 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400'
    case 'PUT':
      return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400'
    case 'DELETE':
      return 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400'
    case 'PATCH':
      return 'bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-400'
    default:
      return 'bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-400'
  }
}

// 创建请求趋势图
const createRequestChart = () => {
  if (!requestChart.value || !stats.value?.time_series) return

  const ctx = requestChart.value.getContext('2d')
  if (!ctx) return

  const data = stats.value.time_series.requests_per_minute || []
  const rangeSeconds = parseTimeRangeSeconds(selectedTimeRange.value)

  // 计算时间范围（按分钟对齐）
  const now = Date.now()
  const endMinute = Math.ceil(now / 60000) * 60000
  const startMinute = endMinute - rangeSeconds * 1000

  // 将后端数据映射到分钟 -> 数值
  const dataMap = new Map<number, number>()
  data.forEach(item => {
    const ms = item.time > 10000000000 ? item.time : item.time * 1000
    // 对齐到分钟
    const minuteTs = Math.floor(ms / 60000) * 60000
    dataMap.set(minuteTs, item.count)
  })

  // 构建完整的时间轴，填充缺失分钟
  const labels: string[] = []
  const values: (number | null)[] = []
  for (let ts = startMinute; ts <= endMinute; ts += 60000) {
    labels.push(formatChartTime(ts))
    values.push(dataMap.get(ts) ?? null)
  }

  // 如果图表已存在，只更新数据，避免重建导致跳动
  if (requestChartInstance) {
    requestChartInstance.data.labels = labels
    requestChartInstance.data.datasets[0].data = values
    requestChartInstance.update('none') // 使用 'none' 模式禁用动画
    return
  }

  // 首次创建图表
  requestChartInstance = new Chart(ctx, {
    type: 'line',
    data: {
      labels: labels,
      datasets: [{
        label: '请求数',
        data: values,
        borderColor: 'rgb(59, 130, 246)',
        backgroundColor: 'rgba(59, 130, 246, 0.1)',
        tension: 0.4,
        fill: true,
        spanGaps: true // 连接 null 值，让线条延伸到下一分钟
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: false, // 禁用初始动画
      plugins: {
        legend: {
          display: false
        },
        tooltip: {
          mode: 'index',
          intersect: false
        }
      },
      scales: {
        y: {
          beginAtZero: true,
          grid: {
            color: 'rgba(156, 163, 175, 0.1)'
          },
          ticks: {
            stepSize: 1,
            callback: function(value) {
              // 只显示整数刻度
              if (Number.isInteger(value)) {
                return value
              }
            }
          }
        },
        x: {
          grid: {
            display: false
          }
        }
      }
    }
  })
}

// 更新图表
const updateCharts = () => {
  nextTick(() => {
    createRequestChart()
  })
}

// 刷新数据
const refreshData = async (options: { manual?: boolean } = {}) => {
  const isManual = options.manual === true
  if (isManual) {
    manualRefreshing.value = true
  }
  try {
    await loadStats(selectedTimeRange.value)
    updateCharts()
  } catch (error) {
    console.error('刷新数据失败:', error)
  } finally {
    if (isManual) {
      manualRefreshing.value = false
    }
  }
}

// 处理时间范围变化
const handleTimeRangeChange = () => {
  refreshData()
}

// 监听统计数据变化
watch(stats, () => {
  updateCharts()
}, { deep: true })

// 生命周期
onMounted(() => {
  // 初始化数据
  refreshData()

  // 监听窗口大小变化，重新渲染图表
  const handleResize = () => {
    updateCharts()
  }

  window.addEventListener('resize', handleResize)

  onUnmounted(() => {
    window.removeEventListener('resize', handleResize)
    if (requestChartInstance) {
      requestChartInstance.destroy()
    }
  })
})
</script>

<style scoped>
/* 图表容器样式 */
canvas {
  max-height: 100%;
}
</style>
