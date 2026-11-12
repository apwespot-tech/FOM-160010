import { ref } from 'vue'

import { listCategories, type Category } from '@/api/events'

// Справочник меняется только миграциями — загружаем один раз за сессию
const categories = ref<Category[]>([])
let loading: Promise<void> | null = null

/** Категории мероприятий; при ошибке список пуст, следующий вызов попробует снова. */
export function useCategories() {
  loading ??= listCategories()
    .then((items) => {
      categories.value = items
    })
    .catch(() => {
      loading = null
    })
  return { categories }
}

/** Для тестов: сбросить кеш между сценариями. */
export function resetCategoriesCache(): void {
  categories.value = []
  loading = null
}
