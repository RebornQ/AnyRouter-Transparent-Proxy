<template>
  <div class="space-y-6">
    <!-- 页面标题和操作栏 -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-gray-900 dark:text-white">
          配置管理
        </h1>
        <p class="mt-1 text-sm text-gray-600 dark:text-gray-400">
          管理代理服务的运行配置
        </p>
      </div>
      <div class="flex items-center space-x-3 opacity-60">
        <!-- 导入按钮 -->
        <button
          disabled
          class="px-4 py-2 bg-gray-400 text-white rounded-lg flex items-center cursor-not-allowed"
        >
          <svg class="w-4 h-4 mr-2" fill="currentColor" viewBox="0 0 20 20">
            <path fill-rule="evenodd" d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zM6.293 6.707a1 1 0 010-1.414l3-3a1 1 0 011.414 0l3 3a1 1 0 01-1.414 1.414L11 5.414V13a1 1 0 11-2 0V5.414L7.707 6.707a1 1 0 01-1.414 0z" clip-rule="evenodd"/>
          </svg>
          导入配置
        </button>

        <!-- 导出按钮 -->
        <button
          @click="handleExport"
          :disabled="!config"
          class="px-4 py-2 bg-gray-600 hover:bg-gray-700 disabled:bg-gray-400 text-white rounded-lg transition-colors flex items-center"
        >
          <svg class="w-4 h-4 mr-2" fill="currentColor" viewBox="0 0 20 20">
            <path fill-rule="evenodd" d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm3.293-7.707a1 1 0 011.414 0L9 10.586V3a1 1 0 112 0v7.586l1.293-1.293a1 1 0 111.414 1.414l-3 3a1 1 0 01-1.414 0l-3-3a1 1 0 010-1.414z" clip-rule="evenodd"/>
          </svg>
          导出配置
        </button>

        <!-- 重置按钮 -->
        <button
          disabled
          class="px-4 py-2 bg-yellow-400 text-white rounded-lg flex items-center cursor-not-allowed"
        >
          <svg class="w-4 h-4 mr-2" fill="currentColor" viewBox="0 0 20 20">
            <path fill-rule="evenodd" d="M4 2a1 1 0 011 1v2.101a7.002 7.002 0 0111.601 2.566 1 1 0 11-1.885.666A5.002 5.002 0 005.999 7H9a1 1 0 010 2H4a1 1 0 01-1-1V3a1 1 0 011-1zm.008 9.057a1 1 0 011.276.61A5.002 5.002 0 0014.001 13H11a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0v-2.101a7.002 7.002 0 01-11.601-2.566 1 1 0 01.61-1.276z" clip-rule="evenodd"/>
          </svg>
          重置更改
        </button>

        <!-- 保存按钮 -->
        <button
          disabled
          class="px-4 py-2 bg-blue-400 text-white rounded-lg flex items-center cursor-not-allowed"
        >
          保存配置
        </button>
      </div>
    </div>

    <!-- 状态提示 -->
    <div v-if="hasChanges" class="p-4 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg">
      <div class="flex items-center">
        <svg class="w-5 h-5 text-yellow-600 dark:text-yellow-400 mr-3" fill="currentColor" viewBox="0 0 20 20">
          <path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd"/>
        </svg>
        <div class="flex-1">
          <h3 class="text-sm font-medium text-yellow-800 dark:text-yellow-200">
            配置已修改
          </h3>
          <p class="text-sm text-yellow-700 dark:text-yellow-300 mt-1">
            您有未保存的配置更改，请点击"保存配置"按钮应用更改。
          </p>
        </div>
      </div>
    </div>

    <!-- 错误提示 -->
    <div v-if="error" class="p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
      <div class="flex items-center">
        <svg class="w-5 h-5 text-red-600 dark:text-red-400 mr-3" fill="currentColor" viewBox="0 0 20 20">
          <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"/>
        </svg>
        <div>
          <h3 class="text-sm font-medium text-red-800 dark:text-red-200">
            操作失败
          </h3>
          <p class="text-sm text-red-700 dark:text-red-300 mt-1">
            {{ error }}
          </p>
        </div>
        <button
          @click="clearError"
          class="ml-auto text-red-600 dark:text-red-400 hover:text-red-800 dark:hover:text-red-200"
        >
          <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
            <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd"/>
          </svg>
        </button>
      </div>
    </div>

    <!-- 成功提示 -->
    <div v-if="success" class="p-4 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg">
      <div class="flex items-center">
        <svg class="w-5 h-5 text-green-600 dark:text-green-400 mr-3" fill="currentColor" viewBox="0 0 20 20">
          <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
        </svg>
        <div>
          <h3 class="text-sm font-medium text-green-800 dark:text-green-200">
            操作成功
          </h3>
          <p class="text-sm text-green-700 dark:text-green-300 mt-1">
            {{ success }}
          </p>
        </div>
        <button
          @click="clearSuccess"
          class="ml-auto text-green-600 dark:text-green-400 hover:text-green-800 dark:hover:text-green-200"
        >
          <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
            <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd"/>
          </svg>
        </button>
      </div>
    </div>

    <!-- 加载状态 -->
    <div v-if="!config" class="flex items-center justify-center py-12">
      <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      <span class="ml-3 text-gray-600 dark:text-gray-400">加载配置中...</span>
    </div>

    <!-- 配置表单 -->
    <div v-if="config" class="space-y-6">
      <!-- 基础代理配置 -->
      <div class="bg-white dark:bg-gray-800 shadow-sm border border-gray-200 dark:border-gray-700 rounded-lg">
        <div class="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <h3 class="text-lg font-medium text-gray-900 dark:text-white">
            基础代理配置
          </h3>
          <p class="mt-1 text-sm text-gray-600 dark:text-gray-400">
            配置代理服务的基本参数
          </p>
        </div>
        <div class="p-6 space-y-6">
          <!-- 目标服务器地址 -->
          <div class="opacity-60">
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              目标服务器地址 <span class="text-red-500">*</span>
            </label>
            <input
              v-model="formData.target_base_url"
              type="url"
              readonly
              class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg shadow-sm dark:bg-gray-700 dark:text-white cursor-not-allowed"
              placeholder="https://example.com"
            />
            <p class="mt-1 text-sm text-gray-500 dark:text-gray-400">
              代理请求的目标服务器地址，必须包含协议（http/https）【只读】
            </p>
          </div>

          <!-- 服务端口 -->
          <div class="opacity-60">
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              服务端口 <span class="text-red-500">*</span>
            </label>
            <input
              v-model.number="formData.port"
              type="number"
              readonly
              class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg shadow-sm dark:bg-gray-700 dark:text-white cursor-not-allowed"
              placeholder="8088"
            />
            <p class="mt-1 text-sm text-gray-500 dark:text-gray-400">
              代理服务监听的端口（1-65535）【只读】
            </p>
          </div>

          <!-- 保留 Host 头 -->
          <div class="flex items-center justify-between opacity-60">
            <div>
              <label class="text-sm font-medium text-gray-700 dark:text-gray-300">
                保留 Host 头
              </label>
              <p class="mt-1 text-sm text-gray-500 dark:text-gray-400">
                是否将原始请求的 Host 头转发给目标服务器【只读】
              </p>
            </div>
            <label class="relative inline-flex items-center cursor-not-allowed">
              <input
                v-model="formData.preserve_host"
                type="checkbox"
                disabled
                class="sr-only peer"
              />
              <div class="w-11 h-6 bg-gray-200 rounded-full peer dark:bg-gray-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-gray-600 peer-checked:bg-blue-600"></div>
            </label>
          </div>

          <!-- 调试模式 -->
          <div class="flex items-center justify-between opacity-60">
            <div>
              <label class="text-sm font-medium text-gray-700 dark:text-gray-300">
                调试模式
              </label>
              <p class="mt-1 text-sm text-gray-500 dark:text-gray-400">
                启用详细的请求日志输出【只读】
              </p>
            </div>
            <label class="relative inline-flex items-center cursor-not-allowed">
              <input
                v-model="formData.debug_mode"
                type="checkbox"
                disabled
                class="sr-only peer"
              />
              <div class="w-11 h-6 bg-gray-200 rounded-full peer dark:bg-gray-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-gray-600 peer-checked:bg-blue-600"></div>
            </label>
          </div>
        </div>
      </div>

      <!-- System Prompt 配置 -->
      <div class="bg-white dark:bg-gray-800 shadow-sm border border-gray-200 dark:border-gray-700 rounded-lg">
        <div class="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <h3 class="text-lg font-medium text-gray-900 dark:text-white">
            System Prompt 配置
          </h3>
          <p class="mt-1 text-sm text-gray-600 dark:text-gray-400">
            配置 System Prompt 的处理方式
          </p>
        </div>
        <div class="p-6 space-y-6">
          <!-- System Prompt 替换文本 -->
          <div class="opacity-60">
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              System Prompt 替换文本
            </label>
            <textarea
              v-model="formData.system_prompt_replacement"
              rows="4"
              readonly
              class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg shadow-sm dark:bg-gray-700 dark:text-white cursor-not-allowed"
              placeholder="输入新的 System Prompt 文本..."
            />
            <p class="mt-1 text-sm text-gray-500 dark:text-gray-400">
              留空表示不替换 System Prompt。将用于替换请求中的 System Prompt 内容。【只读】
            </p>
          </div>

          <!-- 插入模式 -->
          <div class="flex items-center justify-between opacity-60">
            <div>
              <label class="text-sm font-medium text-gray-700 dark:text-gray-300">
                插入模式
              </label>
              <p class="mt-1 text-sm text-gray-500 dark:text-gray-400">
                如果请求不包含 "Claude Code" 关键字，则在开头插入新的 System Prompt【只读】
              </p>
            </div>
            <label class="relative inline-flex items-center cursor-not-allowed">
              <input
                v-model="formData.system_prompt_block_insert_if_not_exist"
                type="checkbox"
                disabled
                class="sr-only peer"
              />
              <div class="w-11 h-6 bg-gray-200 rounded-full peer dark:bg-gray-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-gray-600 peer-checked:bg-blue-600"></div>
            </label>
          </div>
        </div>
      </div>

      <!-- 自定义请求头配置 -->
      <div class="bg-white dark:bg-gray-800 shadow-sm border border-gray-200 dark:border-gray-700 rounded-lg">
        <div class="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <h3 class="text-lg font-medium text-gray-900 dark:text-white">
            自定义请求头
          </h3>
          <p class="mt-1 text-sm text-gray-600 dark:text-gray-400">
            配置代理请求添加的自定义 HTTP 头部
          </p>
        </div>
        <div class="p-6 opacity-60">
          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              请求头配置 (JSON 格式)
            </label>
            <textarea
              v-model="customHeadersText"
              rows="8"
              readonly
              class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg shadow-sm dark:bg-gray-700 dark:text-white font-mono text-sm cursor-not-allowed"
              placeholder='{"User-Agent": "My-Custom-Agent", "X-Custom-Header": "value"}'
            />
            <p class="mt-1 text-sm text-gray-500 dark:text-gray-400">
              使用 JSON 格式配置自定义请求头，键名为主机名，值为请求头对象。【只读】
            </p>
          </div>

          <!-- 快速添加常用请求头 -->
          <div class="mt-4">
            <p class="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              快速添加常用请求头
            </p>
            <div class="flex flex-wrap gap-2">
              <button
                disabled
                class="px-3 py-1 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 text-sm rounded-md cursor-not-allowed"
              >
                User-Agent: claude-cli
              </button>
              <button
                disabled
                class="px-3 py-1 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 text-sm rounded-md cursor-not-allowed"
              >
                Content-Type: application/json
              </button>
              <button
                disabled
                class="px-3 py-1 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 text-sm rounded-md cursor-not-allowed"
              >
                Accept: application/json
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- 功能开关 -->
      <div class="bg-white dark:bg-gray-800 shadow-sm border border-gray-200 dark:border-gray-700 rounded-lg">
        <div class="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <h3 class="text-lg font-medium text-gray-900 dark:text-white">
            功能开关
          </h3>
          <p class="mt-1 text-sm text-gray-600 dark:text-gray-400">
            控制各种功能的启用状态
          </p>
        </div>
        <div class="p-6 space-y-4">
          <!-- 仪表板开关 -->
          <div class="flex items-center justify-between opacity-60">
            <div>
              <label class="text-sm font-medium text-gray-700 dark:text-gray-300">
                启用管理面板
              </label>
              <p class="mt-1 text-sm text-gray-500 dark:text-gray-400">
                此选项已锁定，无法修改（防止误操作导致无法访问管理面板）
              </p>
            </div>
            <label class="relative inline-flex items-center cursor-not-allowed">
              <input
                v-model="formData.dashboard_enabled"
                type="checkbox"
                disabled
                class="sr-only peer"
              />
              <div class="w-11 h-6 bg-gray-200 rounded-full peer dark:bg-gray-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-gray-600 peer-checked:bg-blue-600"></div>
            </label>
          </div>
        </div>
      </div>
    </div>

    <!-- 保存确认对话框 -->
    <div
      v-if="showSaveConfirm"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50"
      @click.self="showSaveConfirm = false"
    >
      <div class="bg-white dark:bg-gray-800 rounded-lg p-6 max-w-md mx-4">
        <h3 class="text-lg font-medium text-gray-900 dark:text-white mb-4">
          确认保存配置？
        </h3>
        <p class="text-sm text-gray-600 dark:text-gray-400 mb-6">
          保存配置将立即应用到代理服务，某些更改可能需要重启服务才能生效。
        </p>
        <div class="flex justify-end space-x-3">
          <button
            @click="showSaveConfirm = false"
            class="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 rounded-lg transition-colors"
          >
            取消
          </button>
          <button
            @click="confirmSave"
            class="px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors"
          >
            确认保存
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useConfigStore } from '@/stores'
import type { SystemConfig } from '@/types'

