import InputNumber from 'primevue/inputnumber'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { EventItem, Participant } from '@/api/events'
import type { Profile } from '@/api/profile'

import {
  blobResponse,
  categories,
  completeProfile,
  errorResponse,
  eventItem,
  jsonResponse,
  mockApi,
  photoFile,
  type MockHandler,
} from './helpers/api'
import { setViewportWidth } from './helpers/media'
import { bodyGet, renderApp, settle, waitForPath, withStoredSession } from './helpers/render'

// 2026-10-31 12:00 МСК; мероприятие из eventItem() — завтра в 19:00, создано вчера в 18:40
const NOW = new Date('2026-10-31T09:00:00Z')
const ME = completeProfile.id
const ADMIN: Profile = { ...completeProfile, roles: ['organizer', 'participant', 'admin'] }
const PERSON = { photo_url: null, telegram: null }

beforeEach(() => {
  vi.useFakeTimers({ toFake: ['Date'] })
  vi.setSystemTime(NOW)
})

afterEach(() => {
  vi.useRealTimers()
})

function mine(overrides: Partial<EventItem> = {}): EventItem {
  return eventItem({
    organizer: { id: ME, name: 'Анна Иванова', ...PERSON },
    is_joined: true,
    ...overrides,
  })
}

/** Окно поверх списка: список из одного этого мероприятия, сервер отдаёт текущее состояние. */
async function openEvent(
  event: EventItem,
  handlers: Record<string, MockHandler> = {},
  profile: Profile = completeProfile,
  path = '/events/e1',
) {
  let current = event
  const api = mockApi({
    'GET /events/e1': () => jsonResponse(200, current),
    'GET /events': () => jsonResponse(200, { items: [current], total: 1 }),
    'GET /categories': () => jsonResponse(200, categories),
    'GET /events/e1/participants': () =>
      jsonResponse(200, [
        { ...current.organizer, telegram: null },
        ...(current.is_joined && current.organizer.id !== ME
          ? [{ id: ME, name: 'Анна Иванова', ...PERSON }]
          : []),
      ]),
    ...handlers,
  })
  withStoredSession(api, profile)
  const app = await renderApp(path)
  return {
    api,
    ...app,
    setServerEvent: (next: EventItem) => {
      current = next
    },
  }
}

/** Содержимое окна рендерится в body (teleport). */
function find(testId: string): HTMLElement | null {
  return document.body.querySelector<HTMLElement>(`[data-testid="${testId}"]`)
}

function text(testId: string): string {
  return find(testId)?.textContent?.trim().replace(/\s+/g, ' ') ?? ''
}

function exists(testId: string): boolean {
  return find(testId) !== null
}

async function click(testId: string): Promise<void> {
  bodyGet(`[data-testid="${testId}"]`).click()
  await settle()
}

function all(testId: string): HTMLElement[] {
  return [...document.body.querySelectorAll<HTMLElement>(`[data-testid="${testId}"]`)]
}

function toasts(): string {
  return document.body.querySelector('.p-toast')?.textContent ?? ''
}

function cardPlaces(): string {
  return document.body.querySelector('[data-testid="event-card-places"]')?.textContent?.trim() ?? ''
}

