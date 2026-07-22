import axios from 'axios'
import { ElMessage } from 'element-plus'

const request = axios.create({
  baseURL: '/api',
  timeout: 30000,
  withCredentials: true,
})

request.interceptors.response.use(
  (response) => response.data,
  (error) => {
    const status = error.response?.status
    const detail = error.response?.data?.message || error.response?.data?.detail
    const isSessionProbe = error.config?.url?.includes('/auth/me')
    if (status === 401 && !error.config?.url?.includes('/auth/login')) {
      localStorage.removeItem('nutrimind_user')
      if (!isSessionProbe && window.location.pathname !== '/login') window.location.assign('/login')
    }
    if (!error.config?.silent) {
      ElMessage.error(detail || (status ? `请求失败（${status}）` : '无法连接后端服务'))
    }
    return Promise.reject(error)
  },
)

export default request
