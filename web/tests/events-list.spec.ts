import DatePicker from 'primevue/datepicker'
import InputNumber from 'primevue/inputnumber'
import { describe, expect, it } from 'vitest'

import type { EventItem } from '@/api/events'
import { buildListQuery, parseListQuery, toListParams } from '@/composables/useEventListQuery'

import {
  categories,
  completeProfile,
  eventItem,
  jsonResponse,
  mockApi,
  type MockRequest,
} from './helpers/api'
import { setViewportWidth } from './helpers/media'
import { bodyGet, renderApp, settle, waitForPath, withStoredSession } from './helpers/render'

function query(request: MockRequest): URLSearchParams {
  return new URLSearchParams(request.url.split('?')[1] ?? '')
}

function page(items: EventItem[], total = items.length) {
  return jsonResponse(200, { items, total })
}

function listApi(handler: (request: MockRequest) => Response | Promise<Response>) {
  const api = mockApi({
    'GET /events': handler,
    'GET /categories': () => jsonResponse(200, categories),
  })
  withStoredSession(api, completeProfile)
  return api
}

function lastListQuery(api: ReturnType<typeof mockApi>): URLSearchParams {
  const calls = api.calls('GET /events')
  const last = calls[calls.length - 1]
  if (!last) throw new Error('Список не запрашивался')
  return query(last)
}

describe('Состояние списка в адресе', () => {
  it('разбор адреса со всеми параметрами', () => {
    const state = parseListQuery({
      tab: 'joined',
      period: 'past',
      category: '3',
      from: '2026-12-01',
      to: '2026-12-02',
      places: '3',
    })
    expect(state.tab).toBe('joined')
    expect(state.minFreePlaces).toBe(3)
    expect(state.period).toBe('past')
    expect(state.categoryId).toBe(3)
    expect(state.from?.getDate()).toBe(1)
    expect(toListParams(state)).toEqual({
      scope: 'joined',
      period: 'past',
      min_free_places: 3,
      category_id: 3,
      from: '2026-12-01T00:00:00+03:00',
      to: '2026-12-03T00:00:00+03:00',
    })
  })

  it('некорректные значения отбрасываются, период для «Найти компанию» не применяется', () => {
    const state = parseListQuery({
      tab: 'mine',
      period: 'past',
      category: 'abc',
      from: 'x',
      places: '101',
    })
    expect(state).toEqual({
      tab: 'find',
      period: 'upcoming',
      categoryId: null,
      from: null,
      to: null,
      minFreePlaces: null,
    })
    expect(toListParams(state)).toEqual({ scope: 'all' })
  })

  it('значения по умолчанию в адрес не пишутся', () => {
    expect(
      buildListQuery({
        tab: 'find',
        period: 'upcoming',
        categoryId: null,
        from: null,
        to: null,
        minFreePlaces: null,
      }),
    ).toEqual({})
    expect(
      buildListQuery({
        tab: 'organized',
        period: 'past',
        categoryId: 2,
        from: null,
        to: null,
        minFreePlaces: 4,
      }),
    ).toEqual({ tab: 'organized', period: 'past', category: '2', places: '4' })
  })
})

