import { createApp } from 'vue'
import ElementPlus from 'element-plus'
import { ElMessage } from 'element-plus'
import 'element-plus/dist/index.css'
import App from './App.vue'
import router from './router'

const app = createApp(App)

app.config.errorHandler = (err) => {
  console.error('[Theia] Uncaught error:', err)
  ElMessage.error('页面发生错误，请刷新重试')
}

app.use(ElementPlus)
app.use(router)
app.mount('#app')
