import { useToast } from 'primevue/usetoast'

import { useSessionStore } from '@/stores/session'

export const PROFILE_REQUIRED_MESSAGE = 'Сначала заполните профиль'

/**
 * Проверка перед действием, которому нужен заполненный профиль (запись, создание мероприятия).
 * Незаполненный профиль — уведомление вместо действия. Права всё равно проверяет сервер.
 * Вызывать в setup компонента: уведомления берутся из контекста приложения.
 */
export function useRequireCompletedProfile(): () => boolean {
  const session = useSessionStore()
  const toast = useToast()

  return () => {
    if (session.isProfileCompleted) return true
    toast.add({ severity: 'warn', summary: PROFILE_REQUIRED_MESSAGE, life: 4000 })
    return false
  }
}
