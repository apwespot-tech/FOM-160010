import { onBeforeUnmount, ref, type Ref } from 'vue'

// Держать в синхроне с src/styles.css
export const TABLET_MIN_WIDTH = 640
export const DESKTOP_MIN_WIDTH = 1024

function useMediaQuery(query: string): Ref<boolean> {
  const media = window.matchMedia(query)
  const matches = ref(media.matches)
  const update = (event: MediaQueryListEvent) => {
    matches.value = event.matches
  }
  media.addEventListener('change', update)
  onBeforeUnmount(() => media.removeEventListener('change', update))
  return matches
}

/** Мобильная ширина: меньше 640 px. Реагирует на изменение окна и поворот экрана. */
export function useIsMobile(): Ref<boolean> {
  return useMediaQuery(`(max-width: ${TABLET_MIN_WIDTH - 1}px)`)
}

/** Ширина компьютера: от 1024 px. */
export function useIsDesktop(): Ref<boolean> {
  return useMediaQuery(`(min-width: ${DESKTOP_MIN_WIDTH}px)`)
}
