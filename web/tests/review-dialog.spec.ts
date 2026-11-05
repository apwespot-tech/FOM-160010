import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { EventItem, Participant } from '@/api/events'
import type { MyReviews, Review } from '@/api/reviews'

import {
  categories,
  completeProfile,
  errorResponse,
  eventItem,
  jsonResponse,
  mockApi,
  type MockHandler,
} from './helpers/api'
import { bodyGet, renderApp, settle, withStoredSession } from './helpers/render'

const ME = completeProfile.id
// Мероприятие началось 30 октября в 18:00 МСК: окно отзывов — с 31 октября 18:00 до 7 ноября 18:00
const STARTED = '2026-10-30T15:00:00Z'
const OPENS_AT = '2026-10-31T15:00:00Z'
const CLOSES_AT = '2026-11-07T15:00:00Z'
const IN_WINDOW = new Date('2026-11-01T09:00:00Z')
const BEFORE_WINDOW = new Date('2026-10-30T17:00:00Z')
const AFTER_WINDOW = new Date('2026-11-08T09:00:00Z')

const organizer: Participant = {
  id: 'org-1',
  name: 'Борис Петров',
  avatar_id: null,
  telegram: null,
  rating: 4.8,
}
const me: Participant = {
  id: ME,
  name: 'Анна Иванова',
  avatar_id: null,
  telegram: null,
  rating: null,
}
const vera: Participant = { id: 'u-3', name: 'Вера', avatar_id: null, telegram: null, rating: 4.6 }

function review(overrides: Partial<Review> = {}): Review {
  return {
    id: 'r1',
    event: { id: 'e1', title: 'Настолки в антикафе' },
    target_id: 'org-1',
    kind: 'organizer',
    stars: 5,
    text: null,
    anonymous: false,
    author: { id: ME, name: 'Анна Иванова', avatar_id: null },
    created_at: '2026-11-01T08:00:00Z',
    updated_at: '2026-11-01T08:00:00Z',
    ...overrides,
  }
}

function pastEvent(overrides: Partial<EventItem> = {}): EventItem {
  return eventItem({
    starts_at: STARTED,
    is_joined: true,
    organizer: { ...organizer, rating: 4.8 },
    participants_count: 3,
    ...overrides,
  })
}

async function open(
  event: EventItem,
  items: Review[] = [],
  handlers: Record<string, MockHandler> = {},
) {
  let reviews = items
  const api = mockApi({
    'GET /events/e1': () => jsonResponse(200, event),
    'GET /events': () => jsonResponse(200, { items: [event], total: 1 }),
    'GET /categories': () => jsonResponse(200, categories),
    'GET /events/e1/participants': () => jsonResponse(200, [organizer, me, vera]),
    'GET /events/e1/reviews/mine': () =>
      jsonResponse(200, {
        items: reviews,
        opens_at: OPENS_AT,
        closes_at: CLOSES_AT,
      } satisfies MyReviews),
    ...handlers,
  })
  withStoredSession(api, completeProfile)
  await renderApp('/events/e1')
  return {
    api,
    setReviews: (next: Review[]) => {
      reviews = next
    },
  }
}

function rows(): HTMLElement[] {
  return [...document.body.querySelectorAll<HTMLElement>('[data-testid="participant"]')]
}

function row(name: string): HTMLElement {
  const found = rows().find((item) => item.textContent?.includes(name))
  if (!found) throw new Error(`Нет строки ${name}`)
  return found
}

function inRow(name: string, testId: string): HTMLElement | null {
  return row(name).querySelector<HTMLElement>(`[data-testid="${testId}"]`)
}

function find(testId: string): HTMLElement | null {
  return document.body.querySelector<HTMLElement>(`[data-testid="${testId}"]`)
}

function text(testId: string): string {
  return find(testId)?.textContent?.trim().replace(/\s+/g, ' ') ?? ''
}

async function click(element: HTMLElement | null): Promise<void> {
  if (!element) throw new Error('Нет элемента')
  element.click()
  await settle()
}

async function chooseStars(count: number): Promise<void> {
  const options = document.body.querySelectorAll<HTMLElement>(
    '[data-testid="review-stars"] .p-rating-option',
  )
  await click(options[count - 1] ?? null)
}