describe('Вкладки списка мероприятий', () => {
  it('главная: «Найти компанию», предстоящие, без переключателя периода', async () => {
    const api = listApi(() => page([eventItem()]))
    const { wrapper } = await renderApp('/')

    expect(lastListQuery(api).get('scope')).toBe('all')
    expect(lastListQuery(api).has('period')).toBe(false)
    expect(wrapper.find('[data-testid="period"]').exists()).toBe(false)
    expect(wrapper.findAll('[data-testid="event-card"]')).toHaveLength(1)
  })

  it('«Организую» -> «Прошедшие»: запрос scope=organized&period=past', async () => {
    const api = listApi(() => page([]))
    const { wrapper, router } = await renderApp('/')

    await wrapper.get('[data-testid="tab-organized"]').trigger('click')
    await settle()
    expect(router.currentRoute.value.query).toEqual({ tab: 'organized' })
    expect(lastListQuery(api).get('scope')).toBe('organized')
    expect(lastListQuery(api).get('period')).toBe('upcoming')

    const past = wrapper
      .get('[data-testid="period"]')
      .findAll('button')
      .find((button) => button.text() === 'Прошедшие')
    await past?.trigger('click')
    await settle()

    expect(router.currentRoute.value.query).toEqual({ tab: 'organized', period: 'past' })
    expect(lastListQuery(api).get('period')).toBe('past')
  })

  it('ссылка с параметрами восстанавливает вкладку, период и категорию', async () => {
    const api = listApi(() => page([]))
    const { wrapper } = await renderApp('/?tab=joined&period=past&category=3')

    expect(wrapper.get('[data-testid="tab-joined"]').attributes('aria-selected')).toBe('true')
    const query = lastListQuery(api)
    expect([query.get('scope'), query.get('period'), query.get('category_id')]).toEqual([
      'joined',
      'past',
      '3',
    ])
    expect(wrapper.get('[data-testid="filter-category"]').text()).toContain('Спорт')
  })

  it('ответ на устаревший запрос не перезаписывает новый список', async () => {
    let releaseFirst: (response: Response) => void = () => undefined
    const api = listApi((request) => {
      if (query(request).get('scope') === 'all') {
        return new Promise<Response>((resolve) => {
          releaseFirst = resolve
        })
      }
      return page([eventItem({ id: 'mine', title: 'Моё' })])
    })
    const { wrapper } = await renderApp('/')

    await wrapper.get('[data-testid="tab-organized"]').trigger('click')
    await settle()
    releaseFirst(page([eventItem({ id: 'old', title: 'Чужое' })]))
    await settle()

    expect(api.calls('GET /events')).toHaveLength(2)
    expect(wrapper.text()).toContain('Моё')
    expect(wrapper.text()).not.toContain('Чужое')
  })
})

describe('Фильтры и состояние списка', () => {
  it('«Сбросить» удаляет фильтры из адреса и загружает список без них', async () => {
    const api = listApi(() => page([eventItem()]))
    const { wrapper, router } = await renderApp(
      '/?category=3&from=2026-12-01&to=2026-12-02&places=2',
    )
    expect(lastListQuery(api).get('category_id')).toBe('3')
    expect(lastListQuery(api).get('min_free_places')).toBe('2')

    await wrapper.get('[data-testid="filters-reset"]').trigger('click')
    await settle()

    expect(router.currentRoute.value.query).toEqual({})
    const query = lastListQuery(api)
    expect(['category_id', 'from', 'to', 'min_free_places'].some((key) => query.has(key))).toBe(
      false,
    )
  })

  it('на мобильном фильтры за кнопкой с числом активных', async () => {
    listApi(() => page([eventItem()]))
    setViewportWidth(360)
    const { wrapper } = await renderApp('/?category=3&from=2026-12-01&to=2026-12-02&places=2')

    expect(wrapper.find('[data-testid="event-filters"]').exists()).toBe(false)
    expect(wrapper.get('[data-testid="filters-button"]').text()).toContain('Фильтры (3)')
  })

  it('«Свободных мест от»: параметр в запросе и в адресе', async () => {
    const api = listApi(() => page([eventItem()]))
    const { wrapper, router } = await renderApp('/')

    wrapper
      .findAllComponents(InputNumber)
      .find((input) => input.attributes('data-testid') === 'filter-places')
      ?.vm.$emit('update:modelValue', 3)
    await settle()

    expect(router.currentRoute.value.query).toEqual({ places: '3' })
    expect(lastListQuery(api).get('min_free_places')).toBe('3')
  })

  it('один клик по дате — фильтр по этому дню, второй клик расширяет диапазон', async () => {
    const api = listApi(() => page([eventItem()]))
    const { wrapper, router } = await renderApp('/')
    const picker = () =>
      wrapper
        .findAllComponents(DatePicker)
        .find((input) => input.attributes('data-testid') === 'filter-dates')

    picker()?.vm.$emit('update:modelValue', [new Date(2026, 11, 1), null])
    await settle()

    expect(router.currentRoute.value.query).toEqual({ from: '2026-12-01', to: '2026-12-01' })
    expect(lastListQuery(api).get('from')).toBe('2026-12-01T00:00:00+03:00')
    expect(lastListQuery(api).get('to')).toBe('2026-12-02T00:00:00+03:00')
    // Календарь всё ещё ждёт конец диапазона
    expect(picker()?.props('modelValue')).toEqual([new Date(2026, 11, 1), null])

    picker()?.vm.$emit('update:modelValue', [new Date(2026, 11, 1), new Date(2026, 11, 3)])
    await settle()

    expect(router.currentRoute.value.query).toEqual({ from: '2026-12-01', to: '2026-12-03' })
    expect(lastListQuery(api).get('to')).toBe('2026-12-04T00:00:00+03:00')
  })
})

