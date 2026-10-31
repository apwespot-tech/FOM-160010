<script setup lang="ts">
/**
 * Фильтры списка: категория, даты и минимум свободных мест. На мобильной ширине
 * прячутся за кнопкой «Фильтры (N)», которая открывает окно с теми же полями.
 */
import Button from 'primevue/button'
import DatePicker from 'primevue/datepicker'
import Dialog from 'primevue/dialog'
import InputNumber from 'primevue/inputnumber'
import Select from 'primevue/select'
import { computed, ref, watch } from 'vue'

import { useCategories } from '@/composables/useCategories'
import { MAX_FREE_PLACES } from '@/composables/useEventListQuery'
import { useIsMobile } from '@/utils/breakpoints'

const props = defineProps<{
  categoryId: number | null
  from: Date | null
  to: Date | null
  minFreePlaces: number | null
  activeCount: number
}>()
const emit = defineEmits<{
  change: [
    patch: {
      categoryId?: number | null
      from?: Date | null
      to?: Date | null
      minFreePlaces?: number | null
    },
  ]
  reset: []
}>()

const { categories } = useCategories()
const isMobile = useIsMobile()
const dialogVisible = ref(false)

const categoryOptions = computed(() => [{ id: null, name: 'Все категории' }, ...categories.value])

/** Значение календаря из адреса: один день показывается как диапазон [день, день]. */
function rangeFromProps(): (Date | null)[] | null {
  return props.from ? [props.from, props.to ?? props.from] : null
}

/*
 * Своё значение календаря: после первого клика DatePicker ждёт конец диапазона ([день, null]).
 * Фильтр по этому дню применяется сразу, но значение календаря не перезаписывается из адреса,
 * чтобы второй клик мог расширить диапазон.
 */
const range = ref(rangeFromProps())
let selecting = false

watch(
  () => [props.from, props.to],
  () => {
    if (!selecting) range.value = rangeFromProps()
  },
)

function onRange(value: unknown) {
  const [from, to] = Array.isArray(value) ? (value as (Date | null)[]) : []
  range.value = from ? [from, to ?? null] : null
  if (!from) {
    selecting = false
    emit('change', { from: null, to: null })
  } else if (!to) {
    selecting = true
    emit('change', { from, to: from })
  } else {
    selecting = false
    emit('change', { from, to })
  }
}

function onRangeHide() {
  selecting = false
  range.value = rangeFromProps()
}

function onCategory(value: unknown) {
  emit('change', { categoryId: typeof value === 'number' ? value : null })
}

/** InputNumber обновляет модель только при потере фокуса — применяем фильтр уже при вводе */
function onPlacesInput(event: { value: string | number | undefined }) {
  const value = typeof event.value === 'number' ? event.value : Number(event.value)
  onPlaces(Number.isInteger(value) && value > 0 ? value : null)
}

function onPlaces(value: number | null) {
  const places = value !== null && value >= 1 ? Math.min(value, MAX_FREE_PLACES) : null
  if (places !== props.minFreePlaces) emit('change', { minFreePlaces: places })
}
</script>

<template>
  <div v-if="isMobile" class="event-filters event-filters--mobile">
    <Button
      type="button"
      icon="pi pi-filter"
      :label="activeCount ? `Фильтры (${activeCount})` : 'Фильтры'"
      severity="secondary"
      outlined
      data-testid="filters-button"
      @click="dialogVisible = true"
    />
    <Dialog
      v-model:visible="dialogVisible"
      modal
      header="Фильтры"
      dismissable-mask
      :draggable="false"
      class="event-filters__dialog"
    >
      <div class="event-filters__fields">
        <div class="app-field">
          <label for="filter-category-mobile">Категория</label>
          <Select
            input-id="filter-category-mobile"
            :model-value="categoryId"
            :options="categoryOptions"
            option-label="name"
            option-value="id"
            placeholder="Все категории"
            @update:model-value="onCategory"
          />
        </div>
        <div class="app-field">
          <label for="filter-dates-mobile">Даты</label>
          <DatePicker
            input-id="filter-dates-mobile"
            :model-value="range"
            selection-mode="range"
            date-format="dd.mm.yy"
            placeholder="Любые даты"
            :manual-input="false"
            show-button-bar
            @update:model-value="onRange"
            @hide="onRangeHide"
          />
        </div>
        <div class="app-field">
          <label for="filter-places-mobile">Свободных мест от</label>
          <InputNumber
            input-id="filter-places-mobile"
            :model-value="minFreePlaces"
            :min="1"
            :max="MAX_FREE_PLACES"
            :use-grouping="false"
            placeholder="Любое число"
            show-buttons
            button-layout="horizontal"
            increment-button-icon="pi pi-plus"
            decrement-button-icon="pi pi-minus"
            @update:model-value="onPlaces"
            @input="onPlacesInput"
          />
        </div>
      </div>
      <template #footer>
        <div class="app-actions app-actions--inline event-filters__actions">
          <Button type="button" label="Готово" @click="dialogVisible = false" />
          <Button
            type="button"
            label="Сбросить"
            severity="secondary"
            outlined
            :disabled="!activeCount"
            @click="emit('reset')"
          />
        </div>
      </template>
    </Dialog>
  </div>

  <div v-else class="event-filters" data-testid="event-filters">
    <Select
      :model-value="categoryId"
      :options="categoryOptions"
      option-label="name"
      option-value="id"
      placeholder="Все категории"
      aria-label="Категория"
      class="event-filters__category"
      data-testid="filter-category"
      @update:model-value="onCategory"
    />
    <DatePicker
      :model-value="range"
      selection-mode="range"
      date-format="dd.mm.yy"
      placeholder="Любые даты"
      :manual-input="false"
      show-button-bar
      show-icon
      icon-display="input"
      aria-label="Даты"
      class="event-filters__dates"
      data-testid="filter-dates"
      @update:model-value="onRange"
      @hide="onRangeHide"
    />
    <InputNumber
      :model-value="minFreePlaces"
      :min="1"
      :max="MAX_FREE_PLACES"
      :use-grouping="false"
      prefix="Мест от "
      placeholder="Свободных мест от"
      aria-label="Свободных мест от"
      class="event-filters__places"
      data-testid="filter-places"
      @update:model-value="onPlaces"
      @input="onPlacesInput"
    />
    <Button
      v-if="activeCount"
      type="button"
      label="Сбросить"
      text
      data-testid="filters-reset"
      @click="emit('reset')"
    />
  </div>
</template>

<style scoped>
.event-filters {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
}

.event-filters__category {
  width: 220px;
  min-height: var(--app-touch-target);
  align-items: center;
}

.event-filters__dates {
  width: 260px;
}

.event-filters__places {
  width: 190px;
}

.event-filters__places :deep(.p-inputtext) {
  width: 100%;
}

.event-filters__fields {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.event-filters__fields :deep(.p-select),
.event-filters__fields :deep(.p-datepicker),
.event-filters__fields :deep(.p-inputnumber) {
  width: 100%;
  min-height: var(--app-touch-target);
}

.event-filters__fields :deep(.p-inputnumber-button) {
  min-width: var(--app-touch-target);
}

.event-filters__actions {
  width: 100%;
}
</style>

<style>
/* Окно фильтров бывает только на мобильной ширине — по стандарту во весь экран */
.event-filters__dialog.p-dialog {
  width: 100vw;
  height: 100dvh;
  max-height: 100dvh;
  margin: 0;
  border-radius: 0;
}
</style>