function toasts(): string {
  return document.body.querySelector('.p-toast')?.textContent ?? ''
}

beforeEach(() => {
  vi.useFakeTimers({ toFake: ['Date'] })
  vi.setSystemTime(IN_WINDOW)
})

afterEach(() => {
  vi.useRealTimers()
})

describe('Рейтинг в окне мероприятия', () => {
  it('рейтинг организатора в блоке организатора', async () => {
    await open(pastEvent())
    expect(find('organizer-card')?.textContent).toContain('4,8')
  })

  it('без рейтинга у организатора звезды нет', async () => {
    await open(pastEvent({ organizer: { ...organizer, rating: null } }))
    expect(find('organizer-card')?.querySelector('[data-testid="rating-badge"]')).toBeNull()
  })

  it('рейтинг в строках участников', async () => {
    await open(pastEvent())
    expect(inRow('Борис Петров', 'rating-badge')?.textContent).toContain('4,8')
    expect(inRow('Вера', 'rating-badge')?.textContent).toContain('4,6')
    expect(inRow('Анна Иванова', 'rating-badge')).toBeNull()
  })
})

describe('Кнопки отзывов в окне мероприятия', () => {
  it('в окне: своя оценка и «Изменить», у других «Оценить», в своей строке пусто', async () => {
    await open(pastEvent(), [review()])

    expect(
      inRow('Борис Петров', 'participant-my-stars')?.querySelectorAll('.pi-star-fill'),
    ).toHaveLength(5)
    expect(inRow('Борис Петров', 'participant-review-button')?.textContent).toContain('Изменить')
    expect(inRow('Вера', 'participant-review-button')?.textContent).toContain('Оценить')
    expect(inRow('Анна Иванова', 'participant-review')).toBeNull()
    expect(text('review-hint')).toBe('Оценить участников можно до 7 ноября в 18:00')
  })

  it('до открытия окна: срок «с …», кнопок нет', async () => {
    vi.setSystemTime(BEFORE_WINDOW)
    await open(pastEvent())

    expect(text('review-hint')).toBe('Оценить участников можно будет с 31 октября в 18:00')
    expect(find('participant-review-button')).toBeNull()
  })

  it('после закрытия окна: свои оценки видны, кнопок и срока нет', async () => {
    vi.setSystemTime(AFTER_WINDOW)
    await open(pastEvent(), [review({ stars: 4 })])

    expect(find('participant-review-button')).toBeNull()
    expect(find('review-hint')).toBeNull()
    expect(
      inRow('Борис Петров', 'participant-my-stars')?.querySelectorAll('.pi-star-fill'),
    ).toHaveLength(4)
  })

  it('предстоящее мероприятие: свои отзывы не запрашиваются', async () => {
    const { api } = await open(eventItem({ is_joined: true, starts_at: '2026-11-03T16:00:00Z' }))

    expect(api.calls('GET /events/e1/reviews/mine')).toHaveLength(0)
    expect(find('review-hint')).toBeNull()
  })

  it('незаписанному свои отзывы не запрашиваются', async () => {
    const { api } = await open(pastEvent({ is_joined: false }))
    expect(api.calls('GET /events/e1/reviews/mine')).toHaveLength(0)
  })
})