describe('Подгрузка списка', () => {
  it('«Показать ещё» добавляет следующую страницу и исчезает', async () => {
    const all = Array.from({ length: 25 }, (_, i) => eventItem({ id: `e${i}`, title: `М${i}` }))
    const api = listApi((request) => {
      const offset = Number(query(request).get('offset'))
      return page(all.slice(offset, offset + 20), all.length)
    })
    const { wrapper } = await renderApp('/')
    expect(wrapper.findAll('[data-testid="event-card"]')).toHaveLength(20)

    await wrapper.get('[data-testid="load-more"]').trigger('click')
    await settle()

    expect(lastListQuery(api).get('offset')).toBe('20')
    expect(wrapper.findAll('[data-testid="event-card"]')).toHaveLength(25)
    expect(wrapper.find('[data-testid="load-more"]').exists()).toBe(false)
  })

  it('ошибка загрузки: сообщение и «Повторить»', async () => {
    let fail = true
    listApi(() => (fail ? Promise.reject(new TypeError('offline')) : page([eventItem()])))
    const { wrapper } = await renderApp('/')

    expect(wrapper.get('[data-testid="events-error"]').text()).toContain('Повторить')

    fail = false
    await wrapper.get('[data-testid="events-error"] button').trigger('click')
    await settle()

    expect(wrapper.findAll('[data-testid="event-card"]')).toHaveLength(1)
  })
})

describe('Карточка мероприятия в списке', () => {
  it('категория, дата, место, места и ссылка', async () => {
    listApi(() => page([eventItem({ free_places: 3, max_participants: 10 })]))
    const { wrapper, router } = await renderApp('/')

    const card = wrapper.get('[data-testid="event-card"]')
    expect(card.text()).toContain('Настольные игры')
    expect(card.text()).toContain('вс, 1 ноября, 19:00')
    expect(card.text()).toContain('Антикафе «Циферблат»')
    expect(card.get('[data-testid="event-card-places"]').text()).toBe('Осталось 3 из 10 мест')
    expect(card.text()).not.toContain('0+')

    await card.trigger('click')
    await waitForPath(router, '/events/e1')
  })

  it('заполненное, 18+, «Вы записаны» и «Вы организатор»', async () => {
    listApi(() =>
      page([
        eventItem({ id: 'a', is_full: true, free_places: 0, min_age: 18, is_joined: true }),
        eventItem({
          id: 'b',
          is_joined: true,
          organizer: {
            id: completeProfile.id,
            name: 'Анна Иванова',
            photo_url: null,
            telegram: null,
          },
        }),
      ]),
    )
    const { wrapper } = await renderApp('/')

    const [full, mine] = wrapper.findAll('[data-testid="event-card"]')
    expect(full?.get('[data-testid="event-card-places"]').text()).toBe('Мест нет')
    expect(full?.text()).toContain('18+')
    expect(full?.find('[data-testid="event-card-joined"]').exists()).toBe(true)
    expect(mine?.find('[data-testid="event-card-organizer"]').exists()).toBe(true)
    expect(mine?.find('[data-testid="event-card-joined"]').exists()).toBe(false)
  })
})

describe('Пустые состояния списка', () => {
  it('«Организую» без мероприятий: текст и кнопка создания открывает окно', async () => {
    listApi(() => page([]))
    const { wrapper } = await renderApp('/?tab=organized')

    expect(wrapper.get('[data-testid="events-empty"]').text()).toContain(
      'Вы ещё не создали мероприятий',
    )
    await wrapper.get('[data-testid="empty-create"]').trigger('click')
    await settle()
    expect(bodyGet('[data-testid="create-event-dialog"]').textContent).toContain(
      'Новое мероприятие',
    )
  })

  it('«Участвую» без записей', async () => {
    listApi(() => page([]))
    const { wrapper } = await renderApp('/?tab=joined')
    expect(wrapper.get('[data-testid="events-empty"]').text()).toContain(
      'Вы пока никуда не записаны',
    )
  })

  it('ничего не найдено по фильтрам: «Сбросить фильтры»', async () => {
    const api = listApi(() => page([]))
    const { wrapper, router } = await renderApp('/?category=3')

    expect(wrapper.get('[data-testid="events-empty"]').text()).toContain(
      'Подходящих мероприятий нет',
    )
    await wrapper.get('[data-testid="empty-reset-filters"]').trigger('click')
    await settle()

    expect(router.currentRoute.value.query).toEqual({})
    expect(lastListQuery(api).has('category_id')).toBe(false)
  })
})
