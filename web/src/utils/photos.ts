import { ApiError } from '@/api/client'
import {
  MAX_PHOTO_BYTES,
  MAX_PHOTOS,
  PHOTO_TYPES,
  type PhotoOrderItem,
  type PhotoRef,
} from '@/api/events'
import { plural } from '@/utils/format'

/** Фото в форме: уже сохранённое (по id) или новый файл с локальным превью. */
export type PhotoDraft =
  | { kind: 'saved'; key: string; id: string }
  | { kind: 'new'; key: string; file: File; previewUrl: string }

export interface RejectedFile {
  name: string
  reason: string
}

export const PHOTO_TOO_LARGE = 'Файл больше 2 МБ'
export const PHOTO_BAD_TYPE = 'Поддерживаются JPEG, PNG и WebP'
export const PHOTO_LIMIT = `Не больше ${MAX_PHOTOS} фото`

export interface PhotoSelection {
  accepted: File[]
  rejected: RejectedFile[]
  /** Сколько подходящих файлов не поместилось в лимит. */
  overflow: number
}

/** Проверка выбранных файлов по правилам сервера (окончательно решает сервер). */
export function validatePhotoFiles(currentCount: number, files: readonly File[]): PhotoSelection {
  const accepted: File[] = []
  const rejected: RejectedFile[] = []
  let overflow = 0
  for (const file of files) {
    if (!PHOTO_TYPES.includes(file.type)) {
      rejected.push({ name: file.name, reason: PHOTO_BAD_TYPE })
    } else if (file.size > MAX_PHOTO_BYTES) {
      rejected.push({ name: file.name, reason: PHOTO_TOO_LARGE })
    } else if (currentCount + accepted.length >= MAX_PHOTOS) {
      overflow += 1
    } else {
      accepted.push(file)
    }
  }
  return { accepted, rejected, overflow }
}

export function overflowMessage(overflow: number): string {
  return `${PHOTO_LIMIT} — ${overflow} ${plural(overflow, ['файл', 'файла', 'файлов'])} не ${
    overflow === 1 ? 'добавлен' : 'добавлены'
  }`
}

export function savedDrafts(photos: readonly PhotoRef[]): PhotoDraft[] {
  return photos.map((photo) => ({ kind: 'saved', key: `saved:${photo.id}`, id: photo.id }))
}

/** Изменился ли набор фото относительно сохранённого. */
export function photosChanged(drafts: readonly PhotoDraft[], saved: readonly PhotoRef[]): boolean {
  if (drafts.length !== saved.length) return true
  return drafts.some((draft, index) => draft.kind !== 'saved' || draft.id !== saved[index]?.id)
}

/** Тело PUT /events/{id}/photos: итоговый порядок и новые файлы в порядке ссылок на них. */
export function buildPhotoPayload(drafts: readonly PhotoDraft[]): {
  order: PhotoOrderItem[]
  files: File[]
} {
  const files: File[] = []
  const order = drafts.map((draft): PhotoOrderItem => {
    if (draft.kind === 'saved') return { id: draft.id }
    files.push(draft.file)
    return { file: files.length - 1 }
  })
  return { order, files }
}

const SERVER_MESSAGES: Record<string, string> = {
  photo_too_large: PHOTO_TOO_LARGE,
  photo_invalid: PHOTO_BAD_TYPE,
  too_many_photos: PHOTO_LIMIT,
  photo_list_invalid: 'Набор фото изменился — откройте мероприятие заново',
}

export function isPhotoError(error: unknown): error is ApiError {
  return error instanceof ApiError && error.code in SERVER_MESSAGES
}

/** Текст ошибки сохранения фото для блока фото. */
export function photoErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    const known = SERVER_MESSAGES[error.code]
    if (known) return known
    if (error.code === 'event_started') return 'Мероприятие уже началось — фото не изменить'
    if (error.code === 'network_error') return 'Нет связи с сервером. Фото не сохранены'
  }
  return 'Не удалось сохранить фото. Попробуйте ещё раз'
}

/** Ключ плитки нового файла, к которому относится ошибка сервера (`detail.file`). */
export function draftKeyForFileError(drafts: readonly PhotoDraft[], error: unknown): string | null {
  if (!(error instanceof ApiError) || error.file === undefined) return null
  const newDrafts = drafts.filter((draft) => draft.kind === 'new')
  return newDrafts[error.file]?.key ?? null
}
