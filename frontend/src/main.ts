import './style.css'
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { useThemeStore } from '@/stores'
import router from './router'
import App from './App.vue'

// 创建 Vue 应用实例
const app = createApp(App)

// 创建 Pinia 实例
const pinia = createPinia()

// 初始化主题
const themeStore = useThemeStore(pinia)
themeStore.init()

// 使用插件
app.use(pinia)
app.use(router)

// 挂载应用
app.mount('#app')
