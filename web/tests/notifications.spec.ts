import { afterEach, describe, expect, it, vi } from 'vitest'

import type { AppNotification } from '@/api/notifications'
import { UNREAD_POLL_INTERVAL_MS } from '@/composables/useUnreadNotifications'

import { completeProfile, errorResponse, jsonResponse, mockApi } from './helpers/api'
import { bodyGet, renderApp, settle, waitForPath, withStoredSession } from './helpers/render'

const UNREAD = 'GET /notifications/unread-count'
const LIST = 'GET /notifications'
const READ = 'POST /notifications/read'

type Wrapper = Awaited<ReturnType<typeof renderApp>>['wrapper']

function notification(overrides: Partial<AppNotification>): AppNotification {
  return {
    id: 'n1',
    type: 'participant_joined',
    created_at: '2026-11-11T10:00:00Z',
    read: false,
    event: { id: 'e1', title: 'Мафия' },
    participant: { id: 'u2', name: 'Олег' },
    changed_fields: null,
    ...overrides,
  }
}

function session(unread: number, items: AppNotification[] = []) {
  const api = mockApi({
    'GET /events': () => jsonResponse(200, { items: [], total: 0 }),
    [UNREAD]: () => jsonResponse(200, { unread_count: unread }),
    [LIST]: () => jsonResponse(200, { items, unread_count: items.filter((i) => !i.read).length }),
    [READ]: () => jsonResponse(204),
  })
  withStoredSession(api, completeProfile)
  return api
}

let visibility: DocumentVisibilityState = 'visible'

Object.defineProperty(document, 'visibilityState', {
  configurable: true,
  get: () => visibility,
})

function setVisibility(value: DocumentVisibilityState): void {
  visibility = value
  document.dispatchEvent(new Event('visibilitychange'))
}

afterEach(() => {
  visibility = 'visible'
  vi.useRealTimers()
})

function dot(wrapper: Wrapper) {
  return wrapper.find('[data-testid="notifications-dot"]')
}

async function openPanel(wrapper: Wrapper): Promise<HTMLElement> {
  await wrapper.get('[data-testid="notifications-button"]').trigger('click')
  await settle()
  return bodyGet('[data-testid="notifications-panel"]')
}

function itemTexts(panel: HTMLElement): (string | null | undefined)[] {
  return [...panel.querySelectorAll('[data-testid="notification-item"]')].map(
    (item) => item.querySelector('.notifications__text')?.textContent,
  )
}

describe('Отметка непрочитанных уведомлений', () => {
  it('есть непрочитанные — точка без числа и доступное имя', async () => {
    session(3)
    const { wrapper } = await renderApp('/')

    expect(dot(wrapper).exists()).toBe(true)
    expect(dot(wrapper).text()).toBe('')
    expect(wrapper.get('[data-testid="notifications-button"]').attributes('aria-label')).toBe(
      'Уведомления, есть непрочитанные',
    )
  })

  it('нет непрочитанных — точки нет', async () => {
    session(0)
    const { wrapper } = await renderApp('/')

    expect(dot(wrapper).exists()).toBe(false)
    expect(wrapper.get('[data-testid="notifications-button"]').attributes('aria-label')).toBe(
      'Уведомления',
    )
  })

  it('обновляется раз в 60 секунд, пока вкладка видима', async () => {
    vi.useFakeTimers({ toFake: ['setInterval', 'clearInterval'] })
    const api = session(0)
    const { wrapper } = await renderApp('/')
    expect(api.calls(UNREAD)).toHaveLength(1)

    api.on(UNREAD, () => jsonResponse(200, { unread_count: 2 }))
    vi.advanceTimersByTime(UNREAD_POLL_INTERVAL_MS - 1)
    await settle()
    expect(api.calls(UNREAD)).toHaveLength(1)
    vi.advanceTimersByTime(1)
    await settle()

    expect(api.calls(UNREAD)).toHaveLength(2)
    expect(dot(wrapper).exists()).toBe(true)
  })

  it('скрытая вкладка не опрашивает, при возвращении — сразу запрос', async () => {
    vi.useFakeTimers({ toFake: ['setInterval', 'clearInterval'] })
    const api = session(0)
    await renderApp('/')

    setVisibility('hidden')
    vi.advanceTimersByTime(UNREAD_POLL_INTERVAL_MS * 3)
    await settle()
    expect(api.calls(UNREAD)).toHaveLength(1)

    setVisibility('visible')
    await settle()
    expect(api.calls(UNREAD)).toHaveLength(2)
  })

  it('после выхода запросов нет и точки нет', async () => {
    vi.useFakeTimers({ toFake: ['setInterval', 'clearInterval'] })
    const api = session(2)
    api.on('POST /auth/logout', () => jsonResponse(204))
    const { wrapper, session: store } = await renderApp('/')
    expect(dot(wrapper).exists()).toBe(true)

    await store.logout()
    await settle()
    const before = api.calls(UNREAD).length
    vi.advanceTimersByTime(UNREAD_POLL_INTERVAL_MS * 2)
    setVisibility('visible')
    await settle()

    expect(api.calls(UNREAD)).toHaveLength(before)
    expect(dot(wrapper).exists()).toBe(false)
  })

  it('ошибка запроса не меняет отметку и не показывает сообщений', async () => {
    vi.useFakeTimers({ toFake: ['setInterval', 'clearInterval'] })
    const api = session(1)
    const { wrapper } = await renderApp('/')

    api.on(UNREAD, () => errorResponse(500, 'server_error'))
    vi.advanceTimersByTime(UNREAD_POLL_INTERVAL_MS)
    await settle()

    expect(api.calls(UNREAD)).toHaveLength(2)
    expect(dot(wrapper).exists()).toBe(true)
    expect(document.body.querySelector('.p-toast-message')).toBeNull()
  })
})

