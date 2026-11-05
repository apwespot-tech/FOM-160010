import { computed } from 'vue'
import { useRoute, useRouter, type LocationQuery, type LocationQueryRaw } from 'vue-router'

import type { EventListParams, EventPeriod, EventScope } from '@/api/events'
import { dateRangeToParams, fromIsoDate, toIsoDate } from '@/utils/dates'

export type EventTab = 'find' | 'joined' | 'organized'

export interface EventListState {
  tab: EventTab
  period: EventPeriod
  /** Город; null — все города */
  cityId: number | null
  categoryId: number | null
  from: Date | null
  to: Date | null
  /** Не меньше N свободных мест */
  minFreePlaces: number | null
  /** Поиск по названию (без пробелов по краям); пустая строка — без поиска */
  search: string
}

const TAB_SCOPE: Record<EventTab, EventScope> = {
  find: 'all',
  joined: 'joined',
  organized: 'organized',
}
const ISO_DATE_RE = /^\d{4}-\d{2}-\d{2}$/
export const MAX_FREE_PLACES = 100
export const MAX_SEARCH_LENGTH = 100

function single(value: LocationQuery[string] | undefined): string | null {
  const raw = Array.isArray(value) ? value[0] : value
  return typeof raw === 'string' ? raw : null
}

function parseDate(value: string | null): Date | null {
  return value && ISO_DATE_RE.test(value) ? fromIsoDate(value) : null
}

/** Адрес -> состояние списка; некорректные значения отбрасываются. */
export function parseListQuery(query: LocationQuery): EventListState {
  const rawTab = single(query.tab)
  const tab: EventTab = rawTab === 'joined' || rawTab === 'organized' ? rawTab : 'find'
  const period: EventPeriod =
    tab !== 'find' && single(query.period) === 'past' ? 'past' : 'upcoming'
  const city = Number(single(query.city))
  const category = Number(single(query.category))
  const places = Number(single(query.places))
  const search = (single(query.q) ?? '').trim()
  return {
    tab,
    period,
    cityId: Number.isInteger(city) && city > 0 ? city : null,
    categoryId: Number.isInteger(category) && category > 0 ? category : null,
    from: parseDate(single(query.from)),
    to: parseDate(single(query.to)),
    minFreePlaces:
      Number.isInteger(places) && places >= 1 && places <= MAX_FREE_PLACES ? places : null,
    search: search.length <= MAX_SEARCH_LENGTH ? search : '',
  }
}

/** Состояние -> адрес: значения по умолчанию не пишутся. */
export function buildListQuery(state: EventListState): LocationQueryRaw {
  const query: LocationQueryRaw = {}
  if (state.tab !== 'find') query.tab = state.tab
  if (state.tab !== 'find' && state.period === 'past') query.period = 'past'
  if (state.cityId !== null) query.city = String(state.cityId)
  if (state.categoryId !== null) query.category = String(state.categoryId)
  if (state.from) query.from = toIsoDate(state.from)
  if (state.to) query.to = toIsoDate(state.to)
  if (state.minFreePlaces !== null) query.places = String(state.minFreePlaces)
  const search = state.search.trim()
  if (search) query.q = search
  return query
}

/** Состояние -> параметры GET /events (без пагинации). */
export function toListParams(state: EventListState): EventListParams {
  const params: EventListParams = { scope: TAB_SCOPE[state.tab] }
  if (state.tab !== 'find') params.period = state.period
  if (state.minFreePlaces !== null) params.min_free_places = state.minFreePlaces
  if (state.cityId !== null) params.city_id = state.cityId
  if (state.categoryId !== null) params.category_id = state.categoryId
  const range = dateRangeToParams(state.from, state.to)
  if (range.from) params.from = range.from
  if (range.to) params.to = range.to
  const search = state.search.trim()
  if (search) params.q = search
  return params
}

/** Вкладка, период и фильтры главной страницы, хранящиеся в адресе. */
export function useEventListQuery() {
  const route = useRoute()
  const router = useRouter()

  const state = computed(() => parseListQuery(route.query))
  const params = computed(() => toListParams(state.value))
  const activeFilters = computed(
    () =>
      (state.value.cityId !== null ? 1 : 0) +
      (state.value.categoryId !== null ? 1 : 0) +
      (state.value.from || state.value.to ? 1 : 0) +
      (state.value.minFreePlaces !== null ? 1 : 0),
  )
  /** Активен поиск или хотя бы один фильтр: показывается «Сбросить». */
  const hasActive = computed(() => activeFilters.value > 0 || state.value.search !== '')

  function update(patch: Partial<EventListState>): void {
    const next = { ...state.value, ...patch }
    // Новая вкладка открывается с предстоящими
    if (patch.tab && patch.tab !== state.value.tab && patch.period === undefined) {
      next.period = 'upcoming'
    }
    void router.replace({ query: buildListQuery(next) })
  }

  function resetFilters(): void {
    update({
      cityId: null,
      categoryId: null,
      from: null,
      to: null,
      minFreePlaces: null,
      search: '',
    })
  }

  return { state, params, activeFilters, hasActive, update, resetFilters }
}
