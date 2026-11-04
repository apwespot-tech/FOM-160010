import { createPinia, setActivePinia } from 'pinia'
import { describe, expect, it, vi } from 'vitest'

import { configureAuth } from '@/api/client'
import { clearPhotoCache, loadPhotoUrl } from '@/composables/usePhotoUrl'
import { useSessionStore } from '@/stores/session'

import { blobResponse, errorResponse, mockApi } from './helpers/api'

describe('кеш фото по id', () => {
  it('два обращения к одному фото — один запрос', async () => {
    configureAuth({ getAccessToken: () => 'access-1', refresh: async () => null })
    const api = mockApi({ 'GET /events/e1/photos/p1': () => blobResponse() })

    const [first, second] = await Promise.all([loadPhotoUrl('e1', 'p1'), loadPhotoUrl('e1', 'p1')])
    const third = await loadPhotoUrl('e1', 'p1')

    expect(first).toMatch(/^blob:/)
    expect(second).toBe(first)
    expect(third).toBe(first)
    expect(api.calls('GET /events/e1/photos/p1')).toHaveLength(1)
    expect(api.requests[0]?.headers.Authorization).toBe('Bearer access-1')
  })

  it('после ошибки следующий показ повторяет запрос', async () => {
    let fail = true
    const api = mockApi({
      'GET /events/e1/photos/p1': () => (fail ? errorResponse(500, 'oops') : blobResponse()),
    })

    await expect(loadPhotoUrl('e1', 'p1')).rejects.toMatchObject({ status: 500 })
    fail = false
    await expect(loadPhotoUrl('e1', 'p1')).resolves.toMatch(/^blob:/)

    expect(api.calls('GET /events/e1/photos/p1')).toHaveLength(2)
  })

  it('выход освобождает все фото, после входа они загружаются заново', async () => {
    setActivePinia(createPinia())
    const session = useSessionStore()
    session.accessToken = 'access-1'
    const revoke = vi.spyOn(URL, 'revokeObjectURL')
    const api = mockApi({
      'GET /events/e1/photos/p1': () => blobResponse(),
      'GET /events/e1/photos/p2': () => blobResponse(),
    })
    const urls = await Promise.all([loadPhotoUrl('e1', 'p1'), loadPhotoUrl('e1', 'p2')])

    await session.logout()

    expect(revoke.mock.calls.map(([url]) => url).sort()).toEqual([...urls].sort())
    await loadPhotoUrl('e1', 'p1')
    expect(api.calls('GET /events/e1/photos/p1')).toHaveLength(2)
    revoke.mockRestore()
    clearPhotoCache()
  })
})
