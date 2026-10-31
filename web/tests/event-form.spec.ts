import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { nextTick } from 'vue'

import { ApiError } from '@/api/client'
import type { EventItem } from '@/api/events'
import { useEventForm } from '@/composables/useEventForm'

import {
  categories,
  completeProfile,
  errorResponse,
  eventItem,
  jsonResponse,
  mockApi,
} from './helpers/api'
import { setViewportWidth } from './helpers/media'
import { bodyGet, renderApp, settle, waitForPath, withStoredSession } from './helpers/render'

// 2026-10-31 12:00 МСК
const NOW = new Date('2026-10-31T09:00:00Z')
const TOMORROW_19 = new Date(2026, 10, 1, 19, 0)

beforeEach(() => {
  vi.useFakeTimers({ toFake: ['Date'] })
  vi.setSystemTime(NOW)
})

afterEach(() => {
  vi.useRealTimers()
})

function fillValid(form: ReturnType<typeof useEventForm>['form']) {
  form.title = '  Настолки  '
  form.categoryId = 1
  form.startsAt = TOMORROW_19
  form.place = 'Антикафе'
  form.description = 'Играем'
}

describe('Проверка полей формы мероприятия', () => {
  it('создание: пробелы обрезаются, время уходит со смещением браузера', async () => {
    const api = mockApi({ 'POST /events': () => jsonResponse(201, eventItem({ id: 'new' })) })
    const controller = useEventForm({ getInitial: () => null })
    fillValid(controller.form)

    const created = await controller.submit()

    expect(created?.id).toBe('new')
    expect(api.calls('POST /events')[0]?.body).toEqual({
      title: 'Настолки',
      description: 'Играем',
      place: 'Антикафе',
      starts_at: '2026-11-01T19:00:00+03:00',
      duration_minutes: null,
      category_id: 1,
      max_participants: 10,
      min_age: 0,
    })
  })

  it('дата в прошлом: ошибка у поля, запроса нет', async () => {
    const api = mockApi()
    const controller = useEventForm({ getInitial: () => null })
    fillValid(controller.form)
    controller.form.startsAt = new Date(2026, 9, 31, 11, 0)

    expect(await controller.submit()).toBeNull()
    expect(controller.errorFor('startsAt')).toBe('Время начала должно быть в будущем')
    expect(api.requests).toHaveLength(0)
  })

  it.each([
    ['maxParticipants', 1, 'Не меньше 2'],
    ['maxParticipants', 101, 'Не больше 100'],
    ['durationMinutes', 0, 'От 1 до 1440 минут'],
    ['durationMinutes', 1441, 'От 1 до 1440 минут'],
  ] as const)('%s = %i: «%s»', async (field, value, message) => {
    const api = mockApi()
    const controller = useEventForm({ getInitial: () => null })
    fillValid(controller.form)
    controller.form[field] = value

    expect(await controller.submit()).toBeNull()
    expect(controller.errorFor(field)).toBe(message)
    expect(api.requests).toHaveLength(0)
  })

  it('границы допустимы: 2 и 100 участников, 1440 минут', async () => {
    mockApi({ 'POST /events': () => jsonResponse(201, eventItem()) })
    for (const [max, duration] of [
      [2, 1],
      [100, 1440],
    ]) {
      const controller = useEventForm({ getInitial: () => null })
      fillValid(controller.form)
      controller.form.maxParticipants = max ?? null
      controller.form.durationMinutes = duration ?? null
      expect(await controller.submit()).not.toBeNull()
    }
  })

  it('пустые обязательные поля: ошибки показываются после попытки отправки', async () => {
    mockApi()
    const controller = useEventForm({ getInitial: () => null })
    controller.form.title = '   '

    expect(controller.requiredFilled.value).toBe(false)
    expect(controller.errorFor('title')).toBeNull()
    await controller.submit()
    expect(controller.errorFor('title')).toBe('Введите название')
    expect(controller.errorFor('categoryId')).toBe('Выберите категорию')
  })

  it.each([
    [errorResponse(422, 'starts_at_in_past'), 'startsAt', 'Время начала должно быть в будущем'],
    [errorResponse(422, 'category_not_found'), 'categoryId', 'Категория не найдена'],
    [
      jsonResponse(422, { detail: [{ loc: ['body', 'place'], msg: 'too long' }] }),
      'place',
      'Некорректное значение',
    ],
  ] as const)('ошибка сервера у поля %#', async (response, field, message) => {
    mockApi({ 'POST /events': () => response.clone() })
    const controller = useEventForm({ getInitial: () => null })
    fillValid(controller.form)

    expect(await controller.submit()).toBeNull()
    expect(controller.errorFor(field)).toBe(message)
    expect(controller.generalError.value).toBeNull()
  })

  it('прочие ошибки — общая ошибка над кнопками', async () => {
    mockApi({ 'POST /events': () => jsonResponse(500, {}) })
    const controller = useEventForm({ getInitial: () => null })
    fillValid(controller.form)

    await controller.submit()

    expect(controller.generalError.value).toBe(
      'Не удалось сохранить мероприятие. Попробуйте ещё раз',
    )
  })
})