describe('Окно мероприятия поверх списка', () => {
  it('показывает данные в шапке и плитках', async () => {
    await openEvent(eventItem({ min_age: 18, participants_count: 3, free_places: 7 }))

    expect(text('event-title')).toBe('Настолки в антикафе')
    expect(text('event-category')).toBe('Настольные игры')
    expect(text('event-starts-at')).toBe('вс, 1 ноября')
    expect(text('event-time')).toBe('19:00')
    expect(text('event-duration')).toBe('~ 2 ч')
    expect(text('event-place')).toBe('Антикафе «Циферблат»')
    expect(text('event-places')).toContain('3 из 10')
    expect(text('event-age')).toBe('18+')
    expect(text('event-free')).toBe('осталось 7 свободных мест')
    expect(text('event-description')).toBe('Играем в «Каркассон»')
  })

  it('без длительности и возраста', async () => {
    await openEvent(eventItem({ duration_minutes: null, min_age: 0 }))

    expect(text('event-duration')).toBe('не указана')
    expect(exists('event-age')).toBe(false)
  })

  it('за окном — список мероприятий', async () => {
    const { api } = await openEvent(eventItem())

    expect(exists('event-modal')).toBe(true)
    expect(all('event-card')).toHaveLength(1)
    expect(api.calls('GET /events')[0]?.url).toContain('scope=all')
  })

  it('открытие из списка сохраняет вкладку, закрытие возвращает к списку без перезагрузки', async () => {
    const { api, router } = await openEvent(
      eventItem({ is_joined: true }),
      {},
      completeProfile,
      '/?tab=joined',
    )

    all('event-card')[0]?.click()
    await waitForPath(router, '/events/e1')
    expect(router.currentRoute.value.query).toEqual({ tab: 'joined' })
    expect(exists('event-modal')).toBe(true)

    bodyGet('.p-dialog-close-button').click()
    await waitForPath(router, '/')
    expect(router.currentRoute.value.query).toEqual({ tab: 'joined' })
    await vi.waitFor(() => expect(exists('event-modal')).toBe(false))
    expect(api.calls('GET /events')).toHaveLength(1)
  })

  it('прямая ссылка: закрытие ведёт на список', async () => {
    const { router } = await openEvent(eventItem())

    bodyGet('.p-dialog-close-button').click()

    await waitForPath(router, '/')
  })

  it('удалённое мероприятие: «Мероприятие не найдено»', async () => {
    await openEvent(eventItem(), { 'GET /events/e1': () => errorResponse(404, 'not_found') })

    expect(text('event-not-found')).toContain('Мероприятие не найдено')
    expect(text('event-not-found')).toContain('К мероприятиям')
  })

  it('на мобильном — во весь экран', async () => {
    setViewportWidth(360)
    await openEvent(eventItem())

    expect(bodyGet('[data-testid="event-modal"]').className).toContain('event-modal--fullscreen')
  })
})

describe('Блок организатора', () => {
  it('инициалы без фото и дата создания', async () => {
    await openEvent(eventItem())

    expect(text('organizer-name')).toBe('Борис Петров')
    expect(
      find('organizer-card')?.querySelector('[data-testid="avatar-initials"]')?.textContent,
    ).toBe('БП')
    expect(text('organizer-created')).toBe('Создал мероприятие вчера в 18:40')
  })

  it('фото и «Написать», когда сервер отдал Telegram', async () => {
    await openEvent(
      eventItem({
        is_joined: true,
        organizer: {
          id: 'org-1',
          name: 'Борис Петров',
          photo_url: 'https://example.com/b.jpg',
          telegram: '@boris_k',
        },
      }),
    )

    expect(find('organizer-card')?.querySelector('img')?.getAttribute('src')).toBe(
      'https://example.com/b.jpg',
    )
    const write = find('organizer-write') as HTMLAnchorElement
    expect(write.href).toBe('https://t.me/boris_k')
    expect(write.target).toBe('_blank')
  })

  it('организатор не видит «Написать» на своём мероприятии', async () => {
    await openEvent(
      mine({ organizer: { id: ME, name: 'Анна Иванова', photo_url: null, telegram: '@anna_k' } }),
    )
    expect(exists('organizer-write')).toBe(false)
  })

  it('без Telegram (посторонний) — без «Написать»', async () => {
    await openEvent(eventItem())
    expect(exists('organizer-write')).toBe(false)
  })
})

