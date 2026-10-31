import { apiFetch } from './client'

export type MinAge = 0 | 14 | 16 | 18
export const MIN_AGE_VALUES: readonly MinAge[] = [0, 14, 16, 18]

export type EventScope = 'all' | 'joined' | 'organized'
export type EventPeriod = 'upcoming' | 'past'

export interface Category {
  id: number
  name: string
}

export interface PersonRef {
  id: string
  name: string
}

export interface EventItem {
  id: string
  title: string
  description: string
  place: string
  starts_at: string
  duration_minutes: number | null
  category: Category
  max_participants: number
  min_age: MinAge
  organizer: PersonRef
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
