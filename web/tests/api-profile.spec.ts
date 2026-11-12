import { describe, expect, it } from 'vitest'

import { configureAuth } from '@/api/client'
import { listCities } from '@/api/events'
import {
  deleteProfileImage,
  getUserProfile,
  updateProfile,
  uploadProfileImage,
} from '@/api/profile'
import { loadUserImageUrl } from '@/composables/usePhotoUrl'

import { blobResponse, completeProfile, jsonResponse, mockApi } from './helpers/api'

describe('API профиля', () => {
  it('адреса и тела запросов', async () => {
    configureAuth({ getAccessToken: () => 'access-1', refresh: async () => null })
    const api = mockApi({
      'GET /profile/u2': () => jsonResponse(200, completeProfile),
      'PATCH /profile': () => jsonResponse(200, completeProfile),
      'PUT /profile/avatar': () => jsonResponse(200, completeProfile),
      'DELETE /profile/cover': () => jsonResponse(200, completeProfile),
      'GET /cities': () => jsonResponse(200, []),
    })

    await getUserProfile('u2')
    await updateProfile({ about: 'Привет', city_id: 1, interest_ids: [2] })
    await uploadProfileImage('avatar', new File(['x'], 'me.jpg', { type: 'image/jpeg' }))
    await deleteProfileImage('cover')
    await listCities()

    expect(api.requests.map((r) => `${r.method} ${r.path}`)).toEqual([
      'GET /profile/u2',
      'PATCH /profile',
      'PUT /profile/avatar',
      'DELETE /profile/cover',
      'GET /cities',
    ])
    expect(api.requests[1]?.body).toEqual({ about: 'Привет', city_id: 1, interest_ids: [2] })
    const form = api.requests[2]?.body as FormData
    expect((form.get('file') as File).name).toBe('me.jpg')
    expect(api.requests[2]?.headers['Content-Type']).toBeUndefined()
    expect(api.requests.every((r) => r.headers.Authorization === 'Bearer access-1')).toBe(true)
  })

  it('аватар одного пользователя в нескольких местах — один запрос', async () => {
    const api = mockApi({ 'GET /users/u2/images/av-1': () => blobResponse() })

    const urls = await Promise.all([
      loadUserImageUrl('u2', 'av-1', 'thumb'),
      loadUserImageUrl('u2', 'av-1', 'thumb'),
      loadUserImageUrl('u2', 'av-1', 'thumb'),
    ])

    expect(new Set(urls).size).toBe(1)
    expect(api.calls('GET /users/u2/images/av-1').map((r) => r.url)).toEqual([
      '/api/users/u2/images/av-1?size=thumb',
    ])
  })
})
