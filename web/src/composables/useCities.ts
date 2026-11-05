import { ref } from 'vue'

import { listCities, type City } from '@/api/events'

// Справочник меняется только миграциями — загружаем один раз за сессию
const cities = ref<City[]>([])
let loading: Promise<void> | null = null

/** Города по алфавиту; при ошибке список пуст, следующий вызов попробует снова. */
export function useCities() {
  loading ??= listCities()
    .then((items) => {
      cities.value = items
    })
    .catch(() => {
      loading = null
    })
  return { cities }
}

/** Для тестов: сбросить кеш между сценариями. */
export function resetCitiesCache(): void {
  cities.value = []
  loading = null
}
