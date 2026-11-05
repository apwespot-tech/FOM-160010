import { describe, expect, it } from 'vitest'

import type { EventItem } from '@/api/events'
import { categoryIcon } from '@/utils/categories'

import {
  blobResponse,
  categories,
  completeProfile,
  errorResponse,
  eventItem,
  jsonResponse,
  mockApi,
  type MockHandler,
} from './helpers/api'
import { renderApp, settle, withStoredSession } from './helpers/render'

const CINEMA = categories[3]!

async function renderList(items: EventItem[], handlers: Record<string, MockHandler> = {}) {
  const api = mockApi({
    'GET /events': () => jsonResponse(200, { items, total: items.length }),
    'GET /categories': () => jsonResponse(200, categories),
    'GET /categories/1/covers/cov-1': () => blobResponse('image/webp'),
    'GET /categories/4/covers/cov-4': () => blobResponse('image/webp'),
    ...handlers,
  })
  withStoredSession(api, completeProfile)
  const app = await renderApp('/')
  await settle()
  return { api, ...app }
}

function cards(wrapper: Awaited<ReturnType<typeof renderApp>>['wrapper']) {
  return wrapper.findAll('[data-testid="event-card"]')
}

describe('Обложка карточки мероприятия', () => {
  it('с фото — уменьшенная копия основного фото, исходник не запрашивается', async () => {
    const { api, wrapper } = await renderList(
      [eventItem({ photos: [{ id: 'p1' }, { id: 'p2' }] })],
      {
        'GET /events/e1/photos/p1': () => blobResponse(),
      },
    )

    expect(api.calls('GET /events/e1/photos/p1').map((r) => r.url)).toEqual([
      '/api/events/e1/photos/p1?size=thumb',
    ])
    expect(api.calls('GET /events/e1/photos/p2')).toHaveLength(0)
    expect(api.calls('GET /categories/1/covers/cov-1')).toHaveLength(0)
    expect(wrapper.get('[data-testid="event-cover-img"]').attributes('src')).toMatch(/^blob:/)
  })

  it('без фото — картинка категории, одна на несколько карточек', async () => {
    const items = Array.from({ length: 5 }, (_, i) =>
      eventItem({ id: `e${i}`, category: CINEMA, photos: [] }),
    )
    const { api, wrapper } = await renderList(items)

    expect(api.calls('GET /categories/4/covers/cov-4').map((r) => r.url)).toEqual([
      '/api/categories/4/covers/cov-4?size=thumb',
    ])
    expect(wrapper.findAll('[data-testid="event-cover-img"]')).toHaveLength(5)
  })

  it('фото не загрузилось — картинка категории', async () => {
    const { api, wrapper } = await renderList([eventItem({ photos: [{ id: 'p1' }] })], {
      'GET /events/e1/photos/p1': () => errorResponse(500, 'oops'),
    })

    expect(api.calls('GET /categories/1/covers/cov-1')).toHaveLength(1)
    expect(wrapper.find('[data-testid="event-cover-img"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="event-cover-fallback"]').exists()).toBe(false)
  })

  it('не загрузились ни фото, ни картинка категории — иконка категории без текста', async () => {
    const { wrapper } = await renderList(
      [eventItem({ category: CINEMA, photos: [{ id: 'p1' }] })],
      {
        'GET /events/e1/photos/p1': () => errorResponse(500, 'oops'),
        'GET /categories/4/covers/cov-4': () => errorResponse(500, 'oops'),
      },
    )

    const fallback = wrapper.get('[data-testid="event-cover-fallback"]')
    expect(fallback.classes()).toContain('pi-video')
    expect(wrapper.find('[data-testid="event-cover-img"]').exists()).toBe(false)
    expect(wrapper.get('[data-testid="event-cover"]').text()).not.toContain('oops')
  })

  it('тег категории с иконкой; неизвестная иконка — общая', async () => {
    const { wrapper } = await renderList([eventItem({ category: CINEMA })])

    const tag = wrapper.get('[data-testid="category-tag"]')
    expect(tag.text()).toBe('Кино')
    expect(tag.get('[data-testid="category-tag-icon"]').classes()).toContain('pi-video')
    expect(categoryIcon('pi-no-such-icon')).toBe('pi-tag')
    expect(categoryIcon('🎬')).toBe('pi-tag')
  })
})

