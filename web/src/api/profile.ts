import { apiFetch } from './client'

export type Role = 'participant' | 'organizer' | 'admin'

export interface Profile {
  id: string
  phone: string
  name: string | null
  birth_date: string | null
  age: number | null
  email: string | null
  telegram: string | null
  photo_url: string | null
  roles: Role[]
  profile_completed: boolean
}

export interface ProfilePatch {
  name?: string
  birth_date?: string
  email?: string | null
  telegram?: string | null
}

export function getProfile(): Promise<Profile> {
  return apiFetch('/profile', { auth: true })
}

export function updateProfile(patch: ProfilePatch): Promise<Profile> {
  return apiFetch('/profile', { method: 'PATCH', body: patch, auth: true })
}