describe('Окно отзыва', () => {
  it('новый отзыв: звёзды и сохранение', async () => {
    const { api, setReviews } = await open(pastEvent(), [], {
      'POST /events/e1/reviews': (request) => {
        const created = review({ stars: 5, text: 'Супер' })
        setReviews([created])
        expect(request.body).toEqual({
          target_id: 'org-1',
          stars: 5,
          text: 'Супер',
          anonymous: true,
        })
        return jsonResponse(201, created)
      },
    })

    await click(inRow('Борис Петров', 'participant-review-button'))
    expect(text('review-title')).toBe('Отзыв: Борис Петров')
    expect(text('review-kind')).toBe('как об организаторе')
    await chooseStars(5)
    const textarea = bodyGet('[data-testid="review-text"]') as HTMLTextAreaElement
    textarea.value = 'Супер'
    textarea.dispatchEvent(new Event('input'))
    await click(bodyGet('#review-anonymous'))
    await click(find('review-save'))

    expect(api.calls('POST /events/e1/reviews')).toHaveLength(1)
    expect(find('review-dialog')).toBeNull()
    expect(inRow('Борис Петров', 'participant-review-button')?.textContent).toContain('Изменить')
    expect(
      inRow('Борис Петров', 'participant-my-stars')?.querySelectorAll('.pi-star-fill'),
    ).toHaveLength(5)
  })

  it('отзыв об участнике подписан «как об участнике»', async () => {
    await open(pastEvent())
    await click(inRow('Вера', 'participant-review-button'))
    expect(text('review-kind')).toBe('как об участнике')
  })

  it('без оценки: ошибка, запрос не отправляется', async () => {
    const { api } = await open(pastEvent())

    await click(inRow('Вера', 'participant-review-button'))
    await click(find('review-save'))

    expect(text('review-stars-error')).toBe('Поставьте оценку')
    expect(api.calls('POST /events/e1/reviews')).toHaveLength(0)
  })

  it('изменение: поля заполнены, отправляется PATCH', async () => {
    const existing = review({ text: 'Хорошо' })
    const { api, setReviews } = await open(pastEvent(), [existing], {
      'PATCH /reviews/r1': () => {
        const updated = { ...existing, stars: 3 }
        setReviews([updated])
        return jsonResponse(200, updated)
      },
    })

    await click(inRow('Борис Петров', 'participant-review-button'))
    expect((bodyGet('[data-testid="review-text"]') as HTMLTextAreaElement).value).toBe('Хорошо')
    await chooseStars(3)
    await click(find('review-save'))

    expect(api.calls('PATCH /reviews/r1')[0]?.body).toEqual({
      stars: 3,
      text: 'Хорошо',
      anonymous: false,
    })
    expect(
      inRow('Борис Петров', 'participant-my-stars')?.querySelectorAll('.pi-star-fill'),
    ).toHaveLength(3)
  })

  it('удаление своего отзыва с подтверждением', async () => {
    const { api, setReviews } = await open(pastEvent(), [review()], {
      'DELETE /reviews/r1': () => {
        setReviews([])
        return jsonResponse(204)
      },
    })

    await click(inRow('Борис Петров', 'participant-review-button'))
    await click(find('review-delete'))
    await click(find('confirm-accept'))

    expect(api.calls('DELETE /reviews/r1')).toHaveLength(1)
    expect(find('review-dialog')).toBeNull()
    expect(inRow('Борис Петров', 'participant-review-button')?.textContent).toContain('Оценить')
  })

  it('окно отзывов закрылось: сообщение и обновление', async () => {
    const { api } = await open(pastEvent(), [], {
      'POST /events/e1/reviews': () => errorResponse(409, 'review_closed'),
    })
    const loadsBefore = api.calls('GET /events/e1').length

    await click(inRow('Вера', 'participant-review-button'))
    await chooseStars(4)
    await click(find('review-save'))

    expect(toasts()).toContain('Время для отзыва истекло')
    expect(api.calls('GET /events/e1').length).toBeGreaterThan(loadsBefore)
    expect(find('review-dialog')).toBeNull()
  })

  it('отзыв уже оставлен: сообщение и «Изменить»', async () => {
    const { setReviews } = await open(pastEvent(), [], {
      'POST /events/e1/reviews': () => {
        setReviews([review({ target_id: 'u-3', kind: 'participant', id: 'r2' })])
        return errorResponse(409, 'review_exists')
      },
    })

    await click(inRow('Вера', 'participant-review-button'))
    await chooseStars(4)
    await click(find('review-save'))

    expect(toasts()).toContain('Вы уже оставили отзыв')
    expect(inRow('Вера', 'participant-review-button')?.textContent).toContain('Изменить')
  })

  it('отмена: окно закрывается без запросов', async () => {
    const { api } = await open(pastEvent(), [review()])

    await click(inRow('Борис Петров', 'participant-review-button'))
    await chooseStars(1)
    await click(find('review-cancel'))

    expect(find('review-dialog')).toBeNull()
    expect(api.calls('PATCH /reviews/r1')).toHaveLength(0)
    expect(
      inRow('Борис Петров', 'participant-my-stars')?.querySelectorAll('.pi-star-fill'),
    ).toHaveLength(5)
  })
})
