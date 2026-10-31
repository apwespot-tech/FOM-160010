import type { VueWrapper } from '@vue/test-utils'
import InputNumber from 'primevue/inputnumber'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { EventItem, Participant } from '@/api/events'
import type { Profile } from '@/api/profile'

import {
  categories,
  completeProfile,
  errorResponse,
  eventItem,
  jsonResponse,
  mockApi,
  type MockHandler,
} from './helpers/api'
import { bodyGet, renderApp, settle, waitForPath, withStoredSession } from './helpers/render'

// 2026-10-31 12:00 МСК; мероприятие из eventItem() — завтра в 19:00
const NOW = new Date('2026-10-31T09:00:00Z')
const ME = completeProfile.id
const ADMIN: Profile = { ...completeProfile, roles: ['organizer', 'participant', 'admin'] }

beforeEach(() => {
  vi.useFakeTimers({ toFake: ['Date'] })
  vi.setSystemTime(NOW)
})

afterEach(() => {
  vi.useRealTimers()
})

function mine(overrides: Partial<EventItem> = {}): EventItem {
  return eventItem({
    organizer: { id: ME, name: 'Анна Иванова' },
    is_joined: true,
    ...overrides,
  })
}

async function openEvent(
  event: EventItem,
  handlers: Record<string, MockHandler> = {},
  profile: Profile = completeProfile,
) {
  let current = event
  const api = mockApi({
    'GET /events/e1': () => jsonResponse(200, current),
    'GET /events': () => jsonResponse(200, { items: [], total: 0 }),
    'GET /categories': () => jsonResponse(200, categories),
    'GET /events/e1/participants': () =>
      jsonResponse(200, [
        current.organizer,
        ...(current.is_joined && current.organizer.id !== ME
          ? [{ id: ME, name: 'Анна Иванова' }]
          : []),
      ]),
    ...handlers,
  })
  withStoredSession(api, profile)
  const app = await renderApp('/events/e1')
  return {
    api,
    ...app,
    setServerEvent: (next: EventItem) => {
      current = next
    },
  }
}

function text(wrapper: VueWrapper, testId: string): string {
  return wrapper.get(`[data-testid="${testId}"]`).text()
}

function exists(wrapper: VueWrapper, testId: string): boolean {
  return wrapper.find(`[data-testid="${testId}"]`).exists()
}

function toasts(): string {
  return document.body.querySelector('.p-toast')?.textContent ?? ''
}

describe('Страница мероприятия', () => {
  it('показывает данные мероприятия', async () => {
    const { wrapper } = await openEvent(eventItem({ min_age: 18 }))

    expect(text(wrapper, 'event-title')).toBe('Настолки в антикафе')
    expect(text(wrapper, 'event-category')).toBe('Настольные игры')
    expect(text(wrapper, 'event-starts-at')).toBe('вс, 1 ноября, 19:00')
    expect(text(wrapper, 'event-duration')).toBe('2 ч')
    expect(text(wrapper, 'event-place')).toBe('Антикафе «Циферблат»')
    expect(text(wrapper, 'event-age')).toBe('18+')
    expect(text(wrapper, 'event-places')).toContain('3 из 10')
    expect(text(wrapper, 'event-organizer')).toBe('Борис Петров')
    expect(text(wrapper, 'event-description')).toBe('Играем в «Каркассон»')
  })

  it('без длительности и возраста', async () => {
    const { wrapper } = await openEvent(eventItem({ duration_minutes: null, min_age: 0 }))

    expect(text(wrapper, 'event-duration')).toBe('не указана')
    expect(text(wrapper, 'event-age')).toBe('без ограничений')
  })

  it('удалённое мероприятие: «Мероприятие не найдено» и ссылка на главную', async () => {
    const { wrapper } = await openEvent(eventItem(), {
      'GET /events/e1': () => errorResponse(404, 'not_found'),
    })

    expect(text(wrapper, 'event-not-found')).toContain('Мероприятие не найдено')
    expect(wrapper.get('[data-testid="event-not-found"] a').attributes('href')).toBe('/')
  })
})

