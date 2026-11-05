import { apiFetch, apiFetchBlob } from './client'

export type MinAge = 0 | 14 | 16 | 18
export const MIN_AGE_VALUES: readonly MinAge[] = [0, 14, 16, 18]

export type EventScope = 'all' | 'joined' | 'organized'
export type EventPeriod = 'upcoming' | 'past'

export interface Category {
  id: number
  name: string
  /** Имя иконки primeicons, например `pi-video` */
  icon: string
  /** Картинка категории — обложка карточек мероприятий без фото */
  cover_id: string
}

export interface City {
  id: number
  name: string
}

/** Размер картинки: исходник или уменьшенная копия (WebP, ширина до 800 px). */
export type ImageSize = 'full' | 'thumb'

/** Человек в мероприятии. Telegram организатора — только записанным и администратору. */
export interface PersonRef {
  id: string
  name: string
  /** Аватар: GET /users/{id}/images/{avatar_id} */
  avatar_id: string | null
  telegram: string | null
}

export interface PhotoRef {
  id: string
}

export interface EventItem {
  id: string
  title: string
  description: string
  city: City
  place: string
  starts_at: string
  duration_minutes: number | null
  created_at: string
  category: Category
  max_participants: number
  min_age: MinAge
  organizer: PersonRef
  /** Фото по порядку, первое — основное. Содержимое — отдельным запросом по `id`. */
  photos: PhotoRef[]
  participants_count: number
  free_places: number
  is_full: boolean
  is_joined: boolean
}

export interface EventPage {
  items: EventItem[]
  total: number
}

export type Participant = PersonRef

export interface EventCreate {
  title: string
  description: string
  city_id: number
  place: string
  /** ISO 8601 с часовым поясом */
  starts_at: string
  duration_minutes: number | null
  category_id: number
  max_participants: number
  min_age: MinAge
}

export type EventPatch = Partial<EventCreate>

export interface EventListParams {
  scope?: EventScope
  period?: EventPeriod
  /** Не меньше N свободных мест */
  min_free_places?: number
  category_id?: number
  /** ISO 8601 с часовым поясом */
  from?: string
  to?: string
  limit?: number
  offset?: number
  /** Поиск по подстроке в названии */
  q?: string
}

export const PAGE_SIZE = 20

function toQuery(params: EventListParams): string {
  const query = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null) query.set(key, String(value))
  }
  const text = query.toString()
  return text ? `?${text}` : ''
}

export function listCities(): Promise<City[]> {
  return apiFetch('/cities', { auth: true })
}

export function listCategories(): Promise<Category[]> {
  return apiFetch('/categories', { auth: true })
}

export function listEvents(params: EventListParams = {}): Promise<EventPage> {
  return apiFetch(`/events${toQuery(params)}`, { auth: true })
}

export function getEvent(id: string): Promise<EventItem> {
  return apiFetch(`/events/${id}`, { auth: true })
}

export function createEvent(data: EventCreate): Promise<EventItem> {
  return apiFetch('/events', { method: 'POST', body: data, auth: true })
}

export function updateEvent(id: string, patch: EventPatch): Promise<EventItem> {
  return apiFetch(`/events/${id}`, { method: 'PATCH', body: patch, auth: true })
}

export function deleteEvent(id: string): Promise<void> {
  return apiFetch(`/events/${id}`, { method: 'DELETE', auth: true })
}

export function joinEvent(id: string): Promise<EventItem> {
  return apiFetch(`/events/${id}/join`, { method: 'POST', auth: true })
}

export function leaveEvent(id: string): Promise<EventItem> {
  return apiFetch(`/events/${id}/leave`, { method: 'POST', auth: true })
}

export function listParticipants(id: string): Promise<Participant[]> {
  return apiFetch(`/events/${id}/participants`, { auth: true })
}

export function removeParticipant(id: string, userId: string): Promise<EventItem> {
  return apiFetch(`/events/${id}/participants/${userId}/remove`, { method: 'POST', auth: true })
}

/** Элемент итогового порядка фото: сохранённое фото или n-й новый файл запроса. */
export type PhotoOrderItem = { id: string } | { file: number }

export const MAX_PHOTOS = 10
export const MAX_PHOTO_BYTES = 2 * 1024 * 1024
export const PHOTO_TYPES: readonly string[] = ['image/jpeg', 'image/png', 'image/webp']

/** Заменяет набор фото целиком: порядок из сохранённых `id` и новых файлов. */
export function replaceEventPhotos(
  id: string,
  order: PhotoOrderItem[],
  files: File[],
): Promise<EventItem> {
  const body = new FormData()
  body.append('order', JSON.stringify(order))
  for (const file of files) body.append('files', file, file.name)
  return apiFetch(`/events/${id}/photos`, { method: 'PUT', body, auth: true })
}

function sizeQuery(size: ImageSize): string {
  return size === 'thumb' ? '?size=thumb' : ''
}

export function photoPath(eventId: string, photoId: string, size: ImageSize = 'full'): string {
  return `/events/${eventId}/photos/${photoId}${sizeQuery(size)}`
}

export function fetchEventPhoto(
  eventId: string,
  photoId: string,
  size: ImageSize = 'full',
): Promise<Blob> {
  return apiFetchBlob(photoPath(eventId, photoId, size), { auth: true })
}

/** Адрес содержит cover_id: новая картинка категории — новый адрес, кеш бессрочный. */
export function categoryCoverPath(
  category: Pick<Category, 'id' | 'cover_id'>,
  size: ImageSize = 'full',
): string {
  return `/categories/${category.id}/covers/${category.cover_id}${sizeQuery(size)}`
}

export function fetchCategoryCover(
  category: Pick<Category, 'id' | 'cover_id'>,
  size: ImageSize = 'full',
): Promise<Blob> {
  return apiFetchBlob(categoryCoverPath(category, size), { auth: true })
}
