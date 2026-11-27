import { onScopeDispose, ref, watch } from "vue";
import type { Ref } from "vue";

// Индикатор загрузки появляется, только если ответа нет дольше 400 мс: короткое мигание отвлекает сильнее ожидания
export const LOADING_INDICATOR_DELAY_MS = 400;

export function useDelayedFlag(source: Ref<boolean>, delayMs: number = LOADING_INDICATOR_DELAY_MS): Ref<boolean> {
    const isRaised = ref(false);
    let timerId: ReturnType<typeof setTimeout> | null = null;

    function clearTimer(): void {
        if (timerId !== null) {
            clearTimeout(timerId);
            timerId = null;
        }
    }

    watch(
        source,
        (isActive) => {
            clearTimer();

            if (!isActive) {
                isRaised.value = false;

                return;
            }

            timerId = setTimeout(() => {
                isRaised.value = true;
            }, delayMs);
        },
        { immediate: true },
    );

    onScopeDispose(clearTimer);

    return isRaised;
}