describe('Запись и отказ', () => {
  it('запись: кнопка «Отказаться», места в окне и в карточке списка', async () => {
    const joined = eventItem({ is_joined: true, participants_count: 4, free_places: 6 })
    const { api, setServerEvent } = await openEvent(eventItem(), {
      'POST /events/e1/join': () => {
        setServerEvent(joined)
        return jsonResponse(200, joined)
      },
    })
    expect(exists('participants-hidden')).toBe(true)

    await click('join')

    expect(api.calls('POST /events/e1/join')).toHaveLength(1)
    expect(exists('leave')).toBe(true)
    expect(text('event-places')).toContain('4 из 10')
    expect(cardPlaces()).toBe('Осталось 6 из 10 мест')
    expect(toasts()).toContain('Вы записаны')
    expect(all('participant')).toHaveLength(2)
  })

  it('возраст меньше ограничения: кнопка неактивна, причина рядом', async () => {
    const teen: Profile = { ...completeProfile, birth_date: '2009-03-01', age: 17 }
    await openEvent(eventItem({ min_age: 18 }), {}, teen)

    expect((find('join') as HTMLButtonElement).disabled).toBe(true)
    expect(text('join-blocked')).toBe('Доступно с 18 лет')
  })

  it('место заняли раньше', async () => {
    const full = eventItem({ is_full: true, free_places: 0, participants_count: 10 })
    const { setServerEvent } = await openEvent(eventItem(), {
      'POST /events/e1/join': () => {
        setServerEvent(full)
        return errorResponse(409, 'event_full')
      },
    })

    await click('join')

    expect(toasts()).toContain('Свободных мест нет')
    expect((find('join') as HTMLButtonElement).disabled).toBe(true)
    expect(text('join-blocked')).toBe('Мест нет')
  })

  it('отказ', async () => {
    const left = eventItem({ is_joined: false, participants_count: 2, free_places: 8 })
    const { setServerEvent } = await openEvent(eventItem({ is_joined: true }), {
      'POST /events/e1/leave': () => {
        setServerEvent(left)
        return jsonResponse(200, left)
      },
    })

    await click('leave')

    expect(exists('join')).toBe(true)
    expect(text('event-places')).toContain('2 из 10')
    expect(exists('participants-hidden')).toBe(true)
  })

  it('организатору — тег «Вы организатор», без записи и отказа', async () => {
    await openEvent(mine())

    expect(text('organizer-mark')).toBe('Вы организатор')
    expect(exists('join')).toBe(false)
    expect(exists('leave')).toBe(false)
  })
})

describe('Редактирование в окне', () => {
  it('форма вместо плиток, блока организатора и участников; адрес тот же', async () => {
    const { router } = await openEvent(mine())

    await click('event-edit')

    expect(exists('event-edit-form')).toBe(true)
    expect(text('event-edit-header')).toBe('Редактирование мероприятия')
    expect(exists('organizer-card')).toBe(false)
    expect(exists('participants')).toBe(false)
    expect(exists('event-category')).toBe(false)
    expect((bodyGet('[data-testid="field-title"]') as HTMLInputElement).value).toBe(
      'Настолки в антикафе',
    )
    expect(document.body.textContent).toContain('Максимум участников *')
    expect(router.currentRoute.value.path).toBe('/events/e1')
  })

  it('изменение места: PATCH только с полем, просмотр, карточка списка обновлена', async () => {
    const { api } = await openEvent(mine(), {
      'PATCH /events/e1': () => jsonResponse(200, mine({ place: 'Библиотека', free_places: 3 })),
    })

    await click('event-edit')
    expect(exists('event-place')).toBe(false)
    expect(exists('event-save')).toBe(true)
    expect(exists('event-cancel')).toBe(true)
    const place = bodyGet('[data-testid="field-place"]') as HTMLInputElement
    place.value = 'Библиотека'
    place.dispatchEvent(new Event('input', { bubbles: true }))
    await settle()
    await click('event-save')

    expect(api.calls('PATCH /events/e1')[0]?.body).toEqual({ place: 'Библиотека' })
    expect(text('event-place')).toBe('Библиотека')
    expect(cardPlaces()).toBe('Осталось 3 из 10 мест')
  })

  it('лимит ниже числа участников: ошибка у поля', async () => {
    const { api, wrapper } = await openEvent(mine({ participants_count: 4 }))

    await click('event-edit')
    wrapper
      .findAllComponents(InputNumber)
      .find((input) => input.attributes('data-testid') === 'field-max-participants')
      ?.vm.$emit('update:modelValue', 3)
    await settle()
    await click('event-save')

    expect(text('error-max-participants')).toBe('Не меньше 4 — столько уже записано')
    expect(api.calls('PATCH /events/e1')).toHaveLength(0)
  })

  it('«Отмена» возвращает прежние значения без запросов', async () => {
    const { api } = await openEvent(mine())

    await click('event-edit')
    const place = bodyGet('[data-testid="field-place"]') as HTMLInputElement
    place.value = 'Другое'
    place.dispatchEvent(new Event('input', { bubbles: true }))
    await click('event-cancel')

    expect(text('event-place')).toBe('Антикафе «Циферблат»')
    expect(api.calls('PATCH /events/e1')).toHaveLength(0)
  })

  it('чужое мероприятие — без «Редактировать» и «Удалить»', async () => {
    await openEvent(eventItem({ is_joined: true }))

    expect(exists('event-edit')).toBe(false)
    expect(exists('event-delete')).toBe(false)
  })

  it('администратор видит управление чужим мероприятием', async () => {
    await openEvent(eventItem(), {}, ADMIN)

    expect(exists('event-edit')).toBe(true)
    expect(exists('event-delete')).toBe(true)
  })
})

