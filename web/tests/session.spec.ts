import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { REFRESH_TOKEN_KEY, useSessionStore } from '@/stores/session'

import { completeProfile, errorResponse, jsonResponse, mockApi, tokens } from './helpers/api'

describe('Сохранение сессии', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('восстанавливает сессию по сохранённому refresh-токену', async () => {
    localStorage.setItem(REFRESH_TOKEN_KEY, 'refresh-0')
    const api = mockApi({
      'POST /auth/refresh': () => jsonResponse(200, tokens(1)),
      'GET /profile': () => jsonResponse(200, completeProfile),
    })
    const session = useSessionStore()

    await session.init()

    expect(api.calls('POST /auth/refresh')[0]?.body).toEqual({ refresh_token: 'refresh-0' })
    expect(api.calls('GET /profile')[0]?.headers.Authorization).toBe('Bearer access-1')
    expect(session.isAuthenticated).toBe(true)
    expect(session.profile).toEqual(completeProfile)
    expect(localStorage.getItem(REFRESH_TOKEN_KEY)).toBe('refresh-1')
  })

  it('без сохранённого токена — гость, запросов нет', async () => {
    const api = mockApi()
    const session = useSessionStore()

    await session.init()

    expect(api.requests).toHaveLength(0)
    expect(session.isAuthenticated).toBe(false)
  })

  it('отклонённый refresh-токен удаляется', async () => {
    localStorage.setItem(REFRESH_TOKEN_KEY, 'refresh-0')
    mockApi({ 'POST /auth/refresh': () => errorResponse(401, 'invalid_token') })
    const session = useSessionStore()

    await session.init()

    expect(session.isAuthenticated).toBe(false)
    expect(localStorage.getItem(REFRESH_TOKEN_KEY)).toBeNull()
  })

  it('init выполняется один раз', async () => {
    localStorage.setItem(REFRESH_TOKEN_KEY, 'refresh-0')
    const api = mockApi({
      'POST /auth/refresh': () => jsonResponse(200, tokens(1)),
      'GET /profile': () => jsonResponse(200, completeProfile),
    })
    const session = useSessionStore()

    await Promise.all([session.init(), session.init()])
    await session.init()

    expect(api.calls('POST /auth/refresh')).toHaveLength(1)
  })
})

describe('Выход', () => {
  beforeEach(() => setActivePinia(createPinia()))

  async function signedIn() {
    mockApi({ 'GET /profile': () => jsonResponse(200, completeProfile) })
    const session = useSessionStore()
    await session.login(tokens(1))
    return session
  }

  it('отзывает refresh-токен и удаляет сессию', async () => {
    const session = await signedIn()
    const api = mockApi({ 'POST /auth/logout': () => jsonResponse(204) })

    await session.logout()

    expect(api.calls('POST /auth/logout')[0]?.body).toEqual({ refresh_token: 'refresh-1' })
    expect(session.isAuthenticated).toBe(false)
    expect(session.accessToken).toBeNull()
    expect(localStorage.getItem(REFRESH_TOKEN_KEY)).toBeNull()
  })

  it('удаляет сессию, даже если сервер недоступен', async () => {
    const session = await signedIn()
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')))

    await expect(session.logout()).resolves.toBeUndefined()

    expect(session.isAuthenticated).toBe(false)
    expect(localStorage.getItem(REFRESH_TOKEN_KEY)).toBeNull()
  })
})
