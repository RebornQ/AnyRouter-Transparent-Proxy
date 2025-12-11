type StatusTone = 'success' | 'redirect' | 'auth' | 'error' | 'info'

const AUTH_STATUS_CODES = new Set([401, 407, 511])

const badgeClassByTone: Record<StatusTone, string> = {
  success: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400',
  redirect: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400',
  auth: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300',
  error: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400',
  info: 'bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-300'
}

const dotClassByTone: Record<StatusTone, string> = {
  success: 'bg-green-500',
  redirect: 'bg-blue-500',
  auth: 'bg-yellow-500',
  error: 'bg-red-500',
  info: 'bg-gray-400'
}

const containerClassByTone: Record<StatusTone, string> = {
  success: 'bg-gray-50 dark:bg-gray-700',
  redirect: 'bg-blue-50 dark:bg-blue-900/20',
  auth: 'bg-yellow-50 dark:bg-yellow-900/20',
  error: 'bg-red-50 dark:bg-red-900/20',
  info: 'bg-gray-50 dark:bg-gray-700'
}

const getStatusTone = (statusCode?: unknown): StatusTone => {
  if (typeof statusCode !== 'number') return 'info'
  if (statusCode >= 200 && statusCode < 300) return 'success'
  if (statusCode >= 300 && statusCode < 400) return 'redirect'
  if (AUTH_STATUS_CODES.has(statusCode)) return 'auth'
  if (statusCode >= 400) return 'error'
  return 'info'
}

export const isErrorStatus = (statusCode?: unknown): boolean => {
  return typeof statusCode === 'number' && statusCode >= 400
}

export const getStatusBadgeClass = (statusCode?: unknown): string => {
  return badgeClassByTone[getStatusTone(statusCode)]
}

export const getStatusDotClass = (statusCode?: unknown): string => {
  return dotClassByTone[getStatusTone(statusCode)]
}

export const getStatusContainerClass = (statusCode?: unknown): string => {
  return containerClassByTone[getStatusTone(statusCode)]
}

/*
 * 为什么有时候状态码会出现 --，但 getStatusContainerClass、getStatusDotClass、getStatusBadgeClass 都判断成取 error 的颜色了
 * 目前是通过前后端都对请求列表做归一化处理了
 */
export const formatStatusLabel = (statusCode?: unknown): string => {
  if (typeof statusCode === 'number') return `${statusCode}`
  if (statusCode !== undefined && statusCode !== null) return String(statusCode)
  return '--'
}
