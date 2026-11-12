<script setup lang="ts">
/**
 * Поле даты рождения: на мобильной ширине — нативный выбор даты (системное колесо),
 * он удобнее на сенсорном экране; на планшете и компьютере — DatePicker с ручным вводом.
 * Значение одно (Date), поэтому при смене ширины введённая дата не теряется.
 * DatePicker молча игнорирует введённую вручную дату вне min/max, поэтому такую дату
 * передаём сами: форма покажет понятную ошибку («с 14 лет», «в будущем»), а не пустое поле.
 */
import DatePicker from 'primevue/datepicker'
import InputText from 'primevue/inputtext'

import { useIsMobile } from '@/utils/breakpoints'
import { fromIsoDate, maxBirthDate, MIN_BIRTH_DATE, toIsoDate } from '@/utils/dates'

defineProps<{
  modelValue: Date | null
  inputId: string
  invalid?: boolean
  ariaLabel?: string
}>()
const emit = defineEmits<{ 'update:modelValue': [value: Date | null]; blur: [] }>()

const isMobile = useIsMobile()
const maxDate = maxBirthDate()

const TYPED_DATE_RE = /^(\d{2})\.(\d{2})\.(\d{4})$/

/** «ДД.ММ.ГГГГ» -> Date; несуществующая дата (31.02) — null. */
function parseTyped(text: string): Date | null {
  const match = TYPED_DATE_RE.exec(text.trim())
  if (!match) return null
  const [day, month, year] = [Number(match[1]), Number(match[2]), Number(match[3])]
  const date = new Date(year, month - 1, day)
  return date.getFullYear() === year && date.getMonth() === month - 1 && date.getDate() === day
    ? date
    : null
}

function onTypedInput(event: Event) {
  const date = parseTyped((event.target as HTMLInputElement).value)
  // Дату в диапазоне DatePicker передаст сам
  if (date && (date < MIN_BIRTH_DATE || date > maxDate)) emit('update:modelValue', date)
}

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
    @blur="emit('blur')"
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
    @input="onTypedInput"
    @blur="emit('blur')"
  />
</template>

<style scoped>
/* Нативное поле даты в некоторых браузерах на 1–2 px выше текстового — выравниваем */
.birth-date-native {
  height: var(--app-touch-target);
}
</style>
