import { computed, onBeforeUnmount, ref, type Ref } from 'vue'

/**
 * Секунды до дедлайна (Date.now() в мс). Пересчитывается от текущего времени,
 * поэтому не отстаёт, если вкладка была неактивна.
 */
export function useCountdown(deadline: Ref<number>) {
  const now = ref(Date.now())
  const timer = setInterval(() => {
    now.value = Date.now()
  }, 250)
  onBeforeUnmount(() => clearInterval(timer))

  const remaining = computed(() => Math.max(0, Math.ceil((deadline.value - now.value) / 1000)))
  /** Сбросить «текущее время» сразу (например, после установки нового дедлайна). */
  const tick = () => {
    now.value = Date.now()
  }
  return { remaining, tick }
}
