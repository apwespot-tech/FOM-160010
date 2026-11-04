import { describe, expect, it } from 'vitest'

import {
  createEvent,
  deleteEvent,
  fetchEventPhoto,
  joinEvent,
  leaveEvent,
  listEvents,
  listParticipants,
  removeParticipant,
  replaceEventPhotos,
  updateEvent,
} from '@/api/events'
import { configureAuth } from '@/api/client'

import { blobResponse, errorResponse, jsonResponse, mockApi, photoFile } from './helpers/api'

describe('API мероприятий', () => {
  it('список: параметры в query, пустые не передаются', async () => {
    const api = mockApi({ 'GET /events': () => jsonResponse(200, { items: [], total: 0 }) })

    await listEvents({ scope: 'joined', period: 'past', category_id: 3, limit: 20, offset: 0 })
    await listEvents()

    expect(api.requests[0]?.url).toBe(
      '/api/events?scope=joined&period=past&category_id=3&limit=20&offset=0',
    )
    expect(api.requests[1]?.url).toBe('/api/events')
  })

  it('действия: методы и адреса', async () => {
    const api = mockApi({
      'POST /events': () => jsonResponse(201, {}),
      'PATCH /events/e1': () => jsonResponse(200, {}),
      'DELETE /events/e1': () => jsonResponse(204),
      'POST /events/e1/join': () => jsonResponse(200, {}),
      'POST /events/e1/leave': () => jsonResponse(200, {}),
      'GET /events/e1/participants': () => jsonResponse(200, []),
      'POST /events/e1/participants/u2/remove': () => jsonResponse(200, {}),
    })

    await createEvent({
      title: 't',
      description: 'd',
      place: 'p',
      starts_at: '2026-11-01T19:00:00+03:00',
      duration_minutes: null,
      category_id: 1,
      max_participants: 10,
      min_age: 0,
    })
    await updateEvent('e1', { place: 'новое' })
    await deleteEvent('e1')
    await joinEvent('e1')
    await leaveEvent('e1')
    await listParticipants('e1')
    await removeParticipant('e1', 'u2')

    expect(api.requests.map((r) => `${r.method} ${r.path}`)).toEqual([
      'POST /events',
      'PATCH /events/e1',
      'DELETE /events/e1',
      'POST /events/e1/join',
      'POST /events/e1/leave',
      'GET /events/e1/participants',
      'POST /events/e1/participants/u2/remove',
    ])
    expect(api.requests[1]?.body).toEqual({ place: 'новое' })
  })
})

describe('API фото мероприятий', () => {
  it('замена набора: multipart с полем order, файлами и токеном, без JSON-заголовка', async () => {
    const api = mockApi({ 'PUT /events/e1/photos': () => jsonResponse(200, {}) })
    configureAuth({ getAccessToken: () => 'access-1', refresh: async () => null })
    const beach = photoFile('beach.jpg')
    const map = photoFile('map.png', 'image/png')

    await replaceEventPhotos('e1', [{ file: 0 }, { id: 'p1' }, { file: 1 }], [beach, map])

    const [request] = api.requests
    expect(request?.method).toBe('PUT')
    expect(request?.headers.Authorization).toBe('Bearer access-1')
    expect(request?.headers['Content-Type']).toBeUndefined()
    const form = request?.body as FormData
    expect(JSON.parse(String(form.get('order')))).toEqual([{ file: 0 }, { id: 'p1' }, { file: 1 }])
    const files = form.getAll('files') as File[]
    expect(files.map((file) => file.name)).toEqual(['beach.jpg', 'map.png'])
  })

  it('ошибка файла: номер файла из detail.file', async () => {
    mockApi({
      'PUT /events/e1/photos': () => errorResponse(422, 'photo_invalid', { file: 1 }),
    })

    const error = await replaceEventPhotos('e1', [], []).catch((e: unknown) => e)

    expect(error).toMatchObject({ status: 422, code: 'photo_invalid', file: 1 })
  })

  it('фото запрашивается с токеном и повторяется после обновления токена', async () => {
    let token = 'access-old'
    configureAuth({
      getAccessToken: () => token,
      refresh: async () => {
        token = 'access-new'
        return token
      },
    })
    const api = mockApi({
      'GET /events/e1/photos/p1': (request) =>
        request.headers.Authorization === 'Bearer access-new'
          ? blobResponse('image/png')
          : errorResponse(401, 'invalid_token'),
    })

    const blob = await fetchEventPhoto('e1', 'p1')

    expect(blob.type).toBe('image/png')
    expect(api.calls('GET /events/e1/photos/p1')).toHaveLength(2)
  })
})
