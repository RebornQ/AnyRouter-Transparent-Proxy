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

const getStatusTone = (statusCode?: number, statusText?: string): StatusTone => {
  if (typeof statusCode !== 'number') {
    if (statusText === 'success') return 'success'
    if (statusText === 'error') return 'error'
    return 'info'
  }
  if (statusCode >= 200 && statusCode < 300) return 'success'
  if (statusCode >= 300 && statusCode < 400) return 'redirect'
  if (AUTH_STATUS_CODES.has(statusCode)) return 'auth'
  if (statusCode >= 400) return 'error'
  return 'info'
}

export const isErrorStatus = (statusCode?: number, statusText?: string): boolean => {
  if (typeof statusCode === 'number') {
    return statusCode >= 400
  }
  return statusText === 'error'
}

export const getStatusBadgeClass = (statusCode?: number, statusText?: string): string => {
  return badgeClassByTone[getStatusTone(statusCode, statusText)]
}

export const getStatusDotClass = (statusCode?: number, statusText?: string): string => {
  return dotClassByTone[getStatusTone(statusCode, statusText)]
}

export const getStatusContainerClass = (statusCode?: number, statusText?: string): string => {
  return containerClassByTone[getStatusTone(statusCode, statusText)]
}

export const formatStatusLabel = (statusCode?: number, statusText?: string): string => {
  if (typeof statusCode === 'number') return `${statusCode}`
  if (statusText) return statusText
  return '--'
}
