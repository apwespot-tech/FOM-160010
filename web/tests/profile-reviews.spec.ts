import { describe, expect, it } from 'vitest'

import type { Profile } from '@/api/profile'
import type { Review, ReviewKind, ReviewPage } from '@/api/reviews'

import {
  categories,
  cities,
  completeProfile,
  errorResponse,
  jsonResponse,
  mockApi,
  type MockHandler,
} from './helpers/api'
import { setViewportWidth } from './helpers/media'
import { renderApp, settle, withStoredSession } from './helpers/render'

const OTHER_ID = 'org-1'
const ADMIN: Profile = { ...completeProfile, roles: ['organizer', 'participant', 'admin'] }

const otherProfile: Profile = {
  ...completeProfile,
  id: OTHER_ID,
  name: 'Борис Петров',
  ratings: {
    as_organizer: { average: 4.8, count: 12 },
    as_participant: { average: null, count: 2 },
  },
}

function review(index: number, overrides: Partial<Review> = {}): Review {
  return {
    id: `r${index}`,
    event: { id: 'e1', title: 'Настолки в антикафе' },
    target_id: OTHER_ID,
    kind: 'organizer',
    stars: 5,
    text: null,
    anonymous: false,
    author: { id: `u${index}`, name: `Автор ${index}`, avatar_id: null },
    created_at: '2026-11-12T10:00:00Z',
    updated_at: '2026-11-12T10:00:00Z',
    ...overrides,
  }
}

/** Сервер отзывов: срез по offset/limit из набора по видам. */
function reviewsHandler(data: Partial<Record<ReviewKind, Review[]>>): MockHandler {
  return (request) => {
    const query = new URL(request.url, 'http://x').searchParams
    const all = data[query.get('kind') as ReviewKind] ?? []
    const offset = Number(query.get('offset'))
    const limit = Number(query.get('limit'))
    return jsonResponse(200, {
      items: all.slice(offset, offset + limit),
      total: all.length,
    } satisfies ReviewPage)
  }
}

async function openProfile(
  data: Partial<Record<ReviewKind, Review[]>>,
  viewer: Profile = completeProfile,
  profile: Profile = otherProfile,
  handlers: Record<string, MockHandler> = {},
) {
  const api = mockApi({
    'GET /categories': () => jsonResponse(200, categories),
    'GET /cities': () => jsonResponse(200, cities),
    [`GET /profile/${profile.id}`]: () => jsonResponse(200, profile),
    [`GET /users/${profile.id}/reviews`]: reviewsHandler(data),
    ...handlers,
  })
  withStoredSession(api, viewer)
  const app = await renderApp(`/users/${profile.id}`)
  return { api, ...app }
}

function find(testId: string): HTMLElement | null {
  return document.body.querySelector<HTMLElement>(`[data-testid="${testId}"]`)
}

function all(testId: string): HTMLElement[] {
  return [...document.body.querySelectorAll<HTMLElement>(`[data-testid="${testId}"]`)]
}

function text(testId: string): string {
  return find(testId)?.textContent?.trim().replace(/\s+/g, ' ') ?? ''
}

async function click(element: HTMLElement | null): Promise<void> {
  if (!element) throw new Error('Нет элемента')
  element.click()
  await settle()
}

describe('Плитки рейтинга в профиле', () => {
  it('рейтинг с числом отзывов и «Мало отзывов»', async () => {
    await openProfile({})

    expect(text('rating-organizer-value')).toBe('4,8')
    expect(text('rating-organizer-count')).toBe('12 отзывов')
    expect(text('rating-organizer')).toContain('Рейтинг организатора')
    expect(text('rating-participant-value')).toBe('Мало отзывов (2)')
    expect(text('rating-participant')).toContain('Рейтинг участника')
  })

  it('нет отзывов: «Мало отзывов (0)»', async () => {
    await openProfile({}, completeProfile, {
      ...otherProfile,
      ratings: {
        as_organizer: { average: null, count: 0 },
        as_participant: { average: null, count: 0 },
      },
    })
    expect(text('rating-participant-value')).toBe('Мало отзывов (0)')
  })

  it('на мобильной ширине плитки в одну колонку', async () => {
    setViewportWidth(360)
    await openProfile({})
    expect(all('rating-organizer')).toHaveLength(1)
    expect(all('rating-participant')).toHaveLength(1)
  })
})

