<template>
  <div class="space-y-6">
    <!-- 页面标题 -->
    <div class="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
      <div>
        <h1 class="text-2xl font-bold text-gray-900 dark:text-white">监控中心</h1>
        <p class="text-sm text-gray-600 dark:text-gray-400 mt-1">实时监控系统运行状态和性能指标</p>
      </div>
      <div class="flex items-center space-x-2">
        <select
          v-model="selectedTimeRange"
          @change="refreshData"
          class="px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-0 focus:border-gray-300 dark:focus:border-gray-600 focus:shadow-none focus-visible:outline-none focus-visible:ring-0 focus-visible:shadow-none"
        >
          <option value="5m">最近 5 分钟</option>
          <option value="15m">最近 15 分钟</option>
          <option value="1h">最近 1 小时</option>
          <option value="6h">最近 6 小时</option>
          <option value="24h">最近 24 小时</option>
        </select>
        <button
          @click="refreshData({ manual: true })"
          :disabled="manualRefreshing"
          aria-label="刷新"
          class="relative h-10 w-10 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-all duration-300 flex items-center justify-center disabled:opacity-60 disabled:cursor-not-allowed"
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

    <!-- 实时状态概览 -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
        <div class="flex items-center">
          <div class="p-2 bg-blue-100 dark:bg-blue-900 rounded-lg">
            <svg class="w-6 h-6 text-blue-600 dark:text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
          </div>
          <div class="ml-4">
            <p class="text-sm font-medium text-gray-600 dark:text-gray-400">活跃请求</p>
            <p class="text-2xl font-semibold text-gray-900 dark:text-white">
              {{ stats?.summary.total_requests || 0 }}
            </p>
          </div>
        </div>
      </div>

      <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
        <div class="flex items-center">
          <div class="p-2 bg-green-100 dark:bg-green-900 rounded-lg">
            <svg class="w-6 h-6 text-green-600 dark:text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <div class="ml-4">
            <p class="text-sm font-medium text-gray-600 dark:text-gray-400">成功率</p>
            <p class="text-2xl font-semibold text-gray-900 dark:text-white">
              {{ ((stats?.summary.success_rate || 0) * 100).toFixed(1) }}%
            </p>
          </div>
        </div>
      </div>

      <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
        <div class="flex items-center">
          <div class="p-2 bg-yellow-100 dark:bg-yellow-900 rounded-lg">
            <svg class="w-6 h-6 text-yellow-600 dark:text-yellow-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <div class="ml-4">
            <p class="text-sm font-medium text-gray-600 dark:text-gray-400">平均响应时间</p>
            <p class="text-2xl font-semibold text-gray-900 dark:text-white">
              {{ (stats?.summary.avg_response_time || 0).toFixed(0) }}ms
            </p>
          </div>
        </div>
      </div>

      <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
        <div class="flex items-center">
          <div class="p-2 bg-red-100 dark:bg-red-900 rounded-lg">
            <svg class="w-6 h-6 text-red-600 dark:text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <div class="ml-4">
            <p class="text-sm font-medium text-gray-600 dark:text-gray-400">错误数</p>
            <p class="text-2xl font-semibold text-gray-900 dark:text-white">
              {{ stats?.summary.failed_requests || 0 }}
            </p>
          </div>
        </div>
      </div>
    </div>

    <!-- 性能图表 -->
    <div class="grid grid-cols-1 gap-6">
      <!-- 请求量趋势 -->
      <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
        <h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-4">请求量趋势</h3>
        <div class="h-64">
          <Line
            v-if="requestChartData"
            :data="requestChartData"
            :options="chartOptions"
          />
          <div v-else class="h-full flex items-center justify-center text-gray-500 dark:text-gray-400">
            暂无数据
          </div>
        </div>
      </div>
    </div>

    <!-- 最近请求和错误信息 -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <!-- 最近请求 -->
      <div class="bg-white dark:bg-gray-800 rounded-lg shadow">
        <div class="p-6 border-b border-gray-200 dark:border-gray-700">
          <h3 class="text-lg font-semibold text-gray-900 dark:text-white">最近请求</h3>
        </div>
        <div class="overflow-hidden">
          <div class="max-h-96 overflow-y-auto p-6">
            <div class="space-y-3">
              <div v-if="!sortedRecentRequests.length" class="text-center py-8 text-gray-500 dark:text-gray-400">
                暂无最近请求
              </div>
              <div
                v-for="request in sortedRecentRequests"
                :key="request.request_id"
                :class="['p-3 rounded-lg', getStatusContainerClass(request.status_code, request.status)]"
              >
                <div class="flex items-center justify-between">
                  <div class="flex items-center space-x-3 min-w-0">
                    <div
                      :class="[
                        'w-2 h-2 rounded-full',
                        getStatusDotClass(request.status_code, request.status)
                      ]"
                    />
                    <div class="flex items-center space-x-2 min-w-0">
                      <span
                        :class="[
                          'inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold',
                          getMethodClass(request.method)
                        ]"
                      >
                        {{ request.method.toUpperCase() }}
                      </span>
                      <div class="min-w-0">
                        <p class="text-sm font-medium text-gray-900 dark:text-white break-all" :title="formatPath(request.path)">
                          {{ formatPath(request.path) }}
                        </p>
                        <p class="text-xs text-gray-500 dark:text-gray-400 whitespace-nowrap">
                          {{ formatTime(request.timestamp) }}
                        </p>
                      </div>
                    </div>
                  </div>
                  <div class="flex items-center space-x-4">
                    <span class="text-sm text-gray-600 dark:text-gray-400">
                      {{ (request.response_time * 1000).toFixed(0) }}ms
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

      <!-- 错误请求 -->
      <div class="bg-white dark:bg-gray-800 rounded-lg shadow">
        <div class="p-6 border-b border-gray-200 dark:border-gray-700">
          <h3 class="text-lg font-semibold text-gray-900 dark:text-white">错误请求</h3>
        </div>
        <div class="overflow-hidden">
          <div class="max-h-96 overflow-y-auto p-6">
            <div class="space-y-3">
              <div v-if="!errorRequests.length" class="text-center py-8 text-gray-500 dark:text-gray-400">
                暂无错误请求
              </div>
              <div
                v-for="request in errorRequests"
                :key="request.request_id"
                :class="['p-3 rounded-lg', getStatusContainerClass(request.status_code, request.status)]"
              >
                <div class="flex items-center justify-between">
                  <div class="flex items-center space-x-3 min-w-0">
                    <div
                      :class="[
                        'w-2 h-2 rounded-full',
                        getStatusDotClass(request.status_code, request.status)
                      ]"
                    />
                    <div class="flex items-center space-x-2 min-w-0">
                      <span
                        :class="[
                          'inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold',
                          getMethodClass(request.method)
                        ]"
                      >
                        {{ request.method.toUpperCase() }}
                      </span>
                      <div class="min-w-0">
                        <p class="text-sm font-medium text-gray-900 dark:text-white break-all" :title="formatPath(request.path)">
                          {{ formatPath(request.path) }}
                        </p>
                        <p class="text-xs text-gray-500 dark:text-gray-400 whitespace-nowrap">
                          {{ formatTime(request.timestamp) }}
                        </p>
                      </div>
                    </div>
                  </div>
                  <div class="flex items-center space-x-4">
                    <span class="text-sm text-gray-600 dark:text-gray-400">
                      {{ (request.response_time * 1000).toFixed(0) }}ms
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
                <div v-if="request.error" class="mt-2 pl-5">
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
    </div>

  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { Line } from 'vue-chartjs'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  type ChartOptions
} from 'chart.js'
import { statsApi } from '@/services/api'
import {
  formatStatusLabel,
  getStatusBadgeClass,
  getStatusContainerClass,
  getStatusDotClass,
  isErrorStatus
} from '@/utils/statusStyle'