// Store
const configStore = useConfigStore()

// 响应式状态
const loading = ref(false)
const error = ref<string | null>(null)
const success = ref<string | null>(null)
const showSaveConfirm = ref(false)

// 表单数据
const formData = ref<SystemConfig>({
  target_base_url: '',
  preserve_host: false,
  system_prompt_replacement: null,
  system_prompt_block_insert_if_not_exist: false,
  debug_mode: false,
  port: 8088,
  custom_headers: {},
  dashboard_enabled: true
})

// 表单验证错误
const errors = ref<Record<string, string>>({})

// 自定义请求头文本
const customHeadersText = ref('')

// 计算属性
const config = computed(() => configStore.config)

const hasChanges = computed(() => {
  if (!config.value) return false
  return JSON.stringify(formData.value) !== JSON.stringify(config.value)
})

const hasErrors = computed(() => {
  return Object.keys(errors.value).some(key => errors.value[key])
})

const hasCustomHeadersChanges = computed(() => {
  if (!config.value) return false
  try {
    const currentHeaders = JSON.parse(customHeadersText.value || '{}')
    return JSON.stringify(currentHeaders) !== JSON.stringify(config.value.custom_headers)
  } catch {
    return false
  }
})

// 验证单个字段
const validateField = (field: string) => {
  switch (field) {
    case 'target_base_url':
      if (!formData.value.target_base_url?.trim()) {
        errors.value.target_base_url = '目标服务器地址不能为空'
      } else if (!isValidUrl(formData.value.target_base_url)) {
        errors.value.target_base_url = '请输入有效的 URL 地址'
      } else {
        delete errors.value.target_base_url
      }
      break

    case 'port':
      if (!formData.value.port) {
        errors.value.port = '端口不能为空'
      } else if (formData.value.port < 1 || formData.value.port > 65535) {
        errors.value.port = '端口必须在 1-65535 范围内'
      } else {
        delete errors.value.port
      }
      break
  }
}

