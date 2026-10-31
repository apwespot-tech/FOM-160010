import { ref } from 'vue'

// Окно создания одно на приложение (смонтировано в App.vue), открыть его можно откуда угодно
const visible = ref(false)

export function useCreateEventDialog() {
  return {
    visible,
    open: () => {
      visible.value = true
    },
    close: () => {
      visible.value = false
    },
  }
}
