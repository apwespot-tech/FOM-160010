import { vi } from 'vitest'

import type { TokenPair } from '@/api/auth'
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
    const body = typeof init.body === 'string' ? (JSON.parse(init.body) as unknown) : undefined
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
