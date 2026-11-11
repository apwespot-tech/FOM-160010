import { describe, expect, it } from 'vitest'

import type { AppNotification } from '@/api/notifications'
import { notificationText } from '@/utils/notifications'

const ME = 'u-me'
const ANNA = { id: 'u-anna', name: 'Анна' }
const OLEG = { id: 'u-oleg', name: 'Олег' }

function make(overrides: Partial<AppNotification>): AppNotification {
  return {
    id: 'n1',
    type: 'event_deleted',
    created_at: '2026-11-11T10:00:00Z',
    read: false,
    event: { id: 'e1', title: 'Мафия' },
    participant: null,
    changed_fields: null,
    ...overrides,
  }
}

describe('Тексты уведомлений', () => {
  it.each([
    [
      { type: 'event_deleted', event: { id: null, title: 'Прогулка' } },
      'Мероприятие «Прогулка» удалено',
    ],
    [{ type: 'participant_joined', participant: OLEG }, 'Новый участник «Мафия»: Олег'],
    [{ type: 'participant_left', participant: OLEG }, 'Отказ от участия в «Мафия»: Олег'],
    [{ type: 'review_reminder' }, 'Оцените участников мероприятия «Мафия»'],
    [
      { type: 'event_changed', changed_fields: ['place', 'starts_at'] },
      'Изменилось мероприятие «Мафия»: время, место',
    ],
    [
      { type: 'event_changed', changed_fields: ['city_id', 'duration_minutes'] },
      'Изменилось мероприятие «Мафия»: длительность, город',
    ],
    [
      { type: 'event_changed', changed_fields: ['title'], event: { id: 'e1', title: 'Мафия 2' } },
      'Изменилось мероприятие «Мафия 2»: название',
    ],
    [
      { type: 'participant_removed', participant: ANNA },
      'Администратор исключил участника Анна из «Мафия»',
    ],
    [
      { type: 'participant_removed', participant: { id: ME, name: 'Я' } },
      'Вас исключили из мероприятия «Мафия»',
    ],
  ] as [Partial<AppNotification>, string][])('%o -> %s', (overrides, text) => {
    expect(notificationText(make(overrides), ME)).toBe(text)
  })
})
