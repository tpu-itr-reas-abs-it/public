import axios, { AxiosError, type AxiosInstance } from 'axios'
import type { ApiError, TokenPair } from '@/types/api'

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api'

const ACCESS_KEY = 'puc.access_token'
const REFRESH_KEY = 'puc.refresh_token'

export const tokenStorage = {
  get access() {
    return localStorage.getItem(ACCESS_KEY)
  },
  get refresh() {
    return localStorage.getItem(REFRESH_KEY)
  },
  save(pair: TokenPair) {
    localStorage.setItem(ACCESS_KEY, pair.access_token)
    localStorage.setItem(REFRESH_KEY, pair.refresh_token)
  },
  clear() {
    localStorage.removeItem(ACCESS_KEY)
    localStorage.removeItem(REFRESH_KEY)
  },
}

export class DomainError extends Error {
  code: string
  details: Record<string, unknown>
  status: number

  constructor(code: string, message: string, details: Record<string, unknown>, status: number) {
    super(message)
    this.name = 'DomainError'
    this.code = code
    this.details = details
    this.status = status
  }
}

let onUnauthorized: (() => void) | null = null
export function setUnauthorizedHandler(handler: () => void) {
  onUnauthorized = handler
}

export const http: AxiosInstance = axios.create({ baseURL: API_BASE_URL, timeout: 20000 })

http.interceptors.request.use((config) => {
  const token = tokenStorage.access
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

let refreshing: Promise<string | null> | null = null

async function refreshTokens(): Promise<string | null> {
  const refresh = tokenStorage.refresh
  if (!refresh) return null
  try {
    const { data } = await axios.post<TokenPair>(`${API_BASE_URL}/auth/refresh`, {
      refresh_token: refresh,
    })
    tokenStorage.save(data)
    return data.access_token
  } catch {
    tokenStorage.clear()
    return null
  }
}

http.interceptors.response.use(
  (response) => response,
  async (error: AxiosError<ApiError>) => {
    const config = error.config as (typeof error.config & { _retried?: boolean }) | undefined
    const status = error.response?.status ?? 0

    const isAuthCall = config?.url?.includes('/auth/')
    if (status === 401 && config && !config._retried && !isAuthCall) {
      config._retried = true
      refreshing = refreshing ?? refreshTokens().finally(() => (refreshing = null))
      const token = await refreshing
      if (token) {
        config.headers = config.headers ?? {}
        config.headers.Authorization = `Bearer ${token}`
        return http.request(config)
      }
      onUnauthorized?.()
    }

    const payload = error.response?.data
    if (payload && typeof payload === 'object' && 'error' in payload) {
      throw new DomainError(
        payload.error.code,
        payload.error.message,
        payload.error.details ?? {},
        status,
      )
    }
    throw new DomainError('network_error', error.message || 'Сервер недоступен', {}, status)
  },
)

export function errorMessage(error: unknown, fallback = 'Неизвестная ошибка'): string {
  if (error instanceof DomainError) {
    const details = error.details as { errors?: { loc: (string | number)[]; msg: string }[] }
    if (error.code === 'request_validation_error' && details.errors?.length) {
      return details.errors.map((item) => `${item.loc.at(-1)}: ${item.msg}`).join('; ')
    }
    if (error.code === 'network_error') return fallback
    return error.message || fallback
  }
  return error instanceof Error && error.message ? error.message : fallback
}
