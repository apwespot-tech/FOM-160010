import { onMounted, onUnmounted, ref } from 'vue'

import { getUnreadCount } from '@/api/notifications'

export const UNREAD_POLL_INTERVAL_MS = 60_000

/**
 * Число непрочитанных уведомлений: запрос при монтировании, раз в минуту при видимой
 * вкладке и сразу при возвращении на неё. Ошибки не меняют значение.
 * Компонент монтируется только у авторизованного пользователя — размонтирование
 * при выходе останавливает опрос.
 */
export function useUnreadNotifications() {
  const unreadCount = ref(0)
  let timer: ReturnType<typeof setInterval> | undefined
  // Ответ, пришедший после локального сброса, не должен вернуть точку
  let generation = 0

  async function refresh(): Promise<void> {
    const current = generation
    try {
      const count = await getUnreadCount()
      if (current === generation) unreadCount.value = count
    } catch {
      // Отметка остаётся прежней, следующий запрос — по расписанию
    }
  }

  /** Сброс после отметки прочитанными. */
  function clear(): void {
    generation += 1
    unreadCount.value = 0
  }

  function isVisible(): boolean {
    return document.visibilityState === 'visible'
  }

  function onVisibilityChange(): void {
    if (isVisible()) void refresh()
  }

  onMounted(() => {
    void refresh()
    timer = setInterval(() => {
      if (isVisible()) void refresh()
    }, UNREAD_POLL_INTERVAL_MS)
    document.addEventListener('visibilitychange', onVisibilityChange)
  })

  onUnmounted(() => {
    clearInterval(timer)
    document.removeEventListener('visibilitychange', onVisibilityChange)
  })

  return { unreadCount, refresh, clear }
}
