<template>
  <div class="min-h-screen bg-gray-50 dark:bg-gray-900 transition-colors duration-200">
    <!-- 移动端遮罩 -->
    <div
      v-if="sidebarOpen"
      class="fixed inset-0 z-40 bg-black/30 backdrop-blur-sm lg:hidden"
      @click="closeSidebar"
    />

    <!-- 桌面端布局容器 -->
    <div class="flex h-screen">
      <!-- 侧边栏 -->
      <aside
        :class="[
          'fixed inset-y-0 left-0 z-50 w-64 transform transition-transform duration-300 ease-in-out lg:relative lg:translate-x-0 lg:inset-0',
          {
            'translate-x-0': sidebarOpen,
            '-translate-x-full': !sidebarOpen
          }
        ]"
      >
      <div class="flex h-full flex-col bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700">
        <!-- Logo 区域 -->
        <div class="flex h-16 items-center justify-between px-6 border-b border-gray-200 dark:border-gray-700">
          <div class="flex items-center">
            <div class="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
              <svg class="w-5 h-5 text-white" fill="currentColor" viewBox="0 0 20 20">
                <path d="M10 2a8 8 0 100 16 8 8 0 000-16zM8 12a2 2 0 110-4 2 2 0 010 4z"/>
              </svg>
            </div>
            <span class="ml-3 text-xl font-semibold text-gray-900 dark:text-white">
              透明代理服务
            </span>
          </div>
          <button
            class="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors cursor-not-allowed opacity-70"
            title="主题切换暂不可用"
            aria-disabled="true"
          >
            <svg class="w-5 h-5 text-gray-500 dark:text-gray-300" fill="currentColor" viewBox="0 0 20 20">
              <path fill-rule="evenodd" d="M3 5a2 2 0 012-2h10a2 2 0 012 2v8a2 2 0 01-2 2h-2.22l.123.489.804.804A1 1 0 0113 18H7a1 1 0 01-.707-1.707l.804-.804L7.22 15H5a2 2 0 01-2-2V5zm5.771 7H5V5h10v7H8.771z" clip-rule="evenodd"/>
            </svg>
          </button>
        </div>

        <!-- 当前代理服务 -->
        <div class="px-4 pt-4">
          <button
            type="button"
            class="proxy-copy-btn w-full text-left px-3 py-2 rounded-lg bg-orange-50 text-orange-800 dark:bg-orange-900/40 dark:text-orange-100 border border-orange-200/70 dark:border-orange-700/60 text-xs leading-relaxed break-all transition-colors hover:bg-orange-100 dark:hover:bg-orange-900/60 outline-none ring-0 shadow-none focus:outline-none focus:ring-0 focus:ring-offset-0 focus:shadow-none focus-visible:outline-none focus-visible:ring-0 focus-visible:ring-offset-0 focus-visible:shadow-none active:outline-none active:ring-0 active:shadow-none"
            @click="copyProxyUrl"
            @keydown.enter.prevent="copyProxyUrl"
            @keydown.space.prevent="copyProxyUrl"
            title="点击复制代理服务地址"
          >
            <div class="text-[11px] font-semibold uppercase tracking-wide text-orange-700 dark:text-orange-200">
              代理服务地址
            </div>
            <div class="mt-1 relative min-w-0">
              <span class="flex-1 break-all whitespace-normal block">{{ proxyBaseUrl }}</span>
              <span
                v-show="copied"
                class="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold bg-orange-200 text-orange-800 dark:bg-orange-800 dark:text-orange-50 shrink-0 absolute"
                style="right: 0.1px; bottom: 0.1px;"
                aria-live="polite"
              >
                已复制
              </span>
            </div>
          </button>
        </div>

        <!-- 导航菜单 -->
        <nav class="flex-1 px-4 py-6 space-y-2 overflow-y-auto">
          <RouterLink
            v-for="item in menuItems"
            :key="item.path"
            :to="item.path"
            :class="[
              'flex items-center px-3 py-2 text-sm font-medium rounded-lg transition-colors group',
              currentPath === item.path
                ? 'bg-blue-50 text-blue-700 dark:bg-blue-900/20 dark:text-blue-300'
                : 'text-gray-700 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-700'
            ]"
            @click="closeSidebar"
          >
            <component
              :is="item.icon"
              class="mr-3 h-5 w-5 flex-shrink-0"
              :class="{
                'text-blue-500': currentPath === item.path,
                'text-gray-400 group-hover:text-gray-500 dark:group-hover:text-gray-300': currentPath !== item.path
              }"
            />
            {{ item.name }}
            <span
              v-if="item.badge"
              class="ml-auto inline-flex items-center justify-center px-2 py-1 text-xs font-bold leading-none text-white bg-red-500 rounded-full"
            >
              {{ item.badge }}
            </span>
          </RouterLink>
        </nav>

        <!-- 底部状态 -->
        <div class="p-4 border-t border-gray-200 dark:border-gray-700">
          <div class="flex items-center">
            <div
              :class="[
                'w-2 h-2 rounded-full mr-2',
                displayIsOnline ? 'bg-green-500' : 'bg-red-500'
              ]"
            />
            <span class="text-xs text-gray-600 dark:text-gray-400">
              {{ displayIsOnline ? '在线' : '离线' }}
            </span>
          </div>
        </div>
      </div>
    </aside>

    <!-- 主内容区域 -->
    <div class="flex-1 flex flex-col">
      <!-- 顶部导航栏 -->
      <header class="sticky top-0 z-30 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
        <div class="flex h-16 items-center justify-between px-4 sm:px-6 lg:px-8">
          <!-- 移动端菜单按钮 -->
          <button
            @click="toggleSidebar"
            class="lg:hidden p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
          >
            <svg class="w-6 h-6 text-gray-600 dark:text-gray-300" fill="currentColor" viewBox="0 0 20 20">
              <path fill-rule="evenodd" d="M3 5a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zM3 10a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zM3 15a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1z" clip-rule="evenodd"/>
            </svg>
          </button>

          <!-- 页面标题 -->
          <h1 class="text-lg font-semibold text-gray-900 dark:text-white">
            {{ currentTitle }}
          </h1>

          <!-- 右侧操作区 -->
          <div class="flex items-center space-x-4">
            <!-- 连接状态指示器 -->
            <div class="hidden sm:flex items-center">
              <div
                :class="[
                  'w-2 h-2 rounded-full mr-2',
                  displayIsOnline ? 'bg-green-500' : 'bg-red-500'
                ]"
              />
              <span class="text-sm text-gray-600 dark:text-gray-400">
                {{ displayIsOnline ? '系统正常' : '连接异常' }}
              </span>
            </div>
          </div>
        </div>
      </header>

      <!-- 页面内容 -->
      <main class="flex-1 px-4 sm:px-6 lg:px-6 pt-6 pb-4 overflow-y-auto">
        <router-view />
      </main>
    </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { RouterLink, useRoute } from 'vue-router'

