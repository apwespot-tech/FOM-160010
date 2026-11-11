import { apiFetch } from './client'

export type NotificationType =
  | 'event_changed'
  | 'event_deleted'
  | 'participant_removed'
  | 'participant_joined'
  | 'participant_left'
  | 'review_reminder'

/** Поля мероприятия, изменение которых порождает `event_changed`. */
export type ChangedField = 'starts_at' | 'duration_minutes' | 'city_id' | 'place' | 'title'

export interface AppNotification {
  id: string
  type: NotificationType
  created_at: string
  read: boolean
  /** id = null, если мероприятие удалено; название — на момент уведомления */
  event: { id: string | null; title: string }
  /** Для уведомлений об исключении, записи и отказе, иначе null */
  participant: { id: string; name: string } | null
  /** Для `event_changed`, иначе null */
  changed_fields: ChangedField[] | null
}

export interface NotificationList {
  items: AppNotification[]
  unread_count: number
}

export function listNotifications(): Promise<NotificationList> {
  return apiFetch('/notifications', { auth: true })
}

export async function getUnreadCount(): Promise<number> {
  const body = await apiFetch<{ unread_count: number }>('/notifications/unread-count', {
    auth: true,
  })
  return body.unread_count
}

/** Отмечает прочитанными уведомления, созданные не позже `upTo`. */
export function markNotificationsRead(upTo: string): Promise<void> {
  return apiFetch('/notifications/read', { method: 'POST', body: { up_to: upTo }, auth: true })
}
