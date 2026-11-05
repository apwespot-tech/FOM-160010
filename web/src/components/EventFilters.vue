<script setup lang="ts">
/**
 * Панель фильтров списка: поиск по названию, город, категория, даты, минимум свободных мест,
 * быстрые фильтры и «Сбросить». На мобильной ширине поиск и быстрые фильтры видны
 * всегда, а остальные поля — в окне «Фильтры (N)».
 */
import Button from 'primevue/button'
import DatePicker from 'primevue/datepicker'
import Dialog from 'primevue/dialog'
import IconField from 'primevue/iconfield'
import InputIcon from 'primevue/inputicon'
import InputNumber from 'primevue/inputnumber'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import { computed, onBeforeUnmount, ref, watch } from 'vue'

import { useCategories } from '@/composables/useCategories'
import { useCities } from '@/composables/useCities'
import { MAX_FREE_PLACES, MAX_SEARCH_LENGTH } from '@/composables/useEventListQuery'
import { useSessionStore } from '@/stores/session'
import { useIsMobile } from '@/utils/breakpoints'
import { currentWeekRange, toIsoDate } from '@/utils/dates'

const props = defineProps<{
  cityId: number | null
  categoryId: number | null
  from: Date | null
  to: Date | null
  minFreePlaces: number | null
  search: string
  /** Активных полей в окне «Фильтры» (без поиска) */
  activeCount: number
  /** Активен поиск или любой фильтр — показывается «Сбросить» */
  hasActive: boolean
}>()
const emit = defineEmits<{
  change: [
    patch: {
      cityId?: number | null
      categoryId?: number | null
      from?: Date | null
      to?: Date | null
      minFreePlaces?: number | null
      search?: string
    },
  ]
  reset: []
}>()

const { categories } = useCategories()
const { cities } = useCities()
const session = useSessionStore()
const isMobile = useIsMobile()
const dialogVisible = ref(false)

const categoryOptions = computed(() => [{ id: null, name: 'Все категории' }, ...categories.value])

/** «Все города», город из профиля с подписью «ваш город», остальные по алфавиту без повтора. */
const cityOptions = computed(() => {
  const own = session.profile?.city ?? null
  return [
    { id: null, name: 'Все города', own: false },
    ...(own ? [{ ...own, own: true }] : []),
    ...cities.value.filter((city) => city.id !== own?.id).map((city) => ({ ...city, own: false })),
  ]
})

function onCity(value: unknown) {
  emit('change', { cityId: typeof value === 'number' ? value : null })
}

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

// --- поиск: запрос через 300 мс после последнего ввода ---

const SEARCH_DELAY_MS = 300
const searchText = ref(props.search)
let searchTimer: ReturnType<typeof setTimeout> | undefined

watch(
  () => props.search,
  (value) => {
    // Адрес поменялся извне («Назад», «Сбросить») — показываем его значение
    if (value !== searchText.value.trim()) searchText.value = value
  },
)

function onSearchInput(value: string | undefined) {
  searchText.value = value ?? ''
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    const search = searchText.value.trim()
    if (search !== props.search) emit('change', { search })
  }, SEARCH_DELAY_MS)
}

onBeforeUnmount(() => clearTimeout(searchTimer))

// --- быстрые фильтры: подсветка вычисляется из текущих значений ---

const freePlacesOn = computed(() => props.minFreePlaces === 1)
const thisWeekOn = computed(() => {
  if (!props.from) return false
  const week = currentWeekRange()
  return (
    toIsoDate(props.from) === toIsoDate(week.from) &&
    toIsoDate(props.to ?? props.from) === toIsoDate(week.to)
  )
})

function toggleFreePlaces() {
  emit('change', { minFreePlaces: freePlacesOn.value ? null : 1 })
}

function toggleThisWeek() {
  if (thisWeekOn.value) {
    emit('change', { from: null, to: null })
  } else {
    const week = currentWeekRange()
    emit('change', { from: week.from, to: week.to })
  }
}

function reset() {
  clearTimeout(searchTimer)
  searchText.value = ''
  emit('reset')
}
</script>