const route = useRoute()
const sidebarOpen = ref(false)
const isOnline = ref(true)

// 延迟的网络状态显示，避免闪烁
const displayIsOnline = ref(true)
const onlineStatusTimeout = ref<NodeJS.Timeout>()

// 更新显示的网络状态（带延迟）
const updateDisplayOnlineStatus = (online: boolean, delay: number = 0) => {
  if (onlineStatusTimeout.value) {
    clearTimeout(onlineStatusTimeout.value)
  }

  if (delay === 0) {
    displayIsOnline.value = online
  } else {
    onlineStatusTimeout.value = setTimeout(() => {
      displayIsOnline.value = online
    }, delay)
  }
}

// 计算属性
const currentPath = computed(() => route.path)
const proxyBaseUrl = computed(() => {
  if (typeof window === 'undefined') return '本机服务'
  return window.location.origin
})
const copied = ref(false)

const copyProxyUrl = async () => {
  const text = proxyBaseUrl.value
  try {
    if (navigator?.clipboard?.writeText) {
      await navigator.clipboard.writeText(text)
    } else {
      const textarea = document.createElement('textarea')
      textarea.value = text
      textarea.setAttribute('readonly', '')
      textarea.style.position = 'absolute'
      textarea.style.left = '-9999px'
      document.body.appendChild(textarea)
      textarea.select()
      document.execCommand('copy')
      document.body.removeChild(textarea)
    }
    copied.value = true
    setTimeout(() => {
      copied.value = false
    }, 1200)
  } catch (err) {
    console.error('[BaseLayout] 复制失败:', err)
  }
}

// 菜单项配置
const menuItems = [
  {
    name: '仪表板',
    path: '/dashboard',
    icon: 'svg',
    badge: null
  },
  {
    name: '配置管理',
    path: '/config',
    icon: 'svg',
    badge: null
  },
  {
    name: '监控中心',
    path: '/monitoring',
    icon: 'svg',
    badge: null
  },
  {
    name: '日志查看器',
    path: '/logs',
    icon: 'svg',
    badge: null
  }
]

