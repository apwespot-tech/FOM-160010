<script setup lang="ts">
// Select не раскрывает список по щелчку на элементе с этой отметкой, как и по своему значку очистки
const SELECT_CLEAR_SECTION = "clearicon";

defineProps<{
    label: string;
}>();

const emit = defineEmits<{
    clear: [event: MouseEvent];
}>();

function requestClear(event: MouseEvent): void {
    emit("clear", event);
}
</script>

<template>
    <!-- Кнопка вместо значка PrimeVue: значок реагирует только на мышь, а кнопку можно нажать и с клавиатуры -->
    <button
        class="filter-clear"
        type="button"
        :data-pc-section="SELECT_CLEAR_SECTION"
        :aria-label="label"
        :title="label"
        @click="requestClear"
    >
        <svg class="filter-clear__icon" viewBox="0 0 16 16" aria-hidden="true">
            <path d="M4.5 4.5l7 7M11.5 4.5l-7 7" />
        </svg>
    </button>
</template>

<style scoped>
.filter-clear {
    display: inline-flex;
    align-items: center;
    align-self: center;
    justify-content: center;
    width: 1.75rem;
    height: 1.75rem;
    flex-shrink: 0;
    padding: 0;
    border: 0;
    border-radius: 50%;
    background: transparent;
    color: var(--color-text-secondary);
    cursor: pointer;
}

.filter-clear:hover {
    background: var(--color-surface-raised);
    color: var(--color-text);
}

.filter-clear:focus-visible {
    outline: none;
    box-shadow: var(--focus-ring);
}

.filter-clear__icon {
    width: 0.875rem;
    height: 0.875rem;
    fill: none;
    stroke: currentColor;
    stroke-width: 1.75;
    stroke-linecap: round;
}
</style>