describe('Удаление', () => {
  it('подтверждение: DELETE, окно закрыто, карточки нет в списке', async () => {
    const { api, router } = await openEvent(mine(), {
      'DELETE /events/e1': () => jsonResponse(204),
    })

    await click('event-delete')
    expect(document.body.textContent).toContain('Удалить мероприятие?')
    await click('confirm-accept')

    expect(api.calls('DELETE /events/e1')).toHaveLength(1)
    await waitForPath(router, '/')
    expect(toasts()).toContain('Мероприятие удалено')
    expect(all('event-card')).toHaveLength(0)
  })

  it('«Отмена» в подтверждении: запроса нет', async () => {
    const { api, router } = await openEvent(mine())

    await click('event-delete')
    await click('confirm-reject')

    expect(api.calls('DELETE /events/e1')).toHaveLength(0)
    expect(router.currentRoute.value.path).toBe('/events/e1')
  })
})

describe('Участники', () => {
  it('организатор первым, Telegram ссылкой, без Telegram — без подзаголовка', async () => {
    const people: Participant[] = [
      { id: 'org-1', name: 'Борис Петров', ...PERSON },
      { id: ME, name: 'Анна Иванова', photo_url: null, telegram: '@anna_k' },
    ]
    await openEvent(eventItem({ is_joined: true, participants_count: 2 }), {
      'GET /events/e1/participants': () => jsonResponse(200, people),
    })

    expect(text('participants-title')).toBe('Участники (2/10)')
    const items = all('participant')
    expect(items[0]?.textContent).toContain('Организатор')
    expect(items[0]?.querySelector('[data-testid="participant-telegram"]')).toBeNull()
    const link = items[1]?.querySelector<HTMLAnchorElement>('[data-testid="participant-telegram"]')
    expect(link?.href).toBe('https://t.me/anna_k')
    expect(exists('participant-remove')).toBe(false)
  })

  it('незаписанный: заглушка без запроса списка', async () => {
    const { api } = await openEvent(eventItem({ is_joined: false }))

    expect(text('participants-hidden')).toBe('Список участников виден после записи')
    expect(api.calls('GET /events/e1/participants')).toHaveLength(0)
  })

  it('автор исключает участника после подтверждения', async () => {
    const people: Participant[] = [
      { id: ME, name: 'Анна Иванова', ...PERSON },
      { id: 'u2', name: 'Борис Петров', ...PERSON },
    ]
    const { api } = await openEvent(mine({ participants_count: 2, free_places: 8 }), {
      'GET /events/e1/participants': () => jsonResponse(200, people),
      'POST /events/e1/participants/u2/remove': () => {
        people.pop()
        return jsonResponse(200, mine({ participants_count: 1, free_places: 9 }))
      },
    })

    await click('participant-remove')
    await click('confirm-accept')

    expect(api.calls('POST /events/e1/participants/u2/remove')).toHaveLength(1)
    expect(all('participant')).toHaveLength(1)
    expect(text('event-places')).toContain('1 из 10')
  })
})

describe('Прошедшее мероприятие', () => {
  const past = { starts_at: '2026-10-30T16:00:00Z' }

  it('отметка, участники, без футера с действиями', async () => {
    await openEvent(mine(past))

    expect(text('event-past')).toBe('Мероприятие прошло')
    expect(exists('event-footer')).toBe(false)
    expect(exists('participant-remove')).toBe(false)
    expect(all('participant').length).toBeGreaterThan(0)
  })

  it('началось, пока окно открыто', async () => {
    const { setServerEvent } = await openEvent(eventItem(), {
      'POST /events/e1/join': () => {
        setServerEvent(eventItem(past))
        return errorResponse(409, 'event_started')
      },
    })

    await click('join')

    expect(toasts()).toContain('Мероприятие уже началось')
    expect(exists('event-past')).toBe(true)
    expect(exists('join')).toBe(false)
  })
})

