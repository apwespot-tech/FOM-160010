import { vi } from 'vitest'

import type { TokenPair } from '@/api/auth'
import type { Category, EventItem } from '@/api/events'
import type { Profile } from '@/api/profile'

export interface MockRequest {
  method: string
  path: string
  url: string
  body: unknown
  headers: Record<string, string>
}

export type MockHandler = (request: MockRequest) => Response | Promise<Response>

export function jsonResponse(
  status: number,
  body?: unknown,
  headers: Record<string, string> = {},
): Response {
  return new Response(body === undefined ? null : JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json', ...headers },
  })
}

export function errorResponse(
  status: number,
  code: string,
  extra: Record<string, unknown> = {},
): Response {
  return jsonResponse(status, { detail: { code, message: code, ...extra } })
}

/**
 * Подменяет fetch: обработчики по ключу "METHOD /path" (без /api и query).
 * Незарегистрированный путь отвечает 404 — как выключенная тестовая ручка.
 */
export function mockApi(handlers: Record<string, MockHandler> = {}) {
  const requests: MockRequest[] = []
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init: RequestInit = {}) => {
    const url = String(input)
    const path = (url.replace(/^\/api/, '').split('?')[0] ?? '').trim()
    const method = (init.method ?? 'GET').toUpperCase()
    const headers = { ...(init.headers as Record<string, string> | undefined) }
    const body =
      typeof init.body === 'string'
        ? (JSON.parse(init.body) as unknown)
        : init.body instanceof FormData
          ? init.body
          : undefined
    const request = { method, path, url, body, headers }
    requests.push(request)
    const handler = handlers[`${method} ${path}`]
    if (!handler) return errorResponse(404, 'not_found')
    return handler(request)
  })
  vi.stubGlobal('fetch', fetchMock)

  return {
    requests,
    fetchMock,
    on(key: string, handler: MockHandler) {
      handlers[key] = handler
    },
    calls(key: string) {
      return requests.filter((request) => `${request.method} ${request.path}` === key)
    },
  }
}

export function tokens(n = 1): TokenPair {
  return {
    access_token: `access-${n}`,
    refresh_token: `refresh-${n}`,
    token_type: 'bearer',
    expires_in: 900,
    refresh_expires_in: 2_592_000,
  }
}

export const draftProfile: Profile = {
  id: '6f1c7e7a-0000-4000-8000-000000000001',
  phone: '+79991234567',
  name: null,
  birth_date: null,
  age: null,
  email: null,
  telegram: null,
  photo_url: null,
  roles: ['organizer', 'participant'],
  profile_completed: false,
}

export const completeProfile: Profile = {
  ...draftProfile,
  name: 'Анна Иванова',
  birth_date: '2000-01-15',
  age: 26,
  telegram: '@anna_k',
  profile_completed: true,
}

export const categories: Category[] = [
  { id: 1, name: 'Настольные игры', icon: 'pi-th-large', cover_id: 'cov-1' },
  { id: 2, name: 'Прогулки', icon: 'pi-map', cover_id: 'cov-2' },
  { id: 3, name: 'Спорт', icon: 'pi-bolt', cover_id: 'cov-3' },
  { id: 4, name: 'Кино', icon: 'pi-video', cover_id: 'cov-4' },
]

/** Мероприятие другого организатора через сутки после 2026-10-31 12:00 МСК. */
export function eventItem(overrides: Partial<EventItem> = {}): EventItem {
  return {
    id: 'e1',
    title: 'Настолки в антикафе',
    description: 'Играем в «Каркассон»',
    place: 'Антикафе «Циферблат»',
    starts_at: '2026-11-01T16:00:00Z',
    duration_minutes: 120,
    created_at: '2026-10-30T15:40:00Z',
    category: { id: 1, name: 'Настольные игры', icon: 'pi-th-large', cover_id: 'cov-1' },
    max_participants: 10,
    min_age: 0,
    organizer: { id: 'org-1', name: 'Борис Петров', photo_url: null, telegram: null },
    photos: [],
    participants_count: 3,
    free_places: 7,
    is_full: false,
    is_joined: false,
    ...overrides,
  }
}

/** Ответ с картинкой (для GET фото). */
export function blobResponse(type = 'image/jpeg', content = 'img'): Response {
  // Строковое тело: Blob из jsdom несовместим с Response из Node, тип берётся из заголовка
  return new Response(content, {
    status: 200,
    headers: { 'Content-Type': type },
  })
}

export function photoFile(name = 'photo.jpg', type = 'image/jpeg', size = 1024): File {
  return new File([new Uint8Array(size)], name, { type })
}
