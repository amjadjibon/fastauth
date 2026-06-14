import axios, { type InternalAxiosRequestConfig } from 'axios'
import { clearTokens, getTokens, setTokens } from './tokens'

export const api = axios.create({
  baseURL: '/',
  withCredentials: false,
})

api.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const { accessToken } = getTokens()
  if (accessToken && config.headers) {
    config.headers.Authorization = `Bearer ${accessToken}`
  }
  return config
})

let refreshing: Promise<void> | null = null

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config
    if (error.response?.status !== 401 || original._retry) {
      return Promise.reject(error)
    }
    original._retry = true

    const { refreshToken } = getTokens()
    if (!refreshToken) {
      clearTokens()
      window.location.href = '/login'
      return Promise.reject(error)
    }

    if (!refreshing) {
      refreshing = api
        .post<{ access_token: string; refresh_token: string }>('/auth/refresh', {
          refresh_token: refreshToken,
        })
        .then((res) => {
          setTokens(res.data.access_token, res.data.refresh_token)
        })
        .catch(() => {
          clearTokens()
          window.location.href = '/login'
        })
        .finally(() => {
          refreshing = null
        })
    }

    await refreshing
    const { accessToken } = getTokens()
    if (!accessToken) return Promise.reject(error)

    original.headers.Authorization = `Bearer ${accessToken}`
    return api(original)
  },
)
