import DatePicker from 'primevue/datepicker'
import InputNumber from 'primevue/inputnumber'
import Select from 'primevue/select'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { EventItem } from '@/api/events'
import type { Profile } from '@/api/profile'
import { buildListQuery, parseListQuery, toListParams } from '@/composables/useEventListQuery'

import {
  categories,
  cities,
  completeProfile,
  errorResponse,
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

// Справочник по алфавиту, как его отдаёт сервер
const sortedCities = [...cities].sort((a, b) => a.name.localeCompare(b.name, 'ru'))

function listApi(
  handler: (request: MockRequest) => Response | Promise<Response>,
  profile: Profile = completeProfile,
) {
  const api = mockApi({
    'GET /events': handler,
    'GET /categories': () => jsonResponse(200, categories),
    'GET /cities': () => jsonResponse(200, sortedCities),
  })
  withStoredSession(api, profile)
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
      cityId: null,
      categoryId: null,
      from: null,
      to: null,
      minFreePlaces: null,
      search: '',
    })
    expect(toListParams(state)).toEqual({ scope: 'all' })
  })

  it('значения по умолчанию в адрес не пишутся', () => {
    expect(
      buildListQuery({
        tab: 'find',
        period: 'upcoming',
        cityId: null,
        categoryId: null,
        from: null,
        to: null,
        minFreePlaces: null,
        search: '  ',
      }),
    ).toEqual({})
    expect(
      buildListQuery({
        tab: 'organized',
        period: 'past',
        cityId: 5,
        categoryId: 2,
        from: null,
        to: null,
        minFreePlaces: 4,
        search: ' йога ',
      }),
    ).toEqual({
      tab: 'organized',
      period: 'past',
      city: '5',
      category: '2',
      places: '4',
      q: 'йога',
    })
  })

  it('город: на всех вкладках уходит в city_id, некорректный отбрасывается', () => {
    expect(parseListQuery({ city: '5' }).cityId).toBe(5)
    expect(toListParams(parseListQuery({ city: '5' }))).toEqual({ scope: 'all', city_id: 5 })
    expect(toListParams(parseListQuery({ tab: 'joined', city: '5' }))).toEqual({
      scope: 'joined',
      period: 'upcoming',
      city_id: 5,
    })
    expect(toListParams(parseListQuery({ tab: 'organized', city: '5' }))).toMatchObject({
      scope: 'organized',
      city_id: 5,
    })
    for (const city of ['abc', '0', '-1', '2.5']) {
      expect(parseListQuery({ city }).cityId).toBeNull()
    }
  })

  it('поиск: обрезка пробелов, слишком длинный отбрасывается', () => {
    expect(parseListQuery({ q: '  мафия ' }).search).toBe('мафия')
    expect(toListParams(parseListQuery({ q: ' мафия ' }))).toEqual({ scope: 'all', q: 'мафия' })
    expect(parseListQuery({ q: 'а'.repeat(100) }).search).toHaveLength(100)
    expect(parseListQuery({ q: 'а'.repeat(101) }).search).toBe('')
    expect(toListParams(parseListQuery({ q: '   ' }))).toEqual({ scope: 'all' })
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
      '/?city=5&category=3&from=2026-12-01&to=2026-12-02&places=2',
    )
    expect(lastListQuery(api).get('city_id')).toBe('5')
    expect(lastListQuery(api).get('category_id')).toBe('3')
    expect(lastListQuery(api).get('min_free_places')).toBe('2')

    await wrapper.get('[data-testid="filters-reset"]').trigger('click')
    await settle()

    expect(router.currentRoute.value.query).toEqual({})
    const query = lastListQuery(api)
    expect(
      ['city_id', 'category_id', 'from', 'to', 'min_free_places'].some((key) => query.has(key)),
    ).toBe(false)
  })

  it('на мобильном фильтры за кнопкой с числом активных', async () => {
    listApi(() => page([eventItem()]))
    setViewportWidth(360)
    const { wrapper } = await renderApp('/?city=5&category=3&places=2')

    // Поиск и быстрые фильтры видны, остальные поля — в окне «Фильтры»
    expect(wrapper.find('[data-testid="filter-search"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="quick-free-places"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="filter-category"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="filter-city"]').exists()).toBe(false)
    expect(wrapper.get('[data-testid="filters-button"]').text()).toContain('Фильтры (3)')

    await wrapper.get('[data-testid="filters-button"]').trigger('click')
    await settle()
    expect(bodyGet('[data-testid="filter-city-mobile"]').textContent).toContain('Казань')
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
            avatar_id: null,
            telegram: null,
            rating: null,
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

// --- новый каталог: заголовок, поиск, быстрые фильтры, «Сбросить» ---

function typeSearch(wrapper: Awaited<ReturnType<typeof renderApp>>['wrapper'], text: string) {
  const input = wrapper.get('[data-testid="filter-search"]').element as HTMLInputElement
  input.value = text
  input.dispatchEvent(new Event('input', { bubbles: true }))
}

describe('Заголовок списка мероприятий', () => {
  it('над вкладками — «Мероприятия» и подзаголовок', async () => {
    listApi(() => page([]))
    const { wrapper } = await renderApp('/')

    expect(wrapper.get('h1').text()).toBe('Мероприятия')
    expect(wrapper.get('[data-testid="events-subtitle"]').text()).toBe(
      'Присоединяйтесь к событиям или создавайте свои для поиска компании',
    )
  })
})

describe('Поиск по названию в списке', () => {
  afterEach(() => {
    vi.useRealTimers()
  })

  it('быстрый ввод — один запрос через 300 мс, q в адресе', async () => {
    const api = listApi(() => page([]))
    const { wrapper, router } = await renderApp('/')
    const before = api.calls('GET /events').length
    vi.useFakeTimers({ toFake: ['setTimeout', 'clearTimeout'] })

    for (const text of ['м', 'ма', 'маф', 'мафи', 'мафия']) {
      typeSearch(wrapper, text)
      vi.advanceTimersByTime(100)
    }
    await settle()
    expect(api.calls('GET /events')).toHaveLength(before)

    vi.advanceTimersByTime(300)
    vi.useRealTimers()
    await settle()

    expect(api.calls('GET /events')).toHaveLength(before + 1)
    expect(lastListQuery(api).get('q')).toBe('мафия')
    expect(router.currentRoute.value.query.q).toBe('мафия')
  })

  it('очистка и пробелы снимают поиск', async () => {
    const api = listApi(() => page([]))
    const { wrapper, router } = await renderApp('/?q=мафия')
    expect(lastListQuery(api).get('q')).toBe('мафия')
    expect((wrapper.get('[data-testid="filter-search"]').element as HTMLInputElement).value).toBe(
      'мафия',
    )
    vi.useFakeTimers({ toFake: ['setTimeout', 'clearTimeout'] })

    typeSearch(wrapper, '   ')
    vi.advanceTimersByTime(300)
    vi.useRealTimers()
    await settle()

    expect(lastListQuery(api).has('q')).toBe(false)
    expect(router.currentRoute.value.query.q).toBeUndefined()
  })

  it('ссылка восстанавливает поиск вместе с фильтрами', async () => {
    const api = listApi(() => page([]))
    await renderApp('/?tab=joined&period=past&category=3&q=йога')

    const query = lastListQuery(api)
    expect(query.get('scope')).toBe('joined')
    expect(query.get('period')).toBe('past')
    expect(query.get('category_id')).toBe('3')
    expect(query.get('q')).toBe('йога')
  })
})

describe('Быстрые фильтры', () => {
  // Среда, 4 ноября 2026, 15:00 МСК
  const WEDNESDAY = new Date('2026-11-04T12:00:00Z')

  afterEach(() => {
    vi.useRealTimers()
  })

  function chip(wrapper: Awaited<ReturnType<typeof renderApp>>['wrapper'], testId: string) {
    return wrapper.get(`[data-testid="${testId}"]`)
  }

  it('«Есть свободные места» -> min_free_places=1 и подсветка', async () => {
    const api = listApi(() => page([]))
    const { wrapper, router } = await renderApp('/')

    await chip(wrapper, 'quick-free-places').trigger('click')
    await settle()

    expect(lastListQuery(api).get('min_free_places')).toBe('1')
    expect(router.currentRoute.value.query.places).toBe('1')
    expect(chip(wrapper, 'quick-free-places').attributes('aria-pressed')).toBe('true')
  })

  it('ручной ввод 3 гасит «Есть свободные места»', async () => {
    const api = listApi(() => page([]))
    const { wrapper } = await renderApp('/?places=1')
    expect(chip(wrapper, 'quick-free-places').attributes('aria-pressed')).toBe('true')

    wrapper
      .findAllComponents(InputNumber)
      .find((input) => input.attributes('data-testid') === 'filter-places')
      ?.vm.$emit('update:modelValue', 3)
    await settle()

    expect(lastListQuery(api).get('min_free_places')).toBe('3')
    expect(chip(wrapper, 'quick-free-places').attributes('aria-pressed')).toBe('false')
  })

  it('«На этой неделе» в среду — с 4 по 8 ноября, повторное нажатие очищает даты', async () => {
    vi.useFakeTimers({ toFake: ['Date'] })
    vi.setSystemTime(WEDNESDAY)
    const api = listApi(() => page([]))
    const { wrapper, router } = await renderApp('/')

    await chip(wrapper, 'quick-this-week').trigger('click')
    await settle()

    expect(router.currentRoute.value.query).toMatchObject({ from: '2026-11-04', to: '2026-11-08' })
    expect(lastListQuery(api).get('from')).toBe('2026-11-04T00:00:00+03:00')
    expect(lastListQuery(api).get('to')).toBe('2026-11-09T00:00:00+03:00')
    expect(chip(wrapper, 'quick-this-week').attributes('aria-pressed')).toBe('true')

    await chip(wrapper, 'quick-this-week').trigger('click')
    await settle()

    expect(router.currentRoute.value.query.from).toBeUndefined()
    expect(lastListQuery(api).has('from')).toBe(false)
  })

  it('«Сбросить» очищает поиск и фильтры и скрывается', async () => {
    const api = listApi(() => page([]))
    const { wrapper, router } = await renderApp('/?q=йога&category=3&from=2026-12-01&to=2026-12-02')

    await wrapper.get('[data-testid="filters-reset"]').trigger('click')
    await settle()

    expect(router.currentRoute.value.query).toEqual({})
    const query = lastListQuery(api)
    expect(['q', 'category_id', 'from', 'to'].some((key) => query.has(key))).toBe(false)
    expect((wrapper.get('[data-testid="filter-search"]').element as HTMLInputElement).value).toBe(
      '',
    )
    expect(wrapper.find('[data-testid="filters-reset"]').exists()).toBe(false)
  })

  it('без поиска и фильтров «Сбросить» нет', async () => {
    listApi(() => page([]))
    const { wrapper } = await renderApp('/')

    expect(wrapper.find('[data-testid="filters-reset"]').exists()).toBe(false)
  })
})

describe('Обновление списка без скачков', () => {
  afterEach(() => {
    vi.useRealTimers()
  })

  it('при поиске прежние карточки остаются до ответа, спиннера нет', async () => {
    let release: (() => void) | null = null
    const api = listApi((request) => {
      if (!query(request).has('q')) return page([eventItem({ id: 'a', title: 'Первое' })])
      // Ответ на поиск придёт, когда тест разрешит
      return new Promise<Response>((resolve) => {
        release = () => resolve(page([eventItem({ id: 'b', title: 'Мафия' })]))
      })
    })
    const { wrapper } = await renderApp('/')
    expect(wrapper.findAll('[data-testid="event-card"]')).toHaveLength(1)
    vi.useFakeTimers({ toFake: ['setTimeout', 'clearTimeout'] })

    typeSearch(wrapper, 'маф')
    vi.advanceTimersByTime(300)
    vi.useRealTimers()
    await settle()

    // Запрос ушёл, но карточки на месте, приглушены, спиннера нет
    expect(lastListQuery(api).get('q')).toBe('маф')
    const list = wrapper.get('[data-testid="event-list"]')
    expect(list.attributes('aria-busy')).toBe('true')
    expect(list.classes()).toContain('events-page__list--refreshing')
    expect(wrapper.findAll('[data-testid="event-card"] h2').map((h) => h.text())).toEqual([
      'Первое',
    ])
    expect(wrapper.find('[data-testid="events-loading"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="events-empty"]').exists()).toBe(false)

    release!()
    await settle()

    expect(wrapper.findAll('[data-testid="event-card"] h2').map((h) => h.text())).toEqual(['Мафия'])
    expect(wrapper.get('[data-testid="event-list"]').attributes('aria-busy')).toBe('false')
  })

  it('первая загрузка — со спиннером', async () => {
    let release: (() => void) | null = null
    listApi(
      () =>
        new Promise<Response>((resolve) => {
          release = () => resolve(page([eventItem()]))
        }),
    )
    const { wrapper } = await renderApp('/')

    expect(wrapper.find('[data-testid="events-loading"]').exists()).toBe(true)
    release!()
    await settle()
    expect(wrapper.find('[data-testid="events-loading"]').exists()).toBe(false)
  })

  it('ошибка при обновлении — прежние карточки убираются, показывается ошибка', async () => {
    const api = listApi((request) =>
      query(request).has('q') ? errorResponse(500, 'oops') : page([eventItem()]),
    )
    const { wrapper } = await renderApp('/')
    vi.useFakeTimers({ toFake: ['setTimeout', 'clearTimeout'] })

    typeSearch(wrapper, 'маф')
    vi.advanceTimersByTime(300)
    vi.useRealTimers()
    await settle()

    expect(lastListQuery(api).get('q')).toBe('маф')
    expect(wrapper.findAll('[data-testid="event-card"]')).toHaveLength(0)
    expect(wrapper.find('[data-testid="events-error"]').exists()).toBe(true)
  })
})

describe('Фильтр по городу в списке', () => {
  type CityOption = { id: number | null; name: string; own: boolean }
  type App = Awaited<ReturnType<typeof renderApp>>

  function citySelect(wrapper: App['wrapper']) {
    const select = wrapper
      .findAllComponents(Select)
      .find((item) => item.attributes('data-testid') === 'filter-city')
    if (!select) throw new Error('Нет поля «Город»')
    return select
  }

  function optionNames(wrapper: App['wrapper']): string[] {
    return (citySelect(wrapper).props('options') as CityOption[]).map((option) =>
      option.own ? option.name + ' (ваш город)' : option.name,
    )
  }

  function renderedOptions(): string[] {
    return [
      ...document.body.querySelectorAll<HTMLElement>('[data-testid="filter-city-option"]'),
    ].map((option) => (option.textContent ?? '').replace(/\s+/g, ' ').trim())
  }

  it('по умолчанию «Все города»: запрос без city_id, в адресе нет city', async () => {
    const api = listApi(() => page([eventItem()]))
    const { wrapper, router } = await renderApp('/')

    expect(citySelect(wrapper).text()).toContain('Все города')
    expect(lastListQuery(api).has('city_id')).toBe(false)
    expect(router.currentRoute.value.query).toEqual({})
  })

  it('город из профиля вторым после «Все города», без повтора', async () => {
    listApi(() => page([eventItem()]))
    const { wrapper } = await renderApp('/')

    expect(optionNames(wrapper)).toEqual([
      'Все города',
      'Москва (ваш город)',
      'Казань',
      'Санкт-Петербург',
    ])
  })

  it('без города в профиле — все города по алфавиту', async () => {
    listApi(() => page([eventItem()]), { ...completeProfile, city: null })
    const { wrapper } = await renderApp('/')

    expect(optionNames(wrapper)).toEqual(['Все города', 'Казань', 'Москва', 'Санкт-Петербург'])
  })

  it('подпись «ваш город» в выпадающем списке', async () => {
    listApi(() => page([eventItem()]))
    const { wrapper } = await renderApp('/')

    citySelect(wrapper).vm.show()
    await settle()

    expect(renderedOptions().slice(0, 3)).toEqual(['Все города', 'Москва ваш город', 'Казань'])
  })

  it('выбор города и возврат ко всем городам', async () => {
    const api = listApi(() => page([eventItem()]))
    const { wrapper, router } = await renderApp('/')

    citySelect(wrapper).vm.$emit('update:modelValue', 5)
    await settle()
    expect(router.currentRoute.value.query).toEqual({ city: '5' })
    expect(lastListQuery(api).get('city_id')).toBe('5')
    expect(wrapper.find('[data-testid="filters-reset"]').exists()).toBe(true)

    citySelect(wrapper).vm.$emit('update:modelValue', null)
    await settle()
    expect(router.currentRoute.value.query).toEqual({})
    expect(lastListQuery(api).has('city_id')).toBe(false)
  })

  it('поиск в списке городов без учёта регистра', async () => {
    listApi(() => page([eventItem()]))
    const { wrapper } = await renderApp('/')

    expect(citySelect(wrapper).props('filter')).toBe(true)
    citySelect(wrapper).vm.show()
    await settle()
    const input = bodyGet('.p-select-filter') as HTMLInputElement
    input.value = 'каз'
    input.dispatchEvent(new Event('input'))
    await settle()

    expect(renderedOptions()).toEqual(['Казань'])
  })

  it('город сохраняется при переходе на вкладку «Участвую»', async () => {
    const api = listApi(() => page([eventItem()]))
    const { wrapper, router } = await renderApp('/?city=5')

    await wrapper.get('[data-testid="tab-joined"]').trigger('click')
    await settle()

    expect(router.currentRoute.value.query).toEqual({ tab: 'joined', city: '5' })
    expect(lastListQuery(api).get('scope')).toBe('joined')
    expect(lastListQuery(api).get('city_id')).toBe('5')
    expect(citySelect(wrapper).text()).toContain('Казань')
  })

  it('ссылка с городом на вкладке «Организую»', async () => {
    const api = listApi(() => page([eventItem()]))
    const { wrapper } = await renderApp('/?tab=organized&city=5')

    expect(lastListQuery(api).get('scope')).toBe('organized')
    expect(lastListQuery(api).get('city_id')).toBe('5')
    expect(citySelect(wrapper).text()).toContain('Казань')
  })

  it('некорректный город в адресе игнорируется', async () => {
    const api = listApi(() => page([eventItem()]))
    const { wrapper } = await renderApp('/?city=abc')

    expect(citySelect(wrapper).text()).toContain('Все города')
    expect(lastListQuery(api).has('city_id')).toBe(false)
  })

  it('несуществующие город и категория в адресе сбрасываются', async () => {
    const api = listApi(() => page([eventItem()]))
    const { wrapper, router } = await renderApp('/?city=999&category=999')
    await settle()

    expect(citySelect(wrapper).text()).toContain('Все города')
    expect(lastListQuery(api).has('city_id')).toBe(false)
    expect(lastListQuery(api).has('category_id')).toBe(false)
    expect(router.currentRoute.value.query).toEqual({})
  })
})