describe('Галерея фото', () => {
  const photos = (count: number) =>
    Array.from({ length: count }, (_, index) => ({ id: `p${index + 1}` }))
  const photoHandlers = (count: number): Record<string, MockHandler> =>
    Object.fromEntries(
      photos(count).map((photo) => [`GET /events/e1/photos/${photo.id}`, () => blobResponse()]),
    )

  it('без фото блока галереи нет', async () => {
    await openEvent(eventItem())

    expect(exists('event-gallery')).toBe(false)
    expect(exists('event-starts-at')).toBe(true)
  })

  it('4 фото: основное и 3 миниатюры по порядку', async () => {
    const { api } = await openEvent(eventItem({ photos: photos(4) }), photoHandlers(4))
    await settle()

    expect(exists('gallery-main')).toBe(true)
    const thumbs = all('gallery-thumb')
    expect(thumbs.map((thumb) => thumb.getAttribute('aria-label'))).toEqual([
      'Открыть фото 2 из 4',
      'Открыть фото 3 из 4',
      'Открыть фото 4 из 4',
    ])
    expect(find('gallery-main')?.querySelector('img')?.getAttribute('src')).toMatch(/^blob:/)
    // Фото запрашиваются с токеном
    expect(api.calls('GET /events/e1/photos/p1')[0]?.headers.Authorization).toMatch(/^Bearer /)
  })

  it('одно фото — без ряда миниатюр', async () => {
    await openEvent(eventItem({ photos: photos(1) }), photoHandlers(1))

    expect(exists('gallery-main')).toBe(true)
    expect(exists('gallery-thumbs')).toBe(false)
  })

  it('просмотр: «3 из 5», вперёд — 4-е, Esc закрывает только просмотр', async () => {
    await openEvent(eventItem({ photos: photos(5) }), photoHandlers(5))

    await click('gallery-main')
    expect(text('photo-viewer-counter')).toBe('1 из 5')
    await click('photo-viewer-close')
    expect(exists('photo-viewer')).toBe(false)

    all('gallery-thumb')[1]?.click()
    await settle()
    expect(text('photo-viewer-counter')).toBe('3 из 5')

    await click('photo-viewer-next')
    expect(text('photo-viewer-counter')).toBe('4 из 5')

    document.body.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }))
    await settle()
    expect(exists('photo-viewer')).toBe(false)
    expect(exists('event-modal')).toBe(true)
  })

  it('повторное открытие окна не запрашивает фото снова', async () => {
    const { api, router } = await openEvent(eventItem({ photos: photos(2) }), photoHandlers(2))
    await settle()
    const photoUrls = () =>
      api.requests.filter((r) => r.path.startsWith('/events/e1/photos/')).map((r) => r.url)
    // Окно: основное фото целиком и миниатюра второго; карточка списка: копия основного
    const firstOpen = photoUrls()
    expect([...firstOpen].sort()).toEqual([
      '/api/events/e1/photos/p1',
      '/api/events/e1/photos/p1?size=thumb',
      '/api/events/e1/photos/p2?size=thumb',
    ])

    await router.push('/')
    await settle()
    await router.push('/events/e1')
    await settle()

    expect(exists('gallery-main')).toBe(true)
    expect(photoUrls()).toEqual(firstOpen)
  })

  it('ошибка загрузки фото — иконка без текста ошибки', async () => {
    await openEvent(eventItem({ photos: photos(1) }), {
      'GET /events/e1/photos/p1': () => errorResponse(500, 'oops'),
    })
    await settle()

    expect(exists('event-photo-failed')).toBe(true)
    expect(text('event-gallery')).toBe('')
  })
})

