import { onScopeDispose, ref, toValue, watch, type MaybeRefOrGetter, type Ref } from 'vue'

import { fetchEventPhoto } from '@/api/events'

/**
 * Кеш фото по id. Фото неизменяемо, поэтому загруженное содержимое переиспользуется,
 * пока открыта вкладка. Одновременные обращения к одному id делят один запрос.
 */
const cache = new Map<string, Promise<string>>()
const objectUrls = new Set<string>()
let generation = 0

export function loadPhotoUrl(eventId: string, photoId: string): Promise<string> {
  const cached = cache.get(photoId)
  if (cached) return cached
  const started = generation
  const promise = fetchEventPhoto(eventId, photoId).then(
    (blob) => {
      const url = URL.createObjectURL(blob)
      if (started !== generation) {
        // Кеш очистили (выход) пока шёл запрос — не сохраняем чужое фото
        URL.revokeObjectURL(url)
        throw new Error('photo cache cleared')
      }
      objectUrls.add(url)
      return url
    },
    (error: unknown) => {
      // Ошибку не кешируем: следующий показ повторит запрос
      cache.delete(photoId)
      throw error
    },
  )
  cache.set(photoId, promise)
  return promise
}

/** Освобождает все загруженные фото (при выходе из аккаунта). */
export function clearPhotoCache(): void {
  generation += 1
  cache.clear()
  for (const url of objectUrls) URL.revokeObjectURL(url)
  objectUrls.clear()
}

export interface PhotoUrlState {
  url: Ref<string | null>
  failed: Ref<boolean>
}

/** Локальная ссылка на фото мероприятия; пока грузится — null. */
export function usePhotoUrl(
  eventId: MaybeRefOrGetter<string>,
  photoId: MaybeRefOrGetter<string | null>,
): PhotoUrlState {
  const url = ref<string | null>(null)
  const failed = ref(false)
  let active = true

  watch(
    () => [toValue(eventId), toValue(photoId)] as const,
    ([event, photo]) => {
      url.value = null
      failed.value = false
      if (!photo) return
      loadPhotoUrl(event, photo).then(
        (value) => {
          if (active && toValue(photoId) === photo) url.value = value
        },
        () => {
          if (active && toValue(photoId) === photo) failed.value = true
        },
      )
    },
    { immediate: true },
  )
  onScopeDispose(() => {
    active = false
  })

  return { url, failed }
}