// 验证自定义请求头
const validateCustomHeaders = () => {
  try {
    const parsed = JSON.parse(customHeadersText.value || '{}')
    if (typeof parsed !== 'object' || Array.isArray(parsed)) {
      errors.value.custom_headers = '自定义请求头必须是 JSON 对象格式'
    } else {
      delete errors.value.custom_headers
      formData.value.custom_headers = parsed
    }
  } catch (err) {
    errors.value.custom_headers = 'JSON 格式无效：' + (err as Error).message
  }
}

// URL 验证
const isValidUrl = (url: string): boolean => {
  try {
    new URL(url)
    return true
  } catch {
    return false
  }
}

// 添加自定义请求头
const addCustomHeader = (key: string, value: string) => {
  try {
    const headers = JSON.parse(customHeadersText.value || '{}')
    headers[key] = value
    customHeadersText.value = JSON.stringify(headers, null, 2)
    validateCustomHeaders()
  } catch (err) {
    console.error('添加自定义请求头失败:', err)
  }
}

// 重置表单
const resetForm = () => {
  if (config.value) {
    formData.value = { ...config.value }
    customHeadersText.value = JSON.stringify(config.value.custom_headers, null, 2)
  }
  errors.value = {}
}

// 处理保存
const handleSave = async () => {
  // 验证所有字段
  validateField('target_base_url')
  validateField('port')
  validateCustomHeaders()

  if (hasErrors.value) {
    error.value = '请修正表单错误后再保存'
    return
  }

  showSaveConfirm.value = true
}

