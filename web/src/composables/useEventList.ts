import { inject, provide, ref, watch, type InjectionKey, type Ref } from 'vue'

import { listEvents, PAGE_SIZE, type EventItem, type EventListParams } from '@/api/events'

/**
 * Список мероприятий с подгрузкой «Показать ещё». При смене параметров список
 * загружается заново, а ответы на устаревшие запросы игнорируются. Пока идёт новый
 * запрос, на экране остаются прежние карточки (`refreshing`), чтобы страница не
 * схлопывалась и не прыгала при каждом изменении фильтров и поиска.
 */
export function useEventList(params: Ref<EventListParams>) {
  const items = ref<EventItem[]>([])
  const total = ref(0)
  const loading = ref(false)
  /** Список загружается заново, а прежние карточки ещё показаны */
  const refreshing = ref(false)
  const error = ref(false)
  let requestId = 0

  async function load(offset: number): Promise<void> {
    const id = ++requestId
    loading.value = true
    refreshing.value = offset === 0 && items.value.length > 0
    error.value = false
    try {
      const page = await listEvents({ ...params.value, limit: PAGE_SIZE, offset })
      if (id !== requestId) return
      items.value = offset === 0 ? page.items : [...items.value, ...page.items]
      total.value = page.total
    } catch {
      if (id !== requestId) return
      // Прежние карточки относятся к другим параметрам — при ошибке их не показываем
      if (offset === 0) {
        items.value = []
        total.value = 0
      }
      error.value = true
    } finally {
      if (id === requestId) {
        loading.value = false
        refreshing.value = false
      }
    }
  }

  function reload(): Promise<void> {
    return load(0)
  }

  function loadMore(): Promise<void> {
    return load(items.value.length)
  }

  /** Мероприятие изменилось в окне — обновляем его карточку на месте, без перезагрузки. */
  function replaceItem(event: EventItem): void {
    items.value = items.value.map((item) => (item.id === event.id ? event : item))
  }

  function removeItem(id: string): void {
    const before = items.value.length
    items.value = items.value.filter((item) => item.id !== id)
    if (items.value.length < before) total.value = Math.max(total.value - 1, 0)
  }

  // Сравниваем по содержимому: при открытии окна (дочерний маршрут) объект параметров
  // пересоздаётся с теми же значениями, и список не должен перезагружаться
  watch(
    () => JSON.stringify(params.value),
    () => void reload(),
    { immediate: true },
  )

  return { items, total, loading, refreshing, error, reload, loadMore, replaceItem, removeItem }
}

export interface EventListUpdates {
  replaceItem: (event: EventItem) => void
  removeItem: (id: string) => void
}

const LIST_KEY: InjectionKey<EventListUpdates> = Symbol('event-list')

/** Список отдаёт окну мероприятия способ обновлять свои карточки. */
export function provideEventListUpdates(updates: EventListUpdates): void {
  provide(LIST_KEY, updates)
}

/** В окне без списка (тесты, другие страницы) обновления просто не нужны. */
export function injectEventListUpdates(): EventListUpdates {
  return inject(LIST_KEY, { replaceItem: () => undefined, removeItem: () => undefined })
}
