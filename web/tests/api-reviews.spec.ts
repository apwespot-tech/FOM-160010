import { describe, expect, it } from 'vitest'

import {
  createReview,
  deleteReview,
  getMyReviews,
  listUserReviews,
  updateReview,
} from '@/api/reviews'

import { jsonResponse, mockApi } from './helpers/api'

describe('API отзывов', () => {
  it('методы, адреса и тела запросов', async () => {
    const api = mockApi({
      'POST /events/e1/reviews': () => jsonResponse(201, {}),
      'GET /events/e1/reviews/mine': () =>
        jsonResponse(200, { items: [], opens_at: '', closes_at: '' }),
      'PATCH /reviews/r1': () => jsonResponse(200, {}),
      'DELETE /reviews/r1': () => jsonResponse(204),
      'GET /users/u1/reviews': () => jsonResponse(200, { items: [], total: 0 }),
    })

    await createReview('e1', { target_id: 'u2', stars: 5, text: 'Супер', anonymous: true })
    await getMyReviews('e1')
    await updateReview('r1', { stars: 3 })
    await deleteReview('r1')
    await listUserReviews('u1', 'participant', 20)

    expect(api.requests.map((r) => `${r.method} ${r.path}`)).toEqual([
      'POST /events/e1/reviews',
      'GET /events/e1/reviews/mine',
      'PATCH /reviews/r1',
      'DELETE /reviews/r1',
      'GET /users/u1/reviews',
    ])
    expect(api.requests[0]?.body).toEqual({
      target_id: 'u2',
      stars: 5,
      text: 'Супер',
      anonymous: true,
    })
    expect(api.requests[2]?.body).toEqual({ stars: 3 })
    expect(api.requests[4]?.url).toBe('/api/users/u1/reviews?kind=participant&limit=20&offset=20')
  })
})
