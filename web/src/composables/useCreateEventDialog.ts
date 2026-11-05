import { ref } from 'vue'

// Окно создания одно на приложение (смонтировано в App.vue), открыть его можно откуда угодно
const visible = ref(false)
// Список мероприятий подписывается, чтобы показать созданное, пока окно ещё открыто
const createdListeners = new Set<() => void>()

export function useCreateEventDialog() {
  return {
    visible,
    open: () => {
      visible.value = true
    },
    close: () => {
      visible.value = false
    },
    /** Подписка на создание мероприятия; возвращает отписку. */
    onEventCreated: (listener: () => void): (() => void) => {
      createdListeners.add(listener)
      return () => createdListeners.delete(listener)
    },
    notifyCreated: () => {
      for (const listener of createdListeners) listener()
    },
  }
}