// 注册 Chart.js 组件
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
)

// 响应式数据
const isLoading = ref(false)
const manualRefreshing = ref(false)
const selectedTimeRange = ref('15m')
const stats = ref<SystemStats | null>(null)
const refreshInterval = ref<NodeJS.Timeout>()

// 图表配置
const chartOptions: ChartOptions<'line'> = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      display: false
    },
    tooltip: {
      mode: 'index',
      intersect: false,
      backgroundColor: 'rgba(0, 0, 0, 0.8)',
      titleColor: '#fff',
      bodyColor: '#fff',
      borderColor: '#ddd',
      borderWidth: 1
    }
  },
  scales: {
    x: {
      grid: {
        color: 'rgba(0, 0, 0, 0.05)'
      },
      ticks: {
        color: '#666'
      }
    },
    y: {
      beginAtZero: true,
      grid: {
        color: 'rgba(0, 0, 0, 0.05)'
      },
      ticks: {
        color: '#666',
        stepSize: 1,
        callback: function(value) {
          // 只显示整数刻度
          if (Number.isInteger(value)) {
            return value
          }
        }
      }
    }
  },
  interaction: {
    mode: 'nearest',
    axis: 'x',
    intersect: false
  }
}

// 最近请求（按时间倒序）
const sortedRecentRequests = computed(() => {
  if (!stats.value?.recent_requests) return []
  // 按时间戳倒序排列（最新的在前）
  return [...stats.value.recent_requests].sort((a, b) => b.timestamp - a.timestamp)
})

