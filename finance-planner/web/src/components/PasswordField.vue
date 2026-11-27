<script setup lang="ts">
import InputText from "primevue/inputtext";
import { computed, ref } from "vue";

import type { InputDescription } from "../composables/useFieldErrors";

const SHOW_PASSWORD_TEXT = "Показать пароль";
const HIDE_PASSWORD_TEXT = "Скрыть пароль";

defineProps<{
    inputId: string;
    autocomplete: "current-password" | "new-password";
    description: InputDescription;
    isInvalid: boolean;
}>();

const password = defineModel<string>({ required: true });

const emit = defineEmits<{
    blur: [];
}>();

// Своя кнопка вместо значка Password из PrimeVue: тот реагирует только на мышь и не попадает в обход клавишей Tab
const isUnmasked = ref(false);
const inputType = computed(() => (isUnmasked.value ? "text" : "password"));
const toggleLabel = computed(() => (isUnmasked.value ? HIDE_PASSWORD_TEXT : SHOW_PASSWORD_TEXT));

function toggleMask(): void {
    isUnmasked.value = !isUnmasked.value;
}

function reportBlur(): void {
    emit("blur");
}
</script>

<template>
    <div class="password-field">
        <InputText
            :id="inputId"
            v-model="password"
            v-bind="description"
            class="password-field__input"
            :type="inputType"
            :autocomplete="autocomplete"
            autocapitalize="none"
            spellcheck="false"
            :invalid="isInvalid"
            fluid
            @blur="reportBlur"
        />
        <button
            class="password-field__toggle"
            type="button"
            :aria-label="toggleLabel"
            :aria-controls="inputId"
            :title="toggleLabel"
            @click="toggleMask"
        >
            <svg class="password-field__icon" viewBox="0 0 16 16" aria-hidden="true">
                <path d="M1.5 8s2.5-4.5 6.5-4.5 6.5 4.5 6.5 4.5-2.5 4.5-6.5 4.5S1.5 8 1.5 8z" />
                <circle cx="8" cy="8" r="2" />
                <path v-if="isUnmasked" d="M2.5 13.5l11-11" />
            </svg>
        </button>
    </div>
</template>

<style scoped>
.password-field {
    position: relative;
}

.password-field__input {
    padding-right: 2.75rem;
}

.password-field__toggle {
    position: absolute;
    top: 0;
    right: 0.375rem;
    bottom: 0;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 2rem;
    height: 2rem;
    margin: auto 0;
    padding: 0;
    border: 0;
    border-radius: var(--radius-medium);
    background: transparent;
    color: var(--color-text-secondary);
    cursor: pointer;
}

.password-field__toggle:hover {
    background: var(--color-surface-raised);
    color: var(--color-text);
}

.password-field__toggle:focus-visible {
    outline: none;
    box-shadow: var(--focus-ring);
}

.password-field__icon {
    width: 1rem;
    height: 1rem;
    fill: none;
    stroke: currentColor;
    stroke-width: 1.5;
    stroke-linecap: round;
    stroke-linejoin: round;
}
</style>
