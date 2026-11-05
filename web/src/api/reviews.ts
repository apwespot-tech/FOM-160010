import { apiFetch } from './client'

/** Вид отзыва — по роли получателя на мероприятии. */
export type ReviewKind = 'organizer' | 'participant'

export const REVIEW_TEXT_MAX_LENGTH = 1000
export const REVIEWS_PAGE_SIZE = 20

/** Средняя оценка (null, если отзывов меньше трёх) и число отзывов. */
export interface Rating {
  average: number | null
  count: number
}

export interface ProfileRatings {
  as_organizer: Rating
  as_participant: Rating
}

export interface ReviewAuthor {
  id: string
  name: string
  avatar_id: string | null
}

export interface Review {
  id: string
  /** id = null, если мероприятие удалено */
  event: { id: string | null; title: string }
  target_id: string
  kind: ReviewKind
  stars: number
  text: string | null
  anonymous: boolean
  /** null у анонимного отзыва, если смотрит не администратор и не автор */
  author: ReviewAuthor | null
  created_at: string
  updated_at: string
}

export interface ReviewCreate {
  target_id: string
  stars: number
  text?: string | null
  anonymous?: boolean
}

export type ReviewPatch = Partial<Omit<ReviewCreate, 'target_id'>>

/** Свои отзывы по мероприятию и границы окна отзывов. */
export interface MyReviews {
  items: Review[]
  opens_at: string
  closes_at: string
}

export interface ReviewPage {
  items: Review[]
  total: number
}

export function createReview(eventId: string, data: ReviewCreate): Promise<Review> {
  return apiFetch(`/events/${eventId}/reviews`, { method: 'POST', body: data, auth: true })
}

export function getMyReviews(eventId: string): Promise<MyReviews> {
  return apiFetch(`/events/${eventId}/reviews/mine`, { auth: true })
}

export function updateReview(id: string, patch: ReviewPatch): Promise<Review> {
  return apiFetch(`/reviews/${id}`, { method: 'PATCH', body: patch, auth: true })
}

export function deleteReview(id: string): Promise<void> {
  return apiFetch(`/reviews/${id}`, { method: 'DELETE', auth: true })
}

export function listUserReviews(
  userId: string,
  kind: ReviewKind,
  offset = 0,
  limit = REVIEWS_PAGE_SIZE,
): Promise<ReviewPage> {
  const query = new URLSearchParams({ kind, limit: String(limit), offset: String(offset) })
  return apiFetch(`/users/${userId}/reviews?${query.toString()}`, { auth: true })
}
