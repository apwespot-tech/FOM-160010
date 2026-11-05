import { describe, expect, it } from 'vitest'

import { completeProfile, jsonResponse, mockApi } from './helpers/api'
import { bodyGet, renderApp, settle, withStoredSession } from './helpers/render'

describe('App', () => {
  it('монтируется и показывает вход гостю', async () => {
    mockApi()
    const { wrapper, router } = await renderApp('/')

    expect(router.currentRoute.value.path).toBe('/login')
    expect(wrapper.text()).toContain('Ищу компанию')
    expect(wrapper.find('[data-testid="profile-menu-button"]').exists()).toBe(false)
  })

  it('выход из меню профиля отзывает токен, очищает сессию и открывает вход', async () => {
    const api = mockApi()
    withStoredSession(api, completeProfile)
    api.on('POST /auth/logout', () => jsonResponse(204))
    const { wrapper, router, session } = await renderApp('/profile')

    await wrapper.get('[data-testid="profile-menu-button"]').trigger('click')
    await settle()
    bodyGet('[data-testid="logout"]').click()
    await settle()

    expect(api.calls('POST /auth/logout')[0]?.body).toEqual({ refresh_token: 'refresh-1' })
    expect(session.isAuthenticated).toBe(false)
    expect(localStorage.getItem('ik.refreshToken')).toBeNull()
    expect(router.currentRoute.value.path).toBe('/login')
  })

  it('сервер недоступен при выходе — сессия всё равно удаляется', async () => {
    const api = mockApi()
    withStoredSession(api, completeProfile)
    api.on('POST /auth/logout', () => Promise.reject(new TypeError('Failed to fetch')))
    const { wrapper, router, session } = await renderApp('/profile')

    await wrapper.get('[data-testid="profile-menu-button"]').trigger('click')
    await settle()
    bodyGet('[data-testid="logout"]').click()
    await settle()

    expect(session.isAuthenticated).toBe(false)
    expect(router.currentRoute.value.path).toBe('/login')
  })
})