describe('Фото в режиме редактирования', () => {
  const withPhotos = (ids: string[], overrides: Partial<EventItem> = {}) =>
    mine({ photos: ids.map((id) => ({ id })), ...overrides })
  const photoHandlers = (ids: string[]): Record<string, MockHandler> =>
    Object.fromEntries(ids.map((id) => [`GET /events/e1/photos/${id}`, () => blobResponse()]))

  function tiles(): HTMLElement[] {
    return all('photo-tile')
  }

  function setPlace(value: string): void {
    const place = bodyGet('[data-testid="field-place"]') as HTMLInputElement
    place.value = value
    place.dispatchEvent(new Event('input', { bubbles: true }))
  }

  it('форма показывает текущие фото', async () => {
    await openEvent(withPhotos(['p1', 'p2']), photoHandlers(['p1', 'p2']))

    await click('event-edit')

    expect(exists('event-gallery')).toBe(false)
    expect(tiles()).toHaveLength(2)
    expect(tiles()[0]?.textContent).toContain('Основное')
  })

  it('изменение места не отправляет фото', async () => {
    const { api } = await openEvent(withPhotos(['p1']), {
      ...photoHandlers(['p1']),
      'PATCH /events/e1': () => jsonResponse(200, withPhotos(['p1'], { place: 'Библиотека' })),
    })

    await click('event-edit')
    setPlace('Библиотека')
    await settle()
    await click('event-save')

    expect(api.calls('PATCH /events/e1')).toHaveLength(1)
    expect(api.calls('PUT /events/e1/photos')).toHaveLength(0)
  })

  it('только фото: без PATCH, PUT с оставшимися, галерея обновлена', async () => {
    const { api } = await openEvent(withPhotos(['p1', 'p2']), {
      ...photoHandlers(['p1', 'p2']),
      'PUT /events/e1/photos': () => jsonResponse(200, withPhotos(['p2'])),
    })

    await click('event-edit')
    tiles()[0]?.querySelector<HTMLElement>('[data-testid="photo-remove"]')?.click()
    await settle()
    await click('event-save')

    expect(api.calls('PATCH /events/e1')).toHaveLength(0)
    const form = api.calls('PUT /events/e1/photos')[0]?.body as FormData
    expect(JSON.parse(String(form.get('order')))).toEqual([{ id: 'p2' }])
    expect(form.getAll('files')).toHaveLength(0)
    expect(exists('event-edit-form')).toBe(false)
    expect(exists('gallery-main')).toBe(true)
    expect(exists('gallery-thumbs')).toBe(false)
  })

  it('поля и фото: ошибка PUT оставляет форму, повтор не шлёт PATCH', async () => {
    let failPhotos = true
    const { api } = await openEvent(withPhotos(['p1']), {
      ...photoHandlers(['p1']),
      'PATCH /events/e1': () =>
        jsonResponse(200, withPhotos(['p1'], { place: 'Библиотека', free_places: 3 })),
      'PUT /events/e1/photos': () =>
        failPhotos
          ? errorResponse(503, 'unavailable')
          : jsonResponse(200, withPhotos(['p1', 'p9'], { place: 'Библиотека' })),
      'GET /events/e1/photos/p9': () => blobResponse(),
    })

    await click('event-edit')
    setPlace('Библиотека')
    const input = bodyGet('[data-testid="photo-input"]') as HTMLInputElement
    Object.defineProperty(input, 'files', { value: [photoFile('new.jpg')], configurable: true })
    input.dispatchEvent(new Event('change', { bubbles: true }))
    await settle()
    await click('event-save')

    expect(api.calls('PATCH /events/e1')).toHaveLength(1)
    expect(api.calls('PUT /events/e1/photos')).toHaveLength(1)
    expect(exists('event-edit-form')).toBe(true)
    expect(text('photo-error')).toBe('Не удалось сохранить фото. Попробуйте ещё раз')
    // Место уже сохранено — карточка списка обновлена
    expect(cardPlaces()).toBe('Осталось 3 из 10 мест')

    failPhotos = false
    await click('event-save')

    expect(api.calls('PATCH /events/e1')).toHaveLength(1)
    expect(api.calls('PUT /events/e1/photos')).toHaveLength(2)
    expect(exists('event-edit-form')).toBe(false)
    expect(all('gallery-thumb')).toHaveLength(1)
  })

  it('«Отмена» откатывает удаление и добавление фото без запросов', async () => {
    const { api } = await openEvent(withPhotos(['p1', 'p2']), photoHandlers(['p1', 'p2']))

    await click('event-edit')
    tiles()[0]?.querySelector<HTMLElement>('[data-testid="photo-remove"]')?.click()
    const input = bodyGet('[data-testid="photo-input"]') as HTMLInputElement
    Object.defineProperty(input, 'files', { value: [photoFile('x.jpg')], configurable: true })
    input.dispatchEvent(new Event('change', { bubbles: true }))
    await settle()
    await click('event-cancel')

    expect(api.calls('PUT /events/e1/photos')).toHaveLength(0)
    expect(all('gallery-thumb')).toHaveLength(1)

    await click('event-edit')
    expect(tiles()).toHaveLength(2)
  })
})
