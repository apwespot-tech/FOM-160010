import { onScopeDispose, ref, toValue, watch, type MaybeRefOrGetter, type Ref } from 'vue'

import { fetchCategoryCover, fetchEventPhoto, type Category, type ImageSize } from '@/api/events'
import { fetchUserImage } from '@/api/profile'

/**
 * Кеш картинок по ключу: фото мероприятия (`photo:<id>:<size>`) и картинки категорий
 * (`cover:<cover_id>:<size>`). Картинка с данным id неизменяема, поэтому загруженное
 * содержимое переиспользуется, пока открыта вкладка; одновременные обращения делят запрос.
 */
const cache = new Map<string, Promise<string>>()
const objectUrls = new Set<string>()
let generation = 0

function loadCached(key: string, fetchBlob: () => Promise<Blob>): Promise<string> {
  const cached = cache.get(key)
  if (cached) return cached
  const started = generation
  const promise = fetchBlob().then(
    (blob) => {
      const url = URL.createObjectURL(blob)
      if (started !== generation) {
        // Кеш очистили (выход) пока шёл запрос — не сохраняем чужую картинку
        URL.revokeObjectURL(url)
        throw new Error('photo cache cleared')
      }
      objectUrls.add(url)
      return url
    },
    (error: unknown) => {
      // Ошибку не кешируем: следующий показ повторит запрос
      cache.delete(key)
      throw error
    },
  )
  cache.set(key, promise)
  return promise
}

export function loadPhotoUrl(
  eventId: string,
  photoId: string,
  size: ImageSize = 'full',
): Promise<string> {
  return loadCached(`photo:${photoId}:${size}`, () => fetchEventPhoto(eventId, photoId, size))
}

/** Аватар или обложка пользователя по id картинки. */
export function loadUserImageUrl(
  userId: string,
  imageId: string,
  size: ImageSize = 'thumb',
): Promise<string> {
  return loadCached(`user:${imageId}:${size}`, () => fetchUserImage(userId, imageId, size))
}

export function loadCategoryCoverUrl(
  category: Pick<Category, 'id' | 'cover_id'>,
  size: ImageSize = 'thumb',
): Promise<string> {
  return loadCached(`cover:${category.cover_id}:${size}`, () => fetchCategoryCover(category, size))
}

/** Освобождает все загруженные картинки (при выходе из аккаунта). */
export function clearPhotoCache(): void {
  generation += 1
  cache.clear()
  for (const url of objectUrls) URL.revokeObjectURL(url)
  objectUrls.clear()
  shown.clear()
}

export interface PhotoUrlState {
  url: Ref<string | null>
  failed: Ref<boolean>
}

/**
 * Уже показанные картинки по ключу компонента: заново смонтированная карточка
 * (обновление списка, смена фильтров) сразу получает ссылку, без кадра с пустым фоном.
 */
const shown = new Map<string, string>()

/** Локальная ссылка на картинку по загрузчику; пока грузится — null. */
export function useImageUrl(
  source: MaybeRefOrGetter<(() => Promise<string>) | null>,
  key: MaybeRefOrGetter<string | null>,
): PhotoUrlState {
  const url = ref<string | null>(null)
  const failed = ref(false)
  let active = true

  watch(
    () => toValue(key),
    (current) => {
      url.value = current ? (shown.get(current) ?? null) : null
      failed.value = false
      const load = toValue(source)
      if (!current || !load || url.value) return
      load().then(
        (value) => {
          shown.set(current, value)
          if (active && toValue(key) === current) url.value = value
        },
        () => {
          if (active && toValue(key) === current) failed.value = true
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

/** Локальная ссылка на фото мероприятия; пока грузится — null. */
export function usePhotoUrl(
  eventId: MaybeRefOrGetter<string>,
  photoId: MaybeRefOrGetter<string | null>,
  size: MaybeRefOrGetter<ImageSize> = 'full',
): PhotoUrlState {
  return useImageUrl(
    () => {
      const photo = toValue(photoId)
      return photo ? () => loadPhotoUrl(toValue(eventId), photo, toValue(size)) : null
    },
    () => {
      const photo = toValue(photoId)
      return photo ? `${toValue(eventId)}:${photo}:${toValue(size)}` : null
    },
  )
}
