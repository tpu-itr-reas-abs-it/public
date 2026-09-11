import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { authApi } from '@/api'
import { setUnauthorizedHandler, tokenStorage } from '@/api/http'
import type { UserRead } from '@/types/api'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<UserRead | null>(null)
  const loading = ref(false)
  const ready = ref(false)

  const isAuthenticated = computed(() => user.value !== null)

  async function loadMe(): Promise<void> {
    if (!tokenStorage.access) {
      ready.value = true
      return
    }
    try {
      user.value = await authApi.me()
    } catch {
      tokenStorage.clear()
      user.value = null
    } finally {
      ready.value = true
    }
  }

  async function login(email: string, password: string): Promise<void> {
    loading.value = true
    try {
      tokenStorage.save(await authApi.login(email, password))
      user.value = await authApi.me()
    } finally {
      loading.value = false
    }
  }

  async function register(email: string, password: string, fullName: string): Promise<void> {
    loading.value = true
    try {
      tokenStorage.save(await authApi.register(email, password, fullName))
      user.value = await authApi.me()
    } finally {
      loading.value = false
    }
  }

  function logout(): void {
    tokenStorage.clear()
    user.value = null
  }

  setUnauthorizedHandler(() => {
    user.value = null
    tokenStorage.clear()
  })

  return { user, loading, ready, isAuthenticated, loadMe, login, register, logout }
})
