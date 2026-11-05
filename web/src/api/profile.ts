import { apiFetch, apiFetchBlob } from './client'
import type { City, ImageSize } from './events'

export type Role = 'participant' | 'organizer' | 'admin'

/** Интерес — категория мероприятий с иконкой primeicons. */
export interface Interest {
  id: number
  name: string
  icon: string
}

export interface ProfileStats {
  /** Мероприятия, где пользователь автор (предстоящие и прошедшие) */
  organized_count: number
  /** Прошедшие чужие мероприятия, на которые пользователь записан */
  attended_count: number
}

export interface Profile {
  id: string
  phone: string
  name: string | null
  birth_date: string | null
  age: number | null
  email: string | null
  telegram: string | null
  about: string | null
  city: City | null
  interests: Interest[]
  /** Картинки профиля: GET /users/{id}/images/{image_id} */
  avatar_id: string | null
  cover_id: string | null
  created_at: string
  stats: ProfileStats
  roles: Role[]
  profile_completed: boolean
}

export interface ProfilePatch {
  name?: string
  birth_date?: string
  email?: string | null
  telegram?: string | null
  about?: string | null
  city_id?: number | null
  /** Новый набор интересов целиком */
  interest_ids?: number[]
}

export type ProfileImageKind = 'avatar' | 'cover'

export const ABOUT_MAX_LENGTH = 500

export function getProfile(): Promise<Profile> {
  return apiFetch('/profile', { auth: true })
}

/** Чужой профиль: виден участникам общих мероприятий (иначе 403). */
export function getUserProfile(id: string): Promise<Profile> {
  return apiFetch(`/profile/${id}`, { auth: true })
}

export function updateProfile(patch: ProfilePatch): Promise<Profile> {
  return apiFetch('/profile', { method: 'PATCH', body: patch, auth: true })
}

export function uploadProfileImage(kind: ProfileImageKind, file: File): Promise<Profile> {
  const body = new FormData()
  body.append('file', file, file.name)
  return apiFetch(`/profile/${kind}`, { method: 'PUT', body, auth: true })
}

export function deleteProfileImage(kind: ProfileImageKind): Promise<Profile> {
  return apiFetch(`/profile/${kind}`, { method: 'DELETE', auth: true })
}

export function userImagePath(userId: string, imageId: string, size: ImageSize = 'full'): string {
  return `/users/${userId}/images/${imageId}${size === 'thumb' ? '?size=thumb' : ''}`
}

export function fetchUserImage(
  userId: string,
  imageId: string,
  size: ImageSize = 'full',
): Promise<Blob> {
  return apiFetchBlob(userImagePath(userId, imageId, size), { auth: true })
}