describe('Отзывы в профиле', () => {
  it('вкладки с числами, открыта первая', async () => {
    const { api } = await openProfile({ organizer: [review(1)] })

    expect(text('reviews-tab-organizer')).toBe('Как организатор (12)')
    expect(text('reviews-tab-participant')).toBe('Как участник (2)')
    expect(api.calls(`GET /users/${OTHER_ID}/reviews`)[0]?.url).toContain('kind=organizer')
  })

  it('отзыв: звёзды, комментарий, автор ссылкой, мероприятие и дата', async () => {
    await openProfile({ organizer: [review(1, { stars: 4, text: 'Строка 1\nСтрока 2' })] })

    expect(find('review-stars')?.querySelectorAll('.pi-star-fill')).toHaveLength(4)
    expect(find('review-text')?.textContent).toContain('Строка 1\nСтрока 2')
    expect(find('review-author')?.getAttribute('href')).toBe('/users/u1')
    expect(find('review-event')?.getAttribute('href')).toBe('/events/e1')
    expect(text('review-date')).toBe('12 ноября 2026')
  })

  it('переключение вкладки запрашивает отзывы участника', async () => {
    const { api } = await openProfile({
      organizer: [review(1)],
      participant: [review(2, { kind: 'participant', text: 'Пунктуальный' })],
    })

    await click(find('reviews-tab-participant'))

    expect(api.calls(`GET /users/${OTHER_ID}/reviews`).at(-1)?.url).toContain('kind=participant')
    expect(text('review-text')).toBe('Пунктуальный')
  })

  it('анонимный отзыв: «Анонимно» без ссылки', async () => {
    await openProfile({ organizer: [review(1, { anonymous: true, author: null })] })

    expect(text('review-author-anonymous')).toBe('Анонимно')
    expect(find('review-author')).toBeNull()
    expect(find('review-anonymous-mark')).toBeNull()
  })

  it('подгрузка по 20: 25 отзывов — 20, затем 5', async () => {
    const many = Array.from({ length: 25 }, (_, index) => review(index + 1))
    await openProfile({ organizer: many })

    expect(all('review-item')).toHaveLength(20)
    await click(find('reviews-more'))
    expect(all('review-item')).toHaveLength(25)
    expect(find('reviews-more')).toBeNull()
  })

  it('мероприятие удалено: название без ссылки', async () => {
    await openProfile({
      organizer: [review(1, { event: { id: null, title: 'Старое мероприятие' } })],
    })

    expect(text('review-event')).toBe('Старое мероприятие')
    expect(find('review-event')?.tagName).toBe('SPAN')
  })

  it('нет отзывов: «Отзывов пока нет»', async () => {
    await openProfile({})
    expect(text('reviews-empty')).toBe('Отзывов пока нет')
  })

  it('счётчики по нулям: отзывы не запрашиваются, ошибки нет', async () => {
    const empty: Profile = {
      ...otherProfile,
      ratings: {
        as_organizer: { average: null, count: 0 },
        as_participant: { average: null, count: 0 },
      },
    }
    const { api } = await openProfile({}, completeProfile, empty, {
      [`GET /users/${OTHER_ID}/reviews`]: () => errorResponse(403, 'profile_incomplete'),
    })
    await click(find('reviews-tab-participant'))

    expect(api.calls(`GET /users/${OTHER_ID}/reviews`)).toHaveLength(0)
    expect(text('reviews-empty')).toBe('Отзывов пока нет')
  })
})

describe('Удаление отзыва администратором', () => {
  it('удаляет с подтверждением, обновляет список и плитки', async () => {
    let organizerReviews = [review(1), review(2)]
    let profile = otherProfile
    const { api } = await openProfile({}, ADMIN, otherProfile, {
      [`GET /profile/${OTHER_ID}`]: () => jsonResponse(200, profile),
      [`GET /users/${OTHER_ID}/reviews`]: (request) =>
        reviewsHandler({ organizer: organizerReviews })(request),
      'DELETE /reviews/r1': () => {
        organizerReviews = [review(2)]
        profile = {
          ...otherProfile,
          ratings: { ...otherProfile.ratings, as_organizer: { average: 4.7, count: 11 } },
        }
        return jsonResponse(204)
      },
    })

    await click(all('review-admin-delete')[0] ?? null)
    await click(find('confirm-accept'))

    expect(api.calls('DELETE /reviews/r1')).toHaveLength(1)
    expect(all('review-item')).toHaveLength(1)
    expect(text('reviews-tab-organizer')).toBe('Как организатор (11)')
    expect(text('rating-organizer-count')).toBe('11 отзывов')
  })

  it('администратор видит автора анонимного отзыва с отметкой', async () => {
    await openProfile({ organizer: [review(1, { anonymous: true })] }, ADMIN)

    expect(text('review-author')).toContain('Автор 1')
    expect(text('review-anonymous-mark')).toBe('анонимно')
  })

  it('обычному пользователю кнопок «Удалить» нет', async () => {
    await openProfile({ organizer: [review(1)] })
    expect(find('review-admin-delete')).toBeNull()
  })

  it('на своём профиле кнопок «Удалить» нет', async () => {
    const own: Profile = { ...completeProfile, ratings: otherProfile.ratings }
    await openProfile({ organizer: [review(1)] }, own, own)
    expect(find('review-item')).not.toBeNull()
    expect(find('review-admin-delete')).toBeNull()
  })
})
