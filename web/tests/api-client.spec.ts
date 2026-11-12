import { createPinia, setActivePinia } from 'pinia'
import { describe, expect, it, vi } from 'vitest'

import { ApiError, apiFetch, configureAuth } from '@/api/client'
import { useSessionStore } from '@/stores/session'

import { errorResponse, jsonResponse, mockApi, tokens } from './helpers/api'

describe('apiFetch', () => {
  it('добавляет префикс /api, JSON и заголовок авторизации', async () => {
    const api = mockApi({ 'PATCH /profile': () => jsonResponse(200, { ok: true }) })
    configureAuth({ getAccessToken: () => 'access-1', refresh: async () => null })

    await apiFetch('/profile', { method: 'PATCH', body: { name: 'A' }, auth: true })

    const [request] = api.requests
    expect(request?.url).toBe('/api/profile')
    expect(request?.headers.Authorization).toBe('Bearer access-1')
    expect(request?.headers['Content-Type']).toBe('application/json')
    expect(request?.body).toEqual({ name: 'A' })
  })

  it('без auth не отправляет токен', async () => {
    const api = mockApi({ 'POST /auth/code': () => jsonResponse(200, { expires_in: 300 }) })
    configureAuth({ getAccessToken: () => 'access-1', refresh: async () => null })

    await apiFetch('/auth/code', { method: 'POST', body: { phone: '1' } })

    expect(api.requests[0]?.headers.Authorization).toBeUndefined()
  })

  it('разбирает detail.code и retry_after', async () => {
    mockApi({ 'POST /auth/code': () => errorResponse(429, 'code_cooldown', { retry_after: 42 }) })

    const error = await apiFetch('/auth/code', { method: 'POST', body: {} }).catch((e) => e)

    expect(error).toBeInstanceOf(ApiError)
    expect(error).toMatchObject({ status: 429, code: 'code_cooldown', retryAfter: 42 })
  })

  it('ошибку валидации 422 Pydantic превращает в validation_error с полями', async () => {
    mockApi({
      'PATCH /profile': () =>
        jsonResponse(422, {
          detail: [
            { loc: ['body', 'telegram'], msg: 'bad' },
            { loc: ['body', 'email'], msg: 'bad' },
          ],
        }),
    })

    const error = await apiFetch<never>('/profile', { method: 'PATCH', body: {} }).catch(
      (e: unknown) => e as ApiError,
    )

    expect(error).toMatchObject({ status: 422, code: 'validation_error' })
    expect(error.fields).toEqual(['telegram', 'email'])
  })

  it('сетевую ошибку превращает в network_error', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')))

    const error = await apiFetch('/profile').catch((e) => e)

    expect(error).toMatchObject({ status: 0, code: 'network_error' })
  })

  it('204 возвращает undefined', async () => {
    mockApi({ 'POST /auth/logout': () => jsonResponse(204) })
    await expect(apiFetch('/auth/logout', { method: 'POST', body: {} })).resolves.toBeUndefined()
  })
})

describe('Автоматическое обновление access-токена', () => {
  function setupSession() {
    setActivePinia(createPinia())
    const session = useSessionStore()
    session.accessToken = 'access-0'
    localStorage.setItem('ik.refreshToken', 'refresh-0')
    return session
  }

  it('при 401 обновляет токены и повторяет запрос', async () => {
    const session = setupSession()
    const api = mockApi({
      'GET /profile': (request) =>
        request.headers.Authorization === 'Bearer access-1'
          ? jsonResponse(200, { id: 'u1' })
          : errorResponse(401, 'invalid_token'),
      'POST /auth/refresh': () => jsonResponse(200, tokens(1)),
    })

    const result = await apiFetch('/profile', { auth: true })

    expect(result).toEqual({ id: 'u1' })
    expect(api.calls('POST /auth/refresh')).toHaveLength(1)
    expect(api.calls('POST /auth/refresh')[0]?.body).toEqual({ refresh_token: 'refresh-0' })
    expect(session.accessToken).toBe('access-1')
    expect(localStorage.getItem('ik.refreshToken')).toBe('refresh-1')
  })

  it('одновременные 401 приводят ровно к одному обновлению', async () => {
    setupSession()
    let refreshCalls = 0
    const api = mockApi({
      'GET /profile': (request) =>
        request.headers.Authorization === 'Bearer access-1'
          ? jsonResponse(200, { id: 'u1' })
          : errorResponse(401, 'invalid_token'),
      'POST /auth/refresh': async () => {
        refreshCalls += 1
        // Второй запрос с тем же (уже погашенным) refresh-токеном получил бы 401
        if (refreshCalls > 1) return errorResponse(401, 'invalid_token')
        await new Promise((resolve) => setTimeout(resolve, 10))
        return jsonResponse(200, tokens(1))
      },
    })

    const results = await Promise.all([
      apiFetch('/profile', { auth: true }),
      apiFetch('/profile', { auth: true }),
    ])

    expect(results).toEqual([{ id: 'u1' }, { id: 'u1' }])
    expect(api.calls('POST /auth/refresh')).toHaveLength(1)
    const retried = api
      .calls('GET /profile')
      .filter((r) => r.headers.Authorization === 'Bearer access-1')
    expect(retried).toHaveLength(2)
  })

  it('если обновление не удалось — сессия завершается, повторных попыток нет', async () => {
    const session = setupSession()
    session.profile = { id: 'u1' } as never
    const api = mockApi({
      'GET /profile': () => errorResponse(401, 'invalid_token'),
      'POST /auth/refresh': () => errorResponse(401, 'invalid_token'),
    })

    const error = await apiFetch('/profile', { auth: true }).catch((e) => e)

    expect(error).toMatchObject({ status: 401 })
    expect(api.calls('POST /auth/refresh')).toHaveLength(1)
    expect(api.calls('GET /profile')).toHaveLength(1)
    expect(session.isAuthenticated).toBe(false)
    expect(localStorage.getItem('ik.refreshToken')).toBeNull()
  })

  it('повторный 401 после обновления не запускает новое обновление', async () => {
    setupSession()
    const api = mockApi({
      'GET /profile': () => errorResponse(401, 'invalid_token'),
      'POST /auth/refresh': () => jsonResponse(200, tokens(1)),
    })

    await apiFetch('/profile', { auth: true }).catch(() => undefined)

    expect(api.calls('POST /auth/refresh')).toHaveLength(1)
    expect(api.calls('GET /profile')).toHaveLength(2)
  })
})
