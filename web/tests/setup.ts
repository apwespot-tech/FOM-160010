import { enableAutoUnmount } from '@vue/test-utils'
import { afterEach, beforeEach } from 'vitest'

import { resetCategoriesCache } from '@/composables/useCategories'
import { useCreateEventDialog } from '@/composables/useCreateEventDialog'
import { clearPhotoCache } from '@/composables/usePhotoUrl'

import { installMatchMedia, setViewportWidth } from './helpers/media'

enableAutoUnmount(afterEach)

// В jsdom нет ResizeObserver, а TabList PrimeVue следит им за полосой вкладок
class ResizeObserverStub {
  observe(): void {}
  unobserve(): void {}
  disconnect(): void {}
}
globalThis.ResizeObserver ??= ResizeObserverStub as unknown as typeof ResizeObserver

// В jsdom нет object URL — подменяем предсказуемыми ссылками
let objectUrlCounter = 0
URL.createObjectURL ??= () => `blob:mock/${++objectUrlCounter}`
URL.revokeObjectURL ??= () => undefined

beforeEach(() => {
  installMatchMedia()
  setViewportWidth(1280)
  localStorage.clear()
  // Модульное состояние живёт между тестами одного файла
  resetCategoriesCache()
  clearPhotoCache()
  useCreateEventDialog().close()
})
