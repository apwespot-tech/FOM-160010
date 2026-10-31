import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import * as authApi from '@/api/auth'
import { configureAuth } from '@/api/client'
import * as profileApi from '@/api/profile'
import type { Profile } from '@/api/profile'

export const REFRESH_TOKEN_KEY = 'ik.refreshToken'

function readRefreshToken(): string | null {
  try {
    return localStorage.getItem(REFRESH_TOKEN_KEY)
  } catch {
    return null
  }
}

function writeRefreshToken(token: string | null): void {
  try {
    if (token) localStorage.setItem(REFRESH_TOKEN_KEY, token)
    else localStorage.removeItem(REFRESH_TOKEN_KEY)
  } catch {
    // хранилище недоступно (приватный режим) — сессия живёт до перезагрузки
  }
}

export const useSessionStore = defineStore('session', () => {
  // Access-токен — только в памяти; refresh-токен — в localStorage
  const accessToken = ref<string | null>(null)
  const profile = ref<Profile | null>(null)
  let initPromise: Promise<void> | null = null

  const isAuthenticated = computed(() => accessToken.value !== null && profile.value !== null)
  const isProfileCompleted = computed(() => profile.value?.profile_completed === true)

  function storeTokens(tokens: authApi.TokenPair): void {
    accessToken.value = tokens.access_token
    writeRefreshToken(tokens.refresh_token)
  }

  function clear(): void {
    accessToken.value = null
    profile.value = null
    writeRefreshToken(null)
  }

  async function refresh(): Promise<string | null> {
    const refreshToken = readRefreshToken()
    if (!refreshToken) {
      clear()
      return null
    }
    try {
      const tokens = await authApi.refreshTokens(refreshToken)
      storeTokens(tokens)
      return tokens.access_token
    } catch {
      clear()
      return null
    }
  }

  configureAuth({ getAccessToken: () => accessToken.value, refresh })

  async function loadProfile(): Promise<void> {
    profile.value = await profileApi.getProfile()
  }

  /** Восстановление сессии после перезагрузки; выполняется один раз. */
  function init(): Promise<void> {
    initPromise ??= (async () => {
      if (!readRefreshToken()) return
      if (!(await refresh())) return
      try {
        await loadProfile()
      } catch {
        clear()
      }
    })()
    return initPromise
  }

  async function login(tokens: authApi.TokenPair): Promise<void> {
    storeTokens(tokens)
    await loadProfile()
  }

  /** Локальная сессия удаляется всегда, даже если сервер недоступен. */
  async function logout(): Promise<void> {
    const refreshToken = readRefreshToken()
    clear()
    if (!refreshToken) return
    try {
      await authApi.logout(refreshToken)
    } catch {
      // отзыв на сервере не удался — локально сессия уже удалена
    }
  }

  function setProfile(value: Profile): void {
    profile.value = value
  }

  return {
    accessToken,
    profile,
    isAuthenticated,
    isProfileCompleted,
    init,
    login,
    logout,
    loadProfile,
    setProfile,
    clear,
  }
})