// 确认保存
const confirmSave = async () => {
  showSaveConfirm.value = false
  loading.value = true
  error.value = null
  success.value = null

  try {
    await configStore.updateConfig(formData.value)
    success.value = '配置保存成功'
  } catch (err) {
    error.value = err instanceof Error ? err.message : '保存配置失败'
  } finally {
    loading.value = false
  }
}

// 处理重置
const handleReset = () => {
  resetForm()
  success.value = '配置已重置'
}

// 处理导出
const handleExport = () => {
  if (!config.value) return

  const dataStr = JSON.stringify(config.value, null, 2)
  const dataBlob = new Blob([dataStr], { type: 'application/json' })
  const url = URL.createObjectURL(dataBlob)
  const link = document.createElement('a')
  link.href = url
  link.download = `proxy-config-${new Date().toISOString().split('T')[0]}.json`
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)

  success.value = '配置已导出'
}

// 处理导入
const handleImport = (event: Event) => {
  const file = (event.target as HTMLInputElement).files?.[0]
  if (!file) return

  const reader = new FileReader()
  reader.onload = (e) => {
    try {
      const imported = JSON.parse(e.target?.result as string)
      if (typeof imported === 'object') {
        formData.value = { ...formData.value, ...imported }
        customHeadersText.value = JSON.stringify(imported.custom_headers || {}, null, 2)
        success.value = '配置导入成功'
      } else {
        throw new Error('无效的配置文件格式')
      }
    } catch (err) {
      error.value = '导入失败：' + (err as Error).message
    }
  }
  reader.readAsText(file)

  // 重置文件输入
  const fileInput = event.target as HTMLInputElement
  fileInput.value = ''
}

// 清除消息
const clearError = () => {
  error.value = null
}

const clearSuccess = () => {
  success.value = null
}

// 监听配置变化
watch(config, () => {
  if (config.value) {
    resetForm()
  }
}, { immediate: true })

// 生命周期
onMounted(async () => {
  try {
    await configStore.loadConfig()
  } catch (err) {
    error.value = err instanceof Error ? err.message : '加载配置失败'
  }
})
</script>

<style scoped>
/* 自定义样式 */
.animate-spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}
</style>