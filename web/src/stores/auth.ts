import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

import { ApiError, api, getToken, setToken } from '@/api/client'
import type { TokenResponse, User } from '@/types'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<User | null>(null)
  const token = ref<string | null>(getToken())
  const isAuthenticated = computed(() => token.value !== null)

  function logout() {
    setToken(null)
    token.value = null
    user.value = null
  }

  async function fetchMe() {
    if (!token.value) return
    try {
      user.value = await api<User>('/auth/me')
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) logout()
    }
  }

  async function login(email: string, password: string) {
    const data = await api<TokenResponse>('/auth/login', {
      method: 'POST',
      body: { email, password },
    })
    setToken(data.access_token)
    token.value = data.access_token
    await fetchMe()
  }

  async function register(name: string, email: string, password: string) {
    await api<User>('/auth/register', {
      method: 'POST',
      body: { name, email, password },
    })
    await login(email, password)
  }

  return { user, token, isAuthenticated, fetchMe, login, register, logout }
})