describe('Запись и отказ на странице мероприятия', () => {
  it('запись: кнопка меняется на «Отказаться», показывается уведомление', async () => {
    const joined = eventItem({ is_joined: true, participants_count: 4, free_places: 6 })
    const { wrapper, api, setServerEvent } = await openEvent(eventItem(), {
      'POST /events/e1/join': () => {
        setServerEvent(joined)
        return jsonResponse(200, joined)
      },
    })
    expect(exists(wrapper, 'participants-hidden')).toBe(true)

    await wrapper.get('[data-testid="join"]').trigger('click')
    await settle()

    expect(api.calls('POST /events/e1/join')).toHaveLength(1)
    expect(exists(wrapper, 'leave')).toBe(true)
    expect(text(wrapper, 'event-places')).toContain('4 из 10')
    expect(toasts()).toContain('Вы записаны')
    expect(wrapper.findAll('[data-testid="participant"]')).toHaveLength(2)
  })

  it('возраст меньше ограничения: кнопка неактивна, причина рядом', async () => {
    const teen: Profile = { ...completeProfile, birth_date: '2009-03-01', age: 17 }
    const { wrapper } = await openEvent(eventItem({ min_age: 18 }), {}, teen)

    expect(wrapper.get('[data-testid="join"]').attributes('disabled')).toBeDefined()
    expect(text(wrapper, 'join-blocked')).toBe('Доступно с 18 лет')
  })

  it('мест нет: кнопка неактивна с причиной', async () => {
    const { wrapper } = await openEvent(eventItem({ is_full: true, free_places: 0 }))

    expect(wrapper.get('[data-testid="join"]').attributes('disabled')).toBeDefined()
    expect(text(wrapper, 'join-blocked')).toBe('Мест нет')
  })

  it('место заняли раньше: сообщение и обновлённая страница', async () => {
    const full = eventItem({ is_full: true, free_places: 0, participants_count: 10 })
    const { wrapper, api, setServerEvent } = await openEvent(eventItem(), {
      'POST /events/e1/join': () => {
        setServerEvent(full)
        return errorResponse(409, 'event_full')
      },
    })

    await wrapper.get('[data-testid="join"]').trigger('click')
    await settle()

    expect(toasts()).toContain('Свободных мест нет')
    expect(api.calls('GET /events/e1').length).toBeGreaterThan(1)
    expect(wrapper.get('[data-testid="join"]').attributes('disabled')).toBeDefined()
    expect(text(wrapper, 'join-blocked')).toBe('Мест нет')
  })

  it('отказ: кнопка меняется на «Записаться»', async () => {
    const left = eventItem({ is_joined: false, participants_count: 2 })
    const { wrapper, setServerEvent } = await openEvent(eventItem({ is_joined: true }), {
      'POST /events/e1/leave': () => {
        setServerEvent(left)
        return jsonResponse(200, left)
      },
    })

    await wrapper.get('[data-testid="leave"]').trigger('click')
    await settle()

    expect(exists(wrapper, 'join')).toBe(true)
    expect(text(wrapper, 'event-places')).toContain('2 из 10')
    expect(exists(wrapper, 'participants-hidden')).toBe(true)
  })

  it('организатору — отметка «Вы организатор» без записи и отказа', async () => {
    const { wrapper } = await openEvent(mine())

    expect(text(wrapper, 'organizer-mark')).toBe('Вы организатор')
    expect(exists(wrapper, 'join')).toBe(false)
    expect(exists(wrapper, 'leave')).toBe(false)
  })
})

describe('Редактирование мероприятия на месте', () => {
  it('автор меняет место: PATCH только с изменённым полем, возврат в просмотр', async () => {
    const { wrapper, api } = await openEvent(mine(), {
      'PATCH /events/e1': () => jsonResponse(200, mine({ place: 'Библиотека' })),
    })

    await wrapper.get('[data-testid="event-edit"]').trigger('click')
    expect(exists(wrapper, 'event-place')).toBe(false)
    expect(text(wrapper, 'event-organizer')).toBe('Анна Иванова')
    await wrapper.get('[data-testid="field-place"]').setValue('Библиотека')
    await wrapper.get('[data-testid="event-save"]').trigger('click')
    await settle()

    expect(api.calls('PATCH /events/e1')[0]?.body).toEqual({ place: 'Библиотека' })
    expect(text(wrapper, 'event-place')).toBe('Библиотека')
    expect(exists(wrapper, 'event-edit')).toBe(true)
  })

  it('на месте «Редактировать» — «Сохранить» и «Отмена», поля с текущими значениями', async () => {
    const { wrapper } = await openEvent(mine())

    await wrapper.get('[data-testid="event-edit"]').trigger('click')

    const actions = wrapper.get('[data-testid="event-manage-actions"]')
    expect(actions.find('[data-testid="event-save"]').exists()).toBe(true)
    expect(actions.find('[data-testid="event-cancel"]').exists()).toBe(true)
    expect((wrapper.get('[data-testid="field-title"]').element as HTMLInputElement).value).toBe(
      'Настолки в антикафе',
    )
  })

  it('лимит ниже числа участников: ошибка у поля, запроса нет', async () => {
    const { wrapper, api } = await openEvent(mine({ participants_count: 4 }))

    await wrapper.get('[data-testid="event-edit"]').trigger('click')
    const max = wrapper
      .findAllComponents(InputNumber)
      .find((input) => input.attributes('data-testid') === 'field-max-participants')
    max?.vm.$emit('update:modelValue', 3)
    await wrapper.get('[data-testid="event-save"]').trigger('click')
    await settle()

    expect(text(wrapper, 'error-max-participants')).toBe('Не меньше 4 — столько уже записано')
    expect(api.calls('PATCH /events/e1')).toHaveLength(0)
  })

  it('«Отмена» возвращает прежние значения без запросов', async () => {
    const { wrapper, api } = await openEvent(mine())

    await wrapper.get('[data-testid="event-edit"]').trigger('click')
    await wrapper.get('[data-testid="field-place"]').setValue('Другое место')
    await wrapper.get('[data-testid="event-cancel"]').trigger('click')

    expect(text(wrapper, 'event-place')).toBe('Антикафе «Циферблат»')
    expect(api.calls('PATCH /events/e1')).toHaveLength(0)
  })

  it('чужое мероприятие: нет «Редактировать» и «Удалить»', async () => {
    const { wrapper } = await openEvent(eventItem({ is_joined: true }))

    expect(exists(wrapper, 'event-manage-actions')).toBe(false)
  })

  it('администратор видит управление чужим мероприятием', async () => {
    const { wrapper } = await openEvent(eventItem(), {}, ADMIN)

    expect(exists(wrapper, 'event-edit')).toBe(true)
    expect(exists(wrapper, 'event-delete')).toBe(true)
  })
})

