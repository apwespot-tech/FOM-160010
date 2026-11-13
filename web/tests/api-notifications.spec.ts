import { describe, expect, it } from 'vitest'

import { getUnreadCount, listNotifications, markNotificationsRead } from '@/api/notifications'

import { jsonResponse, mockApi } from './helpers/api'

describe('API уведомлений', () => {
  it('методы, адреса и тела запросов', async () => {
    const api = mockApi({
      'GET /notifications': () => jsonResponse(200, { items: [], unread_count: 0 }),
      'GET /notifications/unread-count': () => jsonResponse(200, { unread_count: 4 }),
      'POST /notifications/read': () => jsonResponse(204),
    })

    await listNotifications()
    expect(await getUnreadCount()).toBe(4)
    await markNotificationsRead('2026-11-11T10:00:00Z')

    expect(api.requests.map((r) => `${r.method} ${r.path}`)).toEqual([
      'GET /notifications',
      'GET /notifications/unread-count',
      'POST /notifications/read',
    ])
    expect(api.requests[2]?.body).toEqual({ up_to: '2026-11-11T10:00:00Z' })
  })
})
