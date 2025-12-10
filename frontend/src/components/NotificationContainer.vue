<template>
  <div class="fixed top-4 right-4 z-50 space-y-2">
    <TransitionGroup
      name="notification"
      tag="div"
      class="space-y-2"
    >
      <div
        v-for="notification in notifications"
        :key="notification.id"
        :class="[
          'max-w-sm w-full bg-white dark:bg-gray-800 shadow-lg rounded-lg pointer-events-auto ring-1 ring-black ring-opacity-5 overflow-hidden',
          getNotificationClasses(notification.type)
        ]"
      >
        <div class="p-4">
          <div class="flex items-start">
            <div class="flex-shrink-0">
              <Icon :name="getIcon(notification.type)" :class="getIconClasses(notification.type)" />
            </div>
            <div class="ml-3 w-0 flex-1 pt-0.5">
              <p class="text-sm font-medium text-gray-900 dark:text-gray-100">
                {{ notification.title }}
              </p>
              <p class="mt-1 text-sm text-gray-500 dark:text-gray-400">
                {{ notification.message }}
              </p>
            </div>
            <div class="ml-4 flex-shrink-0 flex">
              <button
                @click="removeNotification(notification.id)"
                class="bg-white dark:bg-gray-800 rounded-md inline-flex text-gray-400 hover:text-gray-500 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
              >
                <span class="sr-only">关闭</span>
                <Icon name="x" class="h-5 w-5" />
              </button>
            </div>
          </div>
        </div>
        <div
          v-if="notification.duration > 0"
          class="bg-gray-50 dark:bg-gray-900 px-4 py-2"
          :style="{ width: `${progress}%` }"
        >
          <div class="text-sm text-gray-500 dark:text-gray-400">
            {{ remainingTime }}s
          </div>
        </div>
      </div>
    </TransitionGroup>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted } from 'vue'
import { useNotificationStore } from '@/stores'

interface Notification {
  id: string
  type: 'success' | 'error' | 'warning' | 'info'
  title: string
  message: string
  duration?: number
  timestamp: number
}

// Store
const notificationStore = useNotificationStore()

// 计算属性
const notifications = computed(() => notificationStore.notifications)

// 进度条和剩余时间
const progress = computed(() => {
  // 这里可以添加进度条逻辑
  return 100
})

const remainingTime = computed(() => {
  // 这里可以添加剩余时间逻辑
  return 0
})

// 方法
const removeNotification = (id: string) => {
  notificationStore.removeNotification(id)
}

const getNotificationClasses = (type: string) => {
  const classes = {
    success: 'border-l-4 border-green-400',
    error: 'border-l-4 border-red-400',
    warning: 'border-l-4 border-yellow-400',
    info: 'border-l-4 border-blue-400'
  }
  return classes[type as keyof typeof classes] || classes.info
}

const getIcon = (type: string) => {
  const icons = {
    success: 'check-circle',
    error: 'x-circle',
    warning: 'exclamation-triangle',
    info: 'information-circle'
  }
  return icons[type as keyof typeof icons] || icons.info
}

const getIconClasses = (type: string) => {
  const classes = {
    success: 'h-6 w-6 text-green-400',
    error: 'h-6 w-6 text-red-400',
    warning: 'h-6 w-6 text-yellow-400',
    info: 'h-6 w-6 text-blue-400'
  }
  return classes[type as keyof typeof classes] || classes.info
}

// 生命周期
let interval: NodeJS.Timeout | null = null

onMounted(() => {
  // 自动移除过期的通知
  interval = setInterval(() => {
    const now = Date.now()
    notificationStore.notifications.forEach((notification: Notification) => {
      if (notification.duration && notification.duration > 0) {
        const elapsed = now - notification.timestamp
        if (elapsed >= notification.duration) {
          removeNotification(notification.id)
        }
      }
    })
  }, 1000)
})

onUnmounted(() => {
  if (interval) {
    clearInterval(interval)
  }
})
</script>

<style scoped>
/* 通知动画 */
.notification-enter-active,
.notification-leave-active {
  transition: all 0.3s ease;
}

.notification-enter-from {
  opacity: 0;
  transform: translateX(100%);
}

.notification-leave-to {
  opacity: 0;
  transform: translateX(100%);
}

.notification-move {
  transition: transform 0.3s ease;
}

/* 进度条动画 */
@keyframes progress {
  from {
    width: 100%;
  }
  to {
    width: 0%;
  }
}

.progress-bar {
  animation: progress linear;
}
</style>