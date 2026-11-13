import type { AppNotification, ChangedField } from '@/api/notifications'

const FIELD_LABELS: [ChangedField, string][] = [
  ['starts_at', 'время'],
  ['duration_minutes', 'длительность'],
  ['city_id', 'город'],
  ['place', 'место'],
  ['title', 'название'],
]

/** Текст уведомления; `currentUserId` различает исключённого и организатора. */
export function notificationText(n: AppNotification, currentUserId: string | null): string {
  const title = `«${n.event.title}»`
  const name = n.participant?.name ?? ''
  switch (n.type) {
    case 'event_changed': {
      const changed = new Set(n.changed_fields ?? [])
      const fields = FIELD_LABELS.filter(([field]) => changed.has(field)).map(([, label]) => label)
      return `Изменилось мероприятие ${title}: ${fields.join(', ')}`
    }
    case 'event_deleted':
      return `Мероприятие ${title} удалено`
    case 'participant_removed':
      return n.participant?.id === currentUserId
        ? `Вас исключили из мероприятия ${title}`
        : `Администратор исключил участника ${name} из ${title}`
    case 'participant_joined':
      return `Новый участник ${title}: ${name}`
    case 'participant_left':
      return `Отказ от участия в ${title}: ${name}`
    case 'review_reminder':
      return `Оцените участников мероприятия ${title}`
  }
}