describe('Карточка мероприятия в списке', () => {
  function text(card: ReturnType<typeof cards>[number], testId: string): string {
    return card.find(`[data-testid="${testId}"]`).text()
  }

  it('свободные места: «Осталось 3 из 10 мест», «Свободно», полоса 70%, без отметки', async () => {
    const { wrapper } = await renderList([
      eventItem({ max_participants: 10, participants_count: 7, free_places: 3 }),
    ])
    const [card] = cards(wrapper)

    expect(text(card!, 'event-card-places')).toBe('Осталось 3 из 10 мест')
    expect(text(card!, 'event-card-status')).toBe('Свободно')
    expect(card!.get('[data-testid="event-card-bar"]').attributes('aria-valuenow')).toBe('70')
    expect(card!.find('[data-testid="event-card-full"]').exists()).toBe(false)
    expect(card!.find('[data-testid="event-card-joined"]').exists()).toBe(false)
  })

  it('заполнено: «Мест нет», «Заполнено», 100%, отметка «Мест нет»', async () => {
    const { wrapper } = await renderList([
      eventItem({ max_participants: 4, participants_count: 4, free_places: 0, is_full: true }),
    ])
    const [card] = cards(wrapper)

    expect(text(card!, 'event-card-places')).toBe('Мест нет')
    expect(text(card!, 'event-card-status')).toBe('Заполнено')
    expect(card!.get('[data-testid="event-card-bar"]').attributes('aria-valuenow')).toBe('100')
    expect(text(card!, 'event-card-full')).toBe('Мест нет')
  })

  it('записан, в том числе на заполненное: «Вы записаны» и «Записан»', async () => {
    const { wrapper } = await renderList([
      eventItem({ id: 'a', is_joined: true }),
      eventItem({
        id: 'b',
        is_joined: true,
        is_full: true,
        free_places: 0,
        participants_count: 10,
      }),
    ])

    for (const card of cards(wrapper)) {
      expect(text(card, 'event-card-joined')).toBe('Вы записаны')
      expect(text(card, 'event-card-status')).toBe('Записан')
      expect(card.find('[data-testid="event-card-full"]').exists()).toBe(false)
    }
  })

  it('своё мероприятие: «Вы организатор» и «Организатор»', async () => {
    const { wrapper } = await renderList([
      eventItem({
        organizer: { id: completeProfile.id, name: 'Анна', avatar_id: null, telegram: null },
        is_joined: true,
      }),
    ])
    const [card] = cards(wrapper)

    expect(text(card!, 'event-card-organizer')).toBe('Вы организатор')
    expect(text(card!, 'event-card-status')).toBe('Организатор')
  })

  it('город перед местом', async () => {
    const { wrapper } = await renderList([eventItem({ city: { id: 5, name: 'Казань' } })])

    expect(wrapper.get('[data-testid="event-card-place"]').text()).toBe(
      'Казань, Антикафе «Циферблат»',
    )
  })

  it('возраст: 18+ показывается, 0 — нет; дата на обложке', async () => {
    const { wrapper } = await renderList([
      eventItem({ id: 'a', min_age: 18 }),
      eventItem({ id: 'b', min_age: 0 }),
    ])
    const [adult, any] = cards(wrapper)

    expect(text(adult!, 'event-card-age')).toBe('18+')
    expect(any!.find('[data-testid="event-card-age"]').exists()).toBe(false)
    expect(adult!.get('[data-testid="event-card-date"]').attributes('datetime')).toBe(
      '2026-11-01T16:00:00Z',
    )
  })
})

describe('Пустое состояние при поиске', () => {
  it('«Подходящих мероприятий нет» и «Сбросить фильтры» очищает поиск', async () => {
    const api = mockApi({
      'GET /events': () => jsonResponse(200, { items: [], total: 0 }),
      'GET /categories': () => jsonResponse(200, categories),
    })
    withStoredSession(api, completeProfile)
    const { wrapper, router } = await renderApp('/?q=шахматы')

    expect(wrapper.get('[data-testid="events-empty"]').text()).toContain(
      'Подходящих мероприятий нет',
    )
    await wrapper.get('[data-testid="empty-reset-filters"]').trigger('click')
    await settle()

    expect(router.currentRoute.value.query).toEqual({})
  })
})
