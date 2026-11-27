<script setup lang="ts">
import { computed } from "vue";

import { buildErrorId, buildHintId, buildLabelId } from "../utils/formIds";

const props = defineProps<{
    label: string;
    inputId: string;
    error?: string;
    hint?: string;
    isRequired?: boolean;
}>();

const labelId = computed(() => buildLabelId(props.inputId));
const errorId = computed(() => buildErrorId(props.inputId));
const hintId = computed(() => buildHintId(props.inputId));
const hasError = computed(() => Boolean(props.error));

// Атрибут for связывает подпись только с полями ввода, а поле выбора PrimeVue — это span, поэтому его фокусирует щелчок по подписи
function focusField(): void {
    const field = document.getElementById(props.inputId);
    const isNativelyLabelled = field instanceof HTMLInputElement || field instanceof HTMLTextAreaElement || field instanceof HTMLButtonElement;

    if (field !== null && !isNativelyLabelled) {
        field.focus();
    }
}
</script>

<template>
    <div class="form-field">
        <label :id="labelId" class="form-field__label" :for="inputId" @click="focusField">
            {{ label }}
            <span v-if="isRequired" class="form-field__required" aria-hidden="true">*</span>
        </label>
        <slot />
        <p v-if="hint && !hasError" :id="hintId" class="form-field__hint">{{ hint }}</p>
        <p v-if="hasError" :id="errorId" class="form-field__error" role="alert">
            <svg class="form-field__error-icon" viewBox="0 0 16 16" aria-hidden="true">
                <circle cx="8" cy="8" r="7" />
                <path d="M8 4.5v4.25M8 11.25v.25" />
            </svg>
            <span>{{ error }}</span>
        </p>
    </div>
</template>

<style scoped>
.form-field {
    display: grid;
    gap: 0.375rem;
    min-width: 0;
}

.form-field__label {
    font-size: 0.875rem;
    font-weight: 600;
}

.form-field__required {
    margin-left: 0.25rem;
    color: var(--color-danger);
}

.form-field__hint {
    color: var(--color-text-secondary);
    font-size: 0.8125rem;
}

.form-field__error {
    display: flex;
    align-items: flex-start;
    gap: 0.375rem;
    color: var(--color-danger);
    font-size: 0.8125rem;
}

.form-field__error-icon {
    width: 1rem;
    height: 1rem;
    flex-shrink: 0;
    margin-top: 0.0625rem;
}

.form-field__error-icon circle {
    fill: none;
    stroke: currentColor;
    stroke-width: 1.5;
}

.form-field__error-icon path {
    fill: none;
    stroke: currentColor;
    stroke-width: 1.75;
    stroke-linecap: round;
}
</style>
