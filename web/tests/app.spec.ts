import { describe, expect, it } from 'vitest'

import { completeProfile, jsonResponse, mockApi } from './helpers/api'
import { setViewportWidth } from './helpers/media'
import { renderApp, settle, withStoredSession } from './helpers/render'

describe('App', () => {
  it('монтируется и показывает вход гостю', async () => {
    mockApi()
    const { wrapper, router } = await renderApp('/')

    expect(router.currentRoute.value.path).toBe('/login')
    expect(wrapper.text()).toContain('Ищу компанию')
    expect(wrapper.find('[data-testid="logout"]').exists()).toBe(false)
  })

  it('на компьютере кнопка «Выйти» с текстом, на мобильном — только иконка', async () => {
    const api = mockApi()
    withStoredSession(api, completeProfile)
    const { wrapper } = await renderApp('/profile')

    const logout = () => wrapper.get('[data-testid="logout"]')
    expect(logout().text()).toContain('Выйти')

    // Граница 640 -> 639: раскладка меняется без перезагрузки
    setViewportWidth(640)
    await settle()
    expect(logout().text()).toContain('Выйти')
    setViewportWidth(639)
    await settle()
    expect(logout().text()).not.toContain('Выйти')
    expect(logout().attributes('aria-label')).toBe('Выйти')
  })

  it('выход отзывает токен, очищает сессию и открывает вход', async () => {
    const api = mockApi()
    withStoredSession(api, completeProfile)
    api.on('POST /auth/logout', () => jsonResponse(204))
    const { wrapper, router, session } = await renderApp('/profile')

    await wrapper.get('[data-testid="logout"]').trigger('click')
    await settle()

    expect(api.calls('POST /auth/logout')[0]?.body).toEqual({ refresh_token: 'refresh-1' })
    expect(session.isAuthenticated).toBe(false)
    expect(localStorage.getItem('ik.refreshToken')).toBeNull()
    expect(router.currentRoute.value.path).toBe('/login')
  })
})
