<script setup lang="ts">
/**
 * Дата и время начала: на мобильной ширине — нативный datetime-local (системный выбор),
 * на планшете и компьютере — DatePicker с выбором времени. Значение — Date в часовом поясе браузера.
 * Ручной ввод в DatePicker выключен: в PrimeVue 4.5 разбор времени в 24-часовом формате
 * падает (populateTime ждёт AM/PM), поэтому дата и время выбираются только в календаре.
 */
import DatePicker from 'primevue/datepicker'
import InputText from 'primevue/inputtext'

import { useIsMobile } from '@/utils/breakpoints'
import { fromLocalInputValue, startOfToday, toLocalInputValue } from '@/utils/dates'

defineProps<{
  modelValue: Date | null
  inputId: string
  invalid?: boolean
  ariaLabel?: string
}>()
const emit = defineEmits<{ 'update:modelValue': [value: Date | null]; blur: [] }>()

const isMobile = useIsMobile()
const minDate = startOfToday()

function onNativeInput(value: string | undefined) {
  emit('update:modelValue', fromLocalInputValue(value ?? ''))
}
</script>

<template>
  <InputText
    v-if="isMobile"
    :id="inputId"
    type="datetime-local"
    :model-value="modelValue ? toLocalInputValue(modelValue) : ''"
    :min="toLocalInputValue(minDate)"
    :invalid="invalid"
    :aria-label="ariaLabel"
    class="date-time-native"
    data-testid="field-starts-at-native"
    @update:model-value="onNativeInput"
    @blur="emit('blur')"
  />
  <DatePicker
    v-else
    :model-value="modelValue"
    :input-id="inputId"
    date-format="dd.mm.yy"
    placeholder="Выберите дату и время"
    :manual-input="false"
    show-time
    hour-format="24"
    :step-minute="5"
    :min-date="minDate"
    show-icon
    icon-display="input"
    :invalid="invalid"
    :aria-label="ariaLabel"
    data-testid="field-starts-at"
    @update:model-value="emit('update:modelValue', ($event as Date | null) ?? null)"
    @hide="emit('blur')"
  />
</template>

<style scoped>
/* Нативное поле даты в некоторых браузерах на 1–2 px выше текстового — выравниваем */
.date-time-native {
  height: var(--app-touch-target);
}
</style>