describe('Уведомления', () => {
  it('открытие панели: список от новых к старым, непрочитанное выделено', async () => {
    const api = session(1, [
      notification({ id: 'n3', created_at: '2026-11-11T12:00:00Z' }),
      notification({ id: 'n2', type: 'review_reminder', participant: null, read: true }),
      notification({ id: 'n1', type: 'participant_left', read: true }),
    ])
    const { wrapper } = await renderApp('/')

    const panel = await openPanel(wrapper)

    expect(api.calls(LIST)).toHaveLength(1)
    expect(itemTexts(panel)).toEqual([
      'Новый участник «Мафия»: Олег',
      'Оцените участников мероприятия «Мафия»',
      'Отказ от участия в «Мафия»: Олег',
    ])
    const items = panel.querySelectorAll('[data-testid="notification-item"]')
    expect(items[0]?.classList.contains('notifications__item--unread')).toBe(true)
    expect(items[1]?.classList.contains('notifications__item--unread')).toBe(false)
  })

  it('без уведомлений — «Уведомлений пока нет», отметка не отправляется', async () => {
    const api = session(0)
    const { wrapper } = await renderApp('/')

    const panel = await openPanel(wrapper)

    expect(panel.textContent).toContain('Уведомлений пока нет')
    expect(api.calls(READ)).toHaveLength(0)
  })

  it('клик по уведомлению закрывает панель и открывает мероприятие', async () => {
    session(1, [notification({ event: { id: 'e7', title: 'Мафия' } })])
    const { wrapper, router } = await renderApp('/')
    const panel = await openPanel(wrapper)

    panel.querySelector<HTMLElement>('a[data-testid="notification-item"]')?.click()
    await waitForPath(router, '/events/e7')

    expect(document.body.querySelector('[data-testid="notification-item"]')).toBeNull()
  })

  it('уведомление об удалённом мероприятии — не ссылка', async () => {
    session(1, [
      notification({
        type: 'event_deleted',
        participant: null,
        event: { id: null, title: 'Прогулка' },
      }),
    ])
    const { wrapper } = await renderApp('/')

    const panel = await openPanel(wrapper)

    const item = panel.querySelector('[data-testid="notification-item"]')
    expect(item?.tagName).toBe('DIV')
    expect(item?.textContent).toContain('Мероприятие «Прогулка» удалено')
  })

  it('ошибка загрузки — сообщение, точка остаётся', async () => {
    const api = session(2)
    api.on(LIST, () => errorResponse(500, 'server_error'))
    const { wrapper } = await renderApp('/')

    const panel = await openPanel(wrapper)

    expect(panel.textContent).toContain('Не удалось загрузить уведомления')
    expect(api.calls(READ)).toHaveLength(0)
    expect(dot(wrapper).exists()).toBe(true)
  })
})

describe('Прочтение уведомлений при открытии панели', () => {
  it('отметка до самого нового, точка гаснет, выделение остаётся', async () => {
    const api = session(2, [
      notification({ id: 'n2', created_at: '2026-11-11T12:00:00Z' }),
      notification({ id: 'n1', created_at: '2026-11-11T11:00:00Z' }),
    ])
    const { wrapper } = await renderApp('/')
    expect(dot(wrapper).exists()).toBe(true)

    const panel = await openPanel(wrapper)

    expect(api.calls(READ).map((r) => r.body)).toEqual([{ up_to: '2026-11-11T12:00:00Z' }])
    expect(dot(wrapper).exists()).toBe(false)
    expect(panel.querySelectorAll('.notifications__item--unread')).toHaveLength(2)
  })

  it('повторное открытие без новых — ничего не выделено', async () => {
    let read = false
    const api = session(1)
    api.on(LIST, () =>
      jsonResponse(200, { items: [notification({ read })], unread_count: read ? 0 : 1 }),
    )
    api.on(READ, () => {
      read = true
      return jsonResponse(204)
    })
    const { wrapper } = await renderApp('/')

    await openPanel(wrapper)
    // Второй клик закрывает панель, третий — открывает снова
    await wrapper.get('[data-testid="notifications-button"]').trigger('click')
    await settle()
    const panel = await openPanel(wrapper)

    expect(api.calls(LIST)).toHaveLength(2)
    expect(panel.querySelectorAll('.notifications__item--unread')).toHaveLength(0)
  })
})