describe('Редактирование: логика формы', () => {
  const initial: EventItem = eventItem({ participants_count: 4, max_participants: 10 })

  it('отправляет только изменённые поля', async () => {
    const api = mockApi({ 'PATCH /events/e1': () => jsonResponse(200, initial) })
    const controller = useEventForm({ getInitial: () => initial })
    controller.form.place = 'Библиотека'

    await controller.submit()

    expect(api.calls('PATCH /events/e1')[0]?.body).toEqual({ place: 'Библиотека' })
  })

  it('без изменений — без запроса', async () => {
    const api = mockApi()
    const controller = useEventForm({ getInitial: () => initial })

    expect(await controller.submit()).toBe(initial)
    expect(api.requests).toHaveLength(0)
  })

  it('лимит не ниже числа записавшихся', async () => {
    const api = mockApi()
    const controller = useEventForm({ getInitial: () => initial })
    controller.form.maxParticipants = 3

    expect(await controller.submit()).toBeNull()
    expect(controller.errorFor('maxParticipants')).toBe('Не меньше 4 — столько уже записано')
    expect(api.requests).toHaveLength(0)
  })

  it('409 limit_below_participants от сервера — у поля', async () => {
    mockApi({ 'PATCH /events/e1': () => errorResponse(409, 'limit_below_participants') })
    const controller = useEventForm({ getInitial: () => initial })
    controller.form.maxParticipants = 5

    await controller.submit()

    expect(controller.errorFor('maxParticipants')).toBe(
      'Лимит меньше числа записавшихся участников',
    )
  })

  it('event_started — общая ошибка', async () => {
    mockApi({ 'PATCH /events/e1': () => errorResponse(409, 'event_started') })
    const controller = useEventForm({ getInitial: () => initial })
    controller.form.title = 'Новое'

    await controller.submit()

    expect(controller.generalError.value).toBe('Мероприятие уже началось')
    expect(new ApiError(409, 'event_started', '')).toBeInstanceOf(ApiError)
  })
})

// --- окно создания ---

function setInput(selector: string, value: string): void {
  const input = bodyGet(selector) as HTMLInputElement | HTMLTextAreaElement
  input.value = value
  input.dispatchEvent(new Event('input', { bubbles: true }))
}

async function chooseCategory(name: string): Promise<void> {
  bodyGet('[data-testid="field-category-id"]').click()
  await settle()
  const option = [...document.body.querySelectorAll<HTMLElement>('[role="option"]')].find(
    (element) => element.textContent?.includes(name),
  )
  if (!option) throw new Error(`Нет категории ${name}`)
  // PrimeVue Select выбирает пункт по mousedown
  option.dispatchEvent(new MouseEvent('mousedown', { bubbles: true }))
  await settle()
}

async function openCreateDialog(width = 360) {
  setViewportWidth(width)
  const api = mockApi({
    'GET /events': () => jsonResponse(200, { items: [], total: 0 }),
    'GET /categories': () => jsonResponse(200, categories),
    'POST /events': () => jsonResponse(201, eventItem({ id: 'new-1' })),
    'GET /events/new-1': () => jsonResponse(200, eventItem({ id: 'new-1' })),
  })
  withStoredSession(api, completeProfile)
  const app = await renderApp('/')
  await app.wrapper.get('[data-testid="create-event"]').trigger('click')
  await settle()
  return { api, ...app }
}

function dialogOpen(): boolean {
  return document.body.querySelector('[data-testid="create-event-dialog"]') !== null
}

describe('Создание мероприятия', () => {
  it('заполнение и создание: окно закрывается, открывается новое мероприятие', async () => {
    const { api, router } = await openCreateDialog()
    const submit = () => bodyGet('[data-testid="create-event-submit"]') as HTMLButtonElement
    expect(submit().disabled).toBe(true)

    setInput('[data-testid="field-title"]', 'Футбол в парке')
    await chooseCategory('Спорт')
    setInput('[data-testid="field-starts-at-native"]', '2026-11-01T19:00')
    setInput('[data-testid="field-place"]', 'Парк Горького')
    setInput('[data-testid="field-description"]', 'Играем 5 на 5')
    await settle()
    expect(submit().disabled).toBe(false)

    submit().click()
    await settle()

    expect(api.calls('POST /events')[0]?.body).toMatchObject({
      title: 'Футбол в парке',
      category_id: 3,
      starts_at: '2026-11-01T19:00:00+03:00',
      place: 'Парк Горького',
      max_participants: 10,
      min_age: 0,
    })
    await waitForPath(router, '/events/new-1')
    await vi.waitFor(() => expect(dialogOpen()).toBe(false))
  })

  it('на мобильном окно во весь экран', async () => {
    await openCreateDialog(360)
    expect(bodyGet('[data-testid="create-event-dialog"]').className).toContain(
      'create-event--fullscreen',
    )
  })

  it('на компьютере окно не во весь экран', async () => {
    await openCreateDialog(1280)
    expect(bodyGet('[data-testid="create-event-dialog"]').className).not.toContain(
      'create-event--fullscreen',
    )
  })

  it('клик по фону закрывает пустую форму, но не форму с введёнными данными', async () => {
    await openCreateDialog()
    setInput('[data-testid="field-title"]', 'Футбол')
    await nextTick()

    const mask = bodyGet('.p-dialog-mask')
    mask.dispatchEvent(new MouseEvent('mousedown', { bubbles: true }))
    mask.dispatchEvent(new MouseEvent('mouseup', { bubbles: true }))
    await settle()
    expect(dialogOpen()).toBe(true)

    bodyGet('[data-testid="create-event-cancel"]').click()
    await vi.waitFor(() => expect(dialogOpen()).toBe(false))
  })

  it('повторное открытие — с чистой формой', async () => {
    const { wrapper } = await openCreateDialog()
    setInput('[data-testid="field-title"]', 'Черновик')
    bodyGet('[data-testid="create-event-cancel"]').click()
    await vi.waitFor(() => expect(dialogOpen()).toBe(false))

    await wrapper.get('[data-testid="create-event"]').trigger('click')
    await settle()

    expect((bodyGet('[data-testid="field-title"]') as HTMLInputElement).value).toBe('')
  })
})
