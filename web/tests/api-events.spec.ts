import { describe, expect, it } from 'vitest'

import {
  createEvent,
  deleteEvent,
  joinEvent,
  leaveEvent,
  listEvents,
  listParticipants,
  removeParticipant,
  updateEvent,
} from '@/api/events'

import { jsonResponse, mockApi } from './helpers/api'

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
