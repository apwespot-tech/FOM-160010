import { describe, expect, it } from 'vitest'

import { completeProfile, draftProfile, jsonResponse, mockApi } from './helpers/api'
import { setViewportWidth } from './helpers/media'
import { bodyGet, renderApp, settle, waitForPath, withStoredSession } from './helpers/render'

function completeSession() {
  const api = mockApi({ 'GET /events': () => jsonResponse(200, { items: [], total: 0 }) })
  withStoredSession(api, completeProfile)
  return api
}

describe('Шапка приложения', () => {
  it('на компьютере: логотип, «Мероприятия», «Создать мероприятие» с подписью, уведомления, инициалы', async () => {
    completeSession()
    const { wrapper } = await renderApp('/profile')

    expect(wrapper.text()).toContain('Ищу компанию')
    expect(wrapper.get('[data-testid="nav-events"]').attributes('href')).toBe('/')
    expect(wrapper.get('[data-testid="create-event"]').text()).toContain('Создать мероприятие')
    expect(wrapper.find('[data-testid="notifications-button"]').exists()).toBe(true)
    expect(wrapper.get('[data-testid="profile-menu-button"]').text()).toBe('АИ')
  })

  it('правый блок по макету: аватар — квадрат с инициалами, на колокольчике нет счётчика', async () => {
    completeSession()
    const { wrapper } = await renderApp('/profile')

    const avatar = wrapper.get('[data-testid="profile-menu-button"]')
    expect(avatar.text()).toBe('АИ')
    expect(avatar.classes()).not.toContain('p-button-rounded')
    const create = wrapper.get('[data-testid="create-event"]')
    expect(create.text()).toBe('Создать мероприятие')
    expect(create.find('.pi-plus').exists()).toBe(true)
    const bell = wrapper.get('[data-testid="notifications-button"]')
    expect(bell.find('.p-badge').exists()).toBe(false)
    expect(bell.text()).toBe('')
  })

  it('на мобильном: без ссылки «Мероприятия», кнопки — иконки с доступными именами', async () => {
    completeSession()
    setViewportWidth(360)
    const { wrapper } = await renderApp('/profile')

    expect(wrapper.find('[data-testid="nav-events"]').exists()).toBe(false)
    const create = wrapper.get('[data-testid="create-event"]')
    expect(create.text()).not.toContain('Создать мероприятие')
    expect(create.attributes('aria-label')).toBe('Создать мероприятие')
    expect(wrapper.get('[data-testid="notifications-button"]').attributes('aria-label')).toBe(
      'Уведомления',
    )
  })

  it('граница 640 -> 639 меняет раскладку без перезагрузки', async () => {
    completeSession()
    setViewportWidth(640)
    const { wrapper } = await renderApp('/profile')
    expect(wrapper.get('[data-testid="create-event"]').text()).toContain('Создать мероприятие')

    setViewportWidth(639)
    await settle()
    expect(wrapper.get('[data-testid="create-event"]').text()).not.toContain('Создать')
  })

  it('на странице входа — только логотип', async () => {
    mockApi()
    const { wrapper } = await renderApp('/login')

    expect(wrapper.text()).toContain('Ищу компанию')
    expect(wrapper.find('[data-testid="create-event"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="notifications-button"]').exists()).toBe(false)
  })

  it('незаполненный профиль — только логотип', async () => {
    withStoredSession(mockApi(), draftProfile)
    const { wrapper } = await renderApp('/onboarding')

    expect(wrapper.find('[data-testid="profile-menu-button"]').exists()).toBe(false)
  })

  it('«Создать мероприятие» открывает окно создания', async () => {
    completeSession()
    const { wrapper } = await renderApp('/profile')

    await wrapper.get('[data-testid="create-event"]').trigger('click')
    await settle()

    expect(bodyGet('[data-testid="create-event-dialog"]').textContent).toContain(
      'Новое мероприятие',
    )
  })
})

describe('Меню профиля', () => {
  it('показывает имя и телефон, «Профиль» открывает профиль и закрывает меню', async () => {
    completeSession()
    const { wrapper, router } = await renderApp('/')

    await wrapper.get('[data-testid="profile-menu-button"]').trigger('click')
    await settle()
    const header = bodyGet('[data-testid="profile-menu-header"]').textContent ?? ''
    expect(header).toContain('Анна Иванова')
    expect(header).toContain('+7 999 123-45-67')

    bodyGet('[data-testid="menu-profile"]').click()
    await waitForPath(router, `/users/${completeProfile.id}`)
    expect(document.body.querySelector('[data-testid="profile-menu-header"]')).toBeNull()
  })

  it('Esc закрывает меню без перехода', async () => {
    completeSession()
    const { wrapper, router } = await renderApp('/')

    await wrapper.get('[data-testid="profile-menu-button"]').trigger('click')
    await settle()
    expect(document.body.querySelector('[data-testid="profile-menu-header"]')).not.toBeNull()

    // При открытии меню фокус переходит в список пунктов; Esc обрабатывает он
    bodyGet('.p-menu-list').dispatchEvent(
      new KeyboardEvent('keydown', { key: 'Escape', code: 'Escape', bubbles: true }),
    )
    await settle()

    expect(document.body.querySelector('[data-testid="profile-menu-header"]')).toBeNull()
    expect(router.currentRoute.value.path).toBe('/')
  })
})

describe('Уведомления', () => {
  it('панель-заглушка без запросов к серверу', async () => {
    const api = completeSession()
    const { wrapper } = await renderApp('/profile')
    const before = api.requests.length

    await wrapper.get('[data-testid="notifications-button"]').trigger('click')
    await settle()

    const panel = bodyGet('[data-testid="notifications-panel"]').textContent ?? ''
    expect(panel).toContain('Уведомления')
    expect(panel).toContain('Уведомлений пока нет')
    expect(api.requests.length).toBe(before)
  })
})
