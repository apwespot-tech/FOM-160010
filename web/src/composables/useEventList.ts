import { ref, watch, type Ref } from 'vue'

import { listEvents, PAGE_SIZE, type EventItem, type EventListParams } from '@/api/events'

/**
 * Список мероприятий с подгрузкой «Показать ещё». При смене параметров список
 * загружается заново, а ответы на устаревшие запросы игнорируются.
 */
export function useEventList(params: Ref<EventListParams>) {
  const items = ref<EventItem[]>([])
  const total = ref(0)
  const loading = ref(false)
  const error = ref(false)
  let requestId = 0

  async function load(offset: number): Promise<void> {
    const id = ++requestId
    loading.value = true
    error.value = false
    try {
      const page = await listEvents({ ...params.value, limit: PAGE_SIZE, offset })
      if (id !== requestId) return
      items.value = offset === 0 ? page.items : [...items.value, ...page.items]
      total.value = page.total
    } catch {
      if (id !== requestId) return
      error.value = true
    } finally {
      if (id === requestId) loading.value = false
    }
  }

  function reload(): Promise<void> {
    items.value = []
    total.value = 0
    return load(0)
  }

  function loadMore(): Promise<void> {
    return load(items.value.length)
  }

  watch(params, () => void reload(), { immediate: true, deep: true })

  return { items, total, loading, error, reload, loadMore }
}