describe('Удаление мероприятия', () => {
  it('подтверждение: DELETE, переход на главную, уведомление', async () => {
    const { wrapper, api, router } = await openEvent(mine(), {
      'DELETE /events/e1': () => jsonResponse(204),
    })

    await wrapper.get('[data-testid="event-delete"]').trigger('click')
    await settle()
    expect(document.body.textContent).toContain('Удалить мероприятие?')
    bodyGet('[data-testid="confirm-accept"]').click()
    await settle()

    expect(api.calls('DELETE /events/e1')).toHaveLength(1)
    await waitForPath(router, '/')
    expect(toasts()).toContain('Мероприятие удалено')
  })

  it('«Отмена» в подтверждении: запроса нет', async () => {
    const { wrapper, api, router } = await openEvent(mine())

    await wrapper.get('[data-testid="event-delete"]').trigger('click')
    await settle()
    bodyGet('[data-testid="confirm-reject"]').click()
    await settle()

    expect(api.calls('DELETE /events/e1')).toHaveLength(0)
    expect(router.currentRoute.value.path).toBe('/events/e1')
  })
})

describe('Список участников на странице мероприятия', () => {
  it('участник видит список, организатор первым с отметкой', async () => {
    const { wrapper } = await openEvent(eventItem({ is_joined: true }))

    const items = wrapper.findAll('[data-testid="participant"]')
    expect(items.map((item) => item.text())).toEqual([
      expect.stringContaining('Борис Петров'),
      expect.stringContaining('Анна Иванова'),
    ])
    expect(items[0]?.text()).toContain('Организатор')
    expect(exists(wrapper, 'participant-remove')).toBe(false)
  })

  it('незаписанный: заглушка без запроса списка', async () => {
    const { wrapper, api } = await openEvent(eventItem({ is_joined: false }))

    expect(text(wrapper, 'participants-hidden')).toBe('Список участников виден после записи')
    expect(api.calls('GET /events/e1/participants')).toHaveLength(0)
  })

  it('организатор исключает участника после подтверждения', async () => {
    const participants: Participant[] = [
      { id: ME, name: 'Анна Иванова' },
      { id: 'u2', name: 'Борис Петров' },
    ]
    const { wrapper, api } = await openEvent(mine({ participants_count: 2, free_places: 8 }), {
      'GET /events/e1/participants': () => jsonResponse(200, participants),
      'POST /events/e1/participants/u2/remove': () => {
        participants.pop()
        return jsonResponse(200, mine({ participants_count: 1, free_places: 9 }))
      },
    })

    await wrapper.get('[data-testid="participant-remove"]').trigger('click')
    await settle()
    expect(document.body.textContent).toContain('Исключить участника?')
    bodyGet('[data-testid="confirm-accept"]').click()
    await settle()

    expect(api.calls('POST /events/e1/participants/u2/remove')).toHaveLength(1)
    expect(wrapper.findAll('[data-testid="participant"]')).toHaveLength(1)
    expect(text(wrapper, 'event-places')).toContain('1 из 10')
  })
})

describe('Прошедшее мероприятие', () => {
  const past = { starts_at: '2026-10-30T16:00:00Z' }

  it('отметка, список участников, без кнопок действий', async () => {
    const { wrapper } = await openEvent(mine(past))

    expect(text(wrapper, 'event-past')).toBe('Мероприятие прошло')
    expect(exists(wrapper, 'participation')).toBe(false)
    expect(exists(wrapper, 'event-manage-actions')).toBe(false)
    expect(exists(wrapper, 'participant-remove')).toBe(false)
    expect(wrapper.findAll('[data-testid="participant"]').length).toBeGreaterThan(0)
  })

  it('началось, пока страница открыта: сообщение и режим просмотра', async () => {
    const { wrapper, setServerEvent } = await openEvent(eventItem(), {
      'POST /events/e1/join': () => {
        setServerEvent(eventItem(past))
        return errorResponse(409, 'event_started')
      },
    })

    await wrapper.get('[data-testid="join"]').trigger('click')
    await settle()

    expect(toasts()).toContain('Мероприятие уже началось')
    expect(exists(wrapper, 'event-past')).toBe(true)
    expect(exists(wrapper, 'join')).toBe(false)
  })
})
