import axios from 'axios'
import { message } from 'antd'

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE || '/api',
  timeout: 30000,
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('secflow_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (resp) => resp,
  (error) => {
    const status = error?.response?.status
    if (status === 401 && !location.pathname.startsWith('/login')) {
      localStorage.removeItem('secflow_token')
      location.href = '/login'
    } else if (error?.response?.data?.detail) {
      message.error(String(error.response.data.detail))
    } else if (!error?.response) {
      message.error('网络错误：无法连接 SecFlow API')
    }
    return Promise.reject(error)
  },
)

export const authApi = {
  login: (username: string, password: string) =>
    api.post('/auth/login', { username, password }).then((r) => r.data as { access_token: string }),
  me: () => api.get('/auth/me').then((r) => r.data),
  bootstrap: (username: string, password: string) =>
    api.post('/auth/bootstrap-admin', { username, password }).then((r) => r.data as { access_token: string }),
}

export const healthApi = {
  all: () =>
    Promise.all([
      api.get('/health').catch(() => null),
      api.get('/health/db').catch(() => null),
      api.get('/health/redis').catch(() => null),
      api.get('/health/wazuh').catch(() => null),
      api.get('/health/misp').catch(() => null),
      api.get('/health/llm').catch(() => null),
    ]).then(([api_, db, redis, wazuh, misp, llm]) => ({
      api: api_?.data ?? { ok: false },
      db: db?.data ?? { ok: false },
      redis: redis?.data ?? { ok: false },
      wazuh: wazuh?.data ?? { ok: false },
      misp: misp?.data ?? { ok: false },
      llm: llm?.data ?? { ok: false },
    })),
}
