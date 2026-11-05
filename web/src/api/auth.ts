import { apiFetch } from './client'

/** Интервал повторного запроса кода — как на backend */
export const RESEND_INTERVAL_MS = 60_000

export interface TokenPair {
  access_token: string
  refresh_token: string
  token_type: 'bearer'
  expires_in: number
  refresh_expires_in: number
}

export function requestCode(phone: string): Promise<{ expires_in: number }> {
  return apiFetch('/auth/code', { method: 'POST', body: { phone } })
}

/** Временная тестовая ручка: работает только при AUTH_TEST_ENDPOINTS=true на backend. */
export function getTestCode(phone: string): Promise<{ code: string }> {
  return apiFetch(`/auth/test/code?phone=${encodeURIComponent(phone)}`)
}

export function verifyCode(phone: string, code: string): Promise<TokenPair> {
  return apiFetch('/auth/verify', { method: 'POST', body: { phone, code } })
}

export function refreshTokens(refreshToken: string): Promise<TokenPair> {
  return apiFetch('/auth/refresh', { method: 'POST', body: { refresh_token: refreshToken } })
}

export function logout(refreshToken: string): Promise<void> {
  return apiFetch('/auth/logout', { method: 'POST', body: { refresh_token: refreshToken } })
}