<template>
  <section class="event-filters" aria-label="Фильтры мероприятий" data-testid="event-filters">
    <div class="event-filters__fields">
      <IconField class="event-filters__search">
        <InputIcon class="pi pi-search" />
        <InputText
          :model-value="searchText"
          type="search"
          inputmode="search"
          enterkeyhint="search"
          :maxlength="MAX_SEARCH_LENGTH"
          placeholder="Поиск по названию…"
          aria-label="Поиск по названию"
          data-testid="filter-search"
          @update:model-value="onSearchInput"
        />
      </IconField>

      <template v-if="!isMobile">
        <Select
          :model-value="cityId"
          :options="cityOptions"
          option-label="name"
          option-value="id"
          placeholder="Все города"
          filter
          filter-placeholder="Найти город"
          aria-label="Город"
          class="event-filters__field"
          data-testid="filter-city"
          @update:model-value="onCity"
        >
          <template #option="{ option }">
            <span class="event-filters__city-option" data-testid="filter-city-option">
              {{ option.name }}
              <span v-if="option.own" class="event-filters__city-own">ваш город</span>
            </span>
          </template>
        </Select>
        <Select
          :model-value="categoryId"
          :options="categoryOptions"
          option-label="name"
          option-value="id"
          placeholder="Все категории"
          aria-label="Категория"
          class="event-filters__field"
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
          class="event-filters__field"
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
          class="event-filters__field"
          data-testid="filter-places"
          @update:model-value="onPlaces"
          @input="onPlacesInput"
        />
      </template>
    </div>

    <div class="event-filters__quick">
      <span class="event-filters__quick-label">Быстрый фильтр:</span>
      <button
        type="button"
        class="event-filters__chip"
        :class="{ 'event-filters__chip--on': freePlacesOn }"
        :aria-pressed="freePlacesOn"
        data-testid="quick-free-places"
        @click="toggleFreePlaces"
      >
        Есть свободные места
      </button>
      <button
        type="button"
        class="event-filters__chip"
        :class="{ 'event-filters__chip--on': thisWeekOn }"
        :aria-pressed="thisWeekOn"
        data-testid="quick-this-week"
        @click="toggleThisWeek"
      >
        На этой неделе
      </button>

      <span class="event-filters__spacer" />

      <Button
        v-if="isMobile"
        type="button"
        icon="pi pi-filter"
        :label="activeCount ? `Фильтры (${activeCount})` : 'Фильтры'"
        severity="secondary"
        outlined
        data-testid="filters-button"
        @click="dialogVisible = true"
      />
      <Button
        v-if="hasActive"
        type="button"
        icon="pi pi-refresh"
        label="Сбросить"
        text
        data-testid="filters-reset"
        @click="reset"
      />
    </div>

    <Dialog
      v-if="isMobile"
      v-model:visible="dialogVisible"
      modal
      header="Фильтры"
      dismissable-mask
      :draggable="false"
      class="event-filters__dialog"
    >
      <div class="event-filters__dialog-fields">
        <div class="app-field">
          <label for="filter-city-mobile">Город</label>
          <Select
            input-id="filter-city-mobile"
            :model-value="cityId"
            :options="cityOptions"
            option-label="name"
            option-value="id"
            placeholder="Все города"
            filter
            filter-placeholder="Найти город"
            data-testid="filter-city-mobile"
            @update:model-value="onCity"
          >
            <template #option="{ option }">
              <span class="event-filters__city-option">
                {{ option.name }}
                <span v-if="option.own" class="event-filters__city-own">ваш город</span>
              </span>
            </template>
          </Select>
        </div>
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
            :disabled="!hasActive"
            @click="reset"
          />
        </div>
      </template>
    </Dialog>
  </section>
</template>

<style scoped>
/* Панель-карточка: строка полей и строка быстрых фильтров */
.event-filters {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 16px;
  background: var(--p-surface-0);
  border: 1px solid var(--app-border);
  border-radius: 16px;
}

.event-filters__fields {
  display: grid;
  gap: 12px;
}

@media (min-width: 640px) {
  .event-filters__fields {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (min-width: 1024px) {
  .event-filters__fields {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }

  /* Пять полей в одну строку на 1024 px не помещаются: поиск — отдельной строкой */
  .event-filters__search {
    grid-column: 1 / -1;
  }
}

.event-filters__city-option {
  display: flex;
  align-items: baseline;
  gap: 8px;
}

.event-filters__city-own {
  color: var(--app-text-muted);
  font-size: 0.8125rem;
}

.event-filters__search,
.event-filters__field {
  width: 100%;
  min-width: 0;
  min-height: var(--app-touch-target);
}

.event-filters__search :deep(.p-inputtext),
.event-filters__field :deep(.p-inputtext) {
  width: 100%;
  min-height: var(--app-touch-target);
}

.event-filters__field:deep(.p-select-label) {
  display: flex;
  align-items: center;
}

.event-filters__quick {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  padding-top: 12px;
  border-top: 1px solid var(--app-border);
}

.event-filters__quick-label {
  color: var(--app-text-muted);
  font-size: 0.875rem;
}

@media (max-width: 639px) {
  .event-filters__quick-label {
    flex-basis: 100%;
  }
}

.event-filters__chip {
  min-height: var(--app-touch-target);
  padding: 0 12px;
  border: 1px solid var(--app-border);
  border-radius: 8px;
  background: var(--p-surface-100);
  color: var(--p-text-color);
  font: inherit;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
}

@media (min-width: 640px) and (pointer: fine) {
  .event-filters__chip {
    min-height: 36px;
  }
}

.event-filters__chip:hover {
  border-color: var(--p-primary-300);
}

.event-filters__chip:focus-visible {
  outline: 2px solid var(--p-primary-600);
  outline-offset: 2px;
}

.event-filters__chip--on {
  background: var(--p-primary-50);
  border-color: var(--p-primary-300);
  color: var(--p-primary-700);
}

.event-filters__spacer {
  flex: 1;
}

.event-filters__dialog-fields {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.event-filters__dialog-fields :deep(.p-select),
.event-filters__dialog-fields :deep(.p-datepicker),
.event-filters__dialog-fields :deep(.p-inputnumber) {
  width: 100%;
  min-height: var(--app-touch-target);
}

.event-filters__dialog-fields :deep(.p-inputnumber-button) {
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
