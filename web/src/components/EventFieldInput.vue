<script setup lang="ts">
/**
 * Поле ввода мероприятия по имени поля с ошибкой под ним. Одни и те же поля стоят
 * в окне создания и на местах значений при редактировании на странице мероприятия.
 */
import InputNumber from 'primevue/inputnumber'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import SelectButton from 'primevue/selectbutton'
import Textarea from 'primevue/textarea'
import { computed } from 'vue'

import { MIN_AGE_VALUES, type MinAge } from '@/api/events'
import DateTimeInput from '@/components/DateTimeInput.vue'
import { injectEventForm } from '@/composables/eventFormContext'
import { useCategories } from '@/composables/useCategories'
import { MAX_PARTICIPANTS, type EventField } from '@/composables/useEventForm'
import { formatMinAge } from '@/utils/format'

const props = defineProps<{ field: EventField; inputId: string; ariaLabel?: string }>()

const { form, errorFor, touch, minParticipants } = injectEventForm()
const { categories } = useCategories()

const error = computed(() => errorFor(props.field))
const ageOptions = MIN_AGE_VALUES.map((value) => ({ value, label: formatMinAge(value) }))
/** startsAt -> starts-at: для data-testid полей и ошибок */
const slug = computed(() => props.field.replace(/[A-Z]/g, (c) => `-${c.toLowerCase()}`))

function setCategory(value: unknown) {
  form.categoryId = typeof value === 'number' ? value : null
  touch('categoryId')
}

function setStartsAt(value: Date | null) {
  form.startsAt = value
  touch('startsAt')
}

function setNumber(field: 'durationMinutes' | 'maxParticipants', value: number | null) {
  form[field] = value
  touch(field)
}

function setMinAge(value: unknown) {
  form.minAge = value as MinAge
}
</script>

<template>
  <div class="event-field">
    <InputText
      v-if="field === 'title'"
      :id="inputId"
      v-model="form.title"
      maxlength="100"
      :aria-label="ariaLabel"
      :invalid="error !== null"
      :data-testid="`field-${slug}`"
      @blur="touch('title')"
    />
    <InputText
      v-else-if="field === 'place'"
      :id="inputId"
      v-model="form.place"
      maxlength="200"
      :aria-label="ariaLabel"
      :invalid="error !== null"
      :data-testid="`field-${slug}`"
      @blur="touch('place')"
    />
    <Textarea
      v-else-if="field === 'description'"
      :id="inputId"
      v-model="form.description"
      rows="3"
      auto-resize
      maxlength="2000"
      :aria-label="ariaLabel"
      :invalid="error !== null"
      :data-testid="`field-${slug}`"
      @blur="touch('description')"
    />
    <Select
      v-else-if="field === 'categoryId'"
      :input-id="inputId"
      :model-value="form.categoryId"
      :options="categories"
      option-label="name"
      option-value="id"
      placeholder="Выберите категорию"
      :aria-label="ariaLabel"
      :invalid="error !== null"
      :data-testid="`field-${slug}`"
      @update:model-value="setCategory"
    />
    <DateTimeInput
      v-else-if="field === 'startsAt'"
      :model-value="form.startsAt"
      :input-id="inputId"
      :aria-label="ariaLabel"
      :invalid="error !== null"
      @update:model-value="setStartsAt"
      @blur="touch('startsAt')"
    />
    <InputNumber
      v-else-if="field === 'durationMinutes'"
      :input-id="inputId"
      :model-value="form.durationMinutes"
      :min="1"
      :max="1440"
      :use-grouping="false"
      suffix=" мин"
      placeholder="Не указана"
      :aria-label="ariaLabel"
      :invalid="error !== null"
      :data-testid="`field-${slug}`"
      @update:model-value="setNumber('durationMinutes', $event)"
    />
    <InputNumber
      v-else-if="field === 'maxParticipants'"
      :input-id="inputId"
      :model-value="form.maxParticipants"
      :min="minParticipants"
      :max="MAX_PARTICIPANTS"
      :use-grouping="false"
      show-buttons
      button-layout="horizontal"
      increment-button-icon="pi pi-plus"
      decrement-button-icon="pi pi-minus"
      :aria-label="ariaLabel"
      :invalid="error !== null"
      :data-testid="`field-${slug}`"
      @update:model-value="setNumber('maxParticipants', $event)"
    />
    <SelectButton
      v-else-if="field === 'minAge'"
      :model-value="form.minAge"
      :options="ageOptions"
      option-label="label"
      option-value="value"
      :allow-empty="false"
      :aria-label="ariaLabel ?? 'Возраст'"
      :data-testid="`field-${slug}`"
      @update:model-value="setMinAge"
    />
    <small v-if="error" class="app-field-error" :data-testid="`error-${slug}`">{{ error }}</small>
  </div>
</template>

<style scoped>
.event-field {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

.event-field :deep(.p-inputtext),
.event-field :deep(.p-textarea),
.event-field :deep(.p-select),
.event-field :deep(.p-datepicker),
.event-field :deep(.p-inputnumber) {
  width: 100%;
}

.event-field :deep(.p-textarea) {
  font-size: 1rem;
  min-height: var(--app-textarea-min-height);
}

.event-field :deep(.p-select) {
  min-height: var(--app-touch-target);
  align-items: center;
}

.event-field :deep(.p-inputnumber-button) {
  min-width: var(--app-touch-target);
}

.event-field :deep(.p-selectbutton) {
  display: flex;
}

.event-field :deep(.p-selectbutton .p-togglebutton) {
  flex: 1 1 0;
  min-height: var(--app-touch-target);
}
</style>