// 错误请求（从最近请求中过滤出错误请求）
const errorRequests = computed(() => {
  if (!stats.value?.recent_requests) return []
  // 过滤出状态为 'error' 的请求，并按时间戳倒序排列
  return [...stats.value.recent_requests]
    .filter(request => isErrorStatus(request.status_code, request.status))
    .sort((a, b) => b.timestamp - a.timestamp)
})

// 请求量趋势图表数据
const requestChartData = computed(() => {
  if (!stats.value?.time_series?.requests_per_minute) return null

  const data = stats.value.time_series.requests_per_minute
  const now = Date.now()

  const rangeSeconds = (() => {
    const match = /^(\d+)([mh])$/i.exec(selectedTimeRange.value)
    if (!match) return 3600
    const num = Number(match[1])
    const unit = match[2].toLowerCase()
    return unit === 'm' ? num * 60 : num * 3600
  })()

  const endMinute = Math.ceil(now / 60000) * 60000
  const startMinute = endMinute - rangeSeconds * 1000

  const dataMap = new Map<number, number>()
  data.forEach(item => {
    const ms = item.time > 10000000000 ? item.time : item.time * 1000
    const minuteTs = Math.floor(ms / 60000) * 60000
    dataMap.set(minuteTs, item.count)
  })

  const labels: string[] = []
  const values: (number | null)[] = []

  for (let ts = startMinute; ts <= endMinute; ts += 60000) {
    labels.push(new Date(ts).toLocaleTimeString('zh-CN', {
      hour: '2-digit',
      minute: '2-digit'
    }))
    values.push(dataMap.get(ts) ?? null)
  }

  return {
    labels,
    datasets: [
      {
        label: '请求量',
        data: values,
        borderColor: 'rgb(59, 130, 246)',
        backgroundColor: 'rgba(59, 130, 246, 0.1)',
        fill: true,
        tension: 0.3,
        pointRadius: 2,
        pointHoverRadius: 4,
        spanGaps: true // 连接 null 值，让线条覆盖完整时间轴
      }
    ]
  }
})


// 格式化时间
const formatTime = (timestamp: number): string => {
  return new Date(timestamp * 1000).toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}

// 格式化字节数
const formatBytes = (bytes: number): string => {
  if (bytes === 0) return '0 B'

  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))

  return `${(bytes / Math.pow(k, i)).toFixed(i === 0 ? 0 : 1)} ${sizes[i]}`
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

// 刷新数据
const refreshData = async (options: { manual?: boolean } = {}) => {
  if (isLoading.value) return

  const isManual = options.manual === true
  isLoading.value = true
  if (isManual) {
    manualRefreshing.value = true
  }
  try {
    // 加载统计数据
    const statsData = await statsApi.getStats(selectedTimeRange.value)
    stats.value = statsData
  } catch (error) {
    console.error('刷新监控数据失败:', error)
    // 这里可以添加错误提示
  } finally {
    isLoading.value = false
    if (isManual) {
      manualRefreshing.value = false
    }
  }
}

// 组件挂载时加载数据
onMounted(() => {
  refreshData()

  // 设置自动刷新（每30秒）
  refreshInterval.value = setInterval(refreshData, 30000)
})

// 组件卸载时清理定时器
onUnmounted(() => {
  if (refreshInterval.value) {
    clearInterval(refreshInterval.value)
  }
})
</script>