// 图标组件映射
const iconComponents = {
  // 仪表板图标
  dashboard: {
    template: `
      <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
        <path d="M10.707 2.293a1 1 0 00-1.414 0l-7 7a1 1 0 001.414 1.414L4 10.414V17a1 1 0 001 1h2a1 1 0 001-1v-2a1 1 0 011-1h2a1 1 0 011 1v2a1 1 0 001 1h2a1 1 0 001-1v-6.586l.293.293a1 1 0 001.414-1.414l-7-7z"/>
      </svg>
    `
  },
  // 配置管理图标
  config: {
    template: `
      <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
        <path fill-rule="evenodd" d="M11.49 3.17c-.38-1.56-2.6-1.56-2.98 0a1.532 1.532 0 01-2.286.948c-1.372-.836-2.942.734-2.106 2.106.54.886.061 2.042-.947 2.287-1.561.379-1.561 2.6 0 2.978a1.532 1.532 0 01.947 2.287c-.836 1.372.734 2.942 2.106 2.106a1.532 1.532 0 012.287.947c.379 1.561 2.6 1.561 2.978 0a1.533 1.533 0 012.287-.947c1.372.836 2.942-.734 2.106-2.106a1.533 1.533 0 01.947-2.287c1.561-.379 1.561-2.6 0-2.978a1.532 1.532 0 01-.947-2.287c.836-1.372-.734-2.942-2.106-2.106a1.532 1.532 0 01-2.287-.947zM10 13a3 3 0 100-6 3 3 0 000 6z" clip-rule="evenodd"/>
      </svg>
    `
  },
  // 监控中心图标
  monitoring: {
    template: `
      <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
        <path d="M2 11a1 1 0 011-1h2a1 1 0 011 1v5a1 1 0 01-1 1H3a1 1 0 01-1-1v-5zM8 7a1 1 0 011-1h2a1 1 0 011 1v9a1 1 0 01-1 1H9a1 1 0 01-1-1V7zM14 4a1 1 0 011-1h2a1 1 0 011 1v12a1 1 0 01-1 1h-2a1 1 0 01-1-1V4z"/>
      </svg>
    `
  },
  // 日志查看器图标
  logs: {
    template: `
      <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
        <path fill-rule="evenodd" d="M4 4a2 2 0 012-2h8a2 2 0 012 2v12a2 2 0 01-2 2H6a2 2 0 01-2-2V4zm2 0h8v12H6V4zm2 2a1 1 0 011-1h2a1 1 0 110 2H9a1 1 0 01-1-1zm1 3a1 1 0 100 2h2a1 1 0 100-2H9zm-1 4a1 1 0 011-1h2a1 1 0 110 2H9a1 1 0 01-1-1z" clip-rule="evenodd"/>
      </svg>
    `
  }
}

// 动态设置菜单项图标
menuItems.forEach(item => {
  const iconKey = item.path.split('/').pop() as keyof typeof iconComponents
  item.icon = iconComponents[iconKey] || iconComponents.dashboard
})

// 当前页面标题
const currentTitle = computed(() => {
  const item = menuItems.find(item => item.path === currentPath.value)
  return item?.name || '透明代理服务管理面板'
})

// 侧边栏控制
const toggleSidebar = () => {
  sidebarOpen.value = !sidebarOpen.value
}

const closeSidebar = () => {
  sidebarOpen.value = false
}

// 网络状态监听
const updateOnlineStatus = () => {
  const online = navigator.onLine
  isOnline.value = online

  // 延迟显示离线状态，避免短暂的网络波动
  if (online) {
    updateDisplayOnlineStatus(true, 0) // 立即显示在线
  } else {
    updateDisplayOnlineStatus(false, 1000) // 1秒后才显示离线
  }
}

// 生命周期
onMounted(() => {
  updateOnlineStatus()
  window.addEventListener('online', updateOnlineStatus)
  window.addEventListener('offline', updateOnlineStatus)

  // 响应式处理：移动端自动关闭侧边栏
  if (window.innerWidth >= 1024) {
    sidebarOpen.value = false
  }
})

onUnmounted(() => {
  window.removeEventListener('online', updateOnlineStatus)
  window.removeEventListener('offline', updateOnlineStatus)

  // 清理超时
  if (onlineStatusTimeout.value) {
    clearTimeout(onlineStatusTimeout.value)
    onlineStatusTimeout.value = undefined
  }
})
</script>

<style scoped>
/* 自定义滚动条样式 */
.overflow-y-auto::-webkit-scrollbar {
  width: 4px;
}

.overflow-y-auto::-webkit-scrollbar-track {
  background: transparent;
}

.overflow-y-auto::-webkit-scrollbar-thumb {
  background-color: rgba(156, 163, 175, 0.5);
  border-radius: 2px;
}

.overflow-y-auto::-webkit-scrollbar-thumb:hover {
  background-color: rgba(156, 163, 175, 0.7);
}

.dark .overflow-y-auto::-webkit-scrollbar-thumb {
  background-color: rgba(75, 85, 99, 0.5);
}

.dark .overflow-y-auto::-webkit-scrollbar-thumb:hover {
  background-color: rgba(75, 85, 99, 0.7);
}

/* 代理服务复制按钮去除默认聚焦边框/阴影 */
.proxy-copy-btn,
.proxy-copy-btn:focus,
.proxy-copy-btn:focus-visible,
.proxy-copy-btn:active {
  outline: none !important;
  box-shadow: none !important;
}

.proxy-copy-btn::-moz-focus-inner {
  border: 0;
}
</style>
