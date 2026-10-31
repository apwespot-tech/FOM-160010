<script setup lang="ts">
/**
 * Поле даты рождения: на мобильной ширине — нативный выбор даты (системное колесо),
 * он удобнее на сенсорном экране; на планшете и компьютере — DatePicker с ручным вводом.
 * Значение одно (Date), поэтому при смене ширины введённая дата не теряется.
 */
import DatePicker from 'primevue/datepicker'
import InputText from 'primevue/inputtext'

import { useIsMobile } from '@/utils/breakpoints'
import { fromIsoDate, MIN_BIRTH_DATE, startOfToday, toIsoDate } from '@/utils/dates'

defineProps<{
  modelValue: Date | null
  inputId: string
  invalid?: boolean
  ariaLabel?: string
}>()
const emit = defineEmits<{ 'update:modelValue': [value: Date | null] }>()

const isMobile = useIsMobile()
const maxDate = startOfToday()

function onNativeInput(value: string | undefined) {
  emit('update:modelValue', value ? fromIsoDate(value) : null)
}
</script>

<template>
  <InputText
    v-if="isMobile"
    :id="inputId"
    type="date"
    :model-value="modelValue ? toIsoDate(modelValue) : ''"
    :min="toIsoDate(MIN_BIRTH_DATE)"
    :max="toIsoDate(maxDate)"
    :invalid="invalid"
    :aria-label="ariaLabel"
    class="birth-date-native"
    data-testid="field-birth-date-native"
    @update:model-value="onNativeInput"
  />
  <DatePicker
    v-else
    :model-value="modelValue"
    :input-id="inputId"
    date-format="dd.mm.yy"
    placeholder="ДД.ММ.ГГГГ"
    :min-date="MIN_BIRTH_DATE"
    :max-date="maxDate"
    show-icon
    icon-display="input"
    :invalid="invalid"
    :aria-label="ariaLabel"
    data-testid="field-birth-date"
    @update:model-value="emit('update:modelValue', ($event as Date | null) ?? null)"
  />
</template>

<style scoped>
/* Нативное поле даты в некоторых браузерах на 1–2 px выше текстового — выравниваем */
.birth-date-native {
  height: var(--app-touch-target);
}
</style>
