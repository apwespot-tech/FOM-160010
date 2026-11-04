<script setup lang="ts">
/**
 * Главная: список мероприятий. Вкладки «Найти компанию / Участвую / Организую»,
 * период для своих вкладок, фильтры и «Показать ещё». Состояние хранится в адресе.
 */
import Button from 'primevue/button'
import Message from 'primevue/message'
import ProgressSpinner from 'primevue/progressspinner'
import SelectButton from 'primevue/selectbutton'
import Tab from 'primevue/tab'
import TabList from 'primevue/tablist'
import Tabs from 'primevue/tabs'
import { computed, onBeforeUnmount } from 'vue'
import { RouterView } from 'vue-router'

import type { EventPeriod } from '@/api/events'
import EventFilters from '@/components/EventFilters.vue'
import EventListCard from '@/components/EventListCard.vue'
import { useCreateEventDialog } from '@/composables/useCreateEventDialog'
import { provideEventListUpdates, useEventList } from '@/composables/useEventList'
import { useEventListQuery, type EventTab } from '@/composables/useEventListQuery'

const { state, params, activeFilters, update, resetFilters } = useEventListQuery()
const { items, total, loading, error, reload, loadMore, replaceItem, removeItem } =
  useEventList(params)
provideEventListUpdates({ replaceItem, removeItem })
const { open: openCreate, onEventCreated } = useCreateEventDialog()
// Мероприятие создано, а окно создания ещё открыто (не сохранились фото) — показать его в списке
onBeforeUnmount(onEventCreated(() => void reload()))

const periodOptions: { value: EventPeriod; label: string }[] = [
  { value: 'upcoming', label: 'Предстоящие' },
  { value: 'past', label: 'Прошедшие' },
]

const hasMore = computed(() => items.value.length < total.value)

const emptyText = computed(() => {
  if (state.value.tab === 'joined') {
    return state.value.period === 'past'
      ? 'Прошедших мероприятий с вашим участием нет'
      : 'Вы пока никуда не записаны'
  }
  if (state.value.tab === 'organized') {
    return state.value.period === 'past'
      ? 'Прошедших мероприятий нет'
      : 'Вы ещё не создали мероприятий'
  }
  return 'Подходящих мероприятий нет'
})

function onTab(value: string | number) {
  update({ tab: value as EventTab })
}

function onPeriod(value: unknown) {
  if (value === 'upcoming' || value === 'past') update({ period: value })
}

function retry() {
  void (items.value.length ? loadMore() : reload())
}
</script>

<template>
  <main class="events-page">
    <div class="events-page__inner">
      <h1 class="events-page__title">Мероприятия</h1>

      <Tabs :value="state.tab" class="events-page__tabs" @update:value="onTab">
        <TabList>
          <Tab value="find" data-testid="tab-find">Найти компанию</Tab>
          <Tab value="joined" data-testid="tab-joined">Участвую</Tab>
          <Tab value="organized" data-testid="tab-organized">Организую</Tab>
        </TabList>
      </Tabs>

      <div class="events-page__toolbar">
        <SelectButton
          v-if="state.tab !== 'find'"
          :model-value="state.period"
          :options="periodOptions"
          option-label="label"
          option-value="value"
          :allow-empty="false"
          aria-label="Период"
          class="events-page__period"
          data-testid="period"
          @update:model-value="onPeriod"
        />
        <EventFilters
          :category-id="state.categoryId"
          :from="state.from"
          :to="state.to"
          :min-free-places="state.minFreePlaces"
          :active-count="activeFilters"
          @change="update"
          @reset="resetFilters"
        />
      </div>

      <div class="events-page__list" data-testid="event-list">
        <EventListCard v-for="event in items" :key="event.id" :event="event" />
      </div>

      <div v-if="loading" class="events-page__status" data-testid="events-loading">
        <ProgressSpinner style="width: 40px; height: 40px" stroke-width="4" aria-label="Загрузка" />
      </div>

      <div v-else-if="error" class="events-page__status" data-testid="events-error">
        <Message severity="error" :closable="false">Не удалось загрузить мероприятия</Message>
        <Button type="button" label="Повторить" icon="pi pi-refresh" outlined @click="retry" />
      </div>

      <div v-else-if="!items.length" class="events-page__empty" data-testid="events-empty">
        <p class="events-page__empty-text">{{ emptyText }}</p>
        <Button
          v-if="state.tab === 'find' && activeFilters"
          type="button"
          label="Сбросить фильтры"
          outlined
          data-testid="empty-reset-filters"
          @click="resetFilters"
        />
        <Button
          v-else-if="state.tab === 'organized' && state.period === 'upcoming'"
          type="button"
          label="Создать мероприятие"
          icon="pi pi-plus"
          data-testid="empty-create"
          @click="openCreate"
        />
      </div>

      <div v-else-if="hasMore" class="events-page__status">
        <Button
          type="button"
          label="Показать ещё"
          outlined
          data-testid="load-more"
          @click="loadMore"
        />
      </div>
    </div>

    <!-- Окно мероприятия (дочерний маршрут /events/:id) поверх списка -->
    <RouterView />
  </main>
</template>

<style scoped>
.events-page {
  flex: 1;
  width: 100%;
  padding: var(--app-gutter);
}

.events-page__inner {
  max-width: 1200px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.events-page__title {
  margin: 0;
  font-size: 1.5rem;
  font-weight: 600;
}

/* Вкладки прокручиваются внутри себя, страница — нет */
.events-page__tabs {
  min-width: 0;
}

.events-page__tabs :deep(.p-tablist-tab-list) {
  background: transparent;
}

.events-page__tabs :deep(.p-tab) {
  min-height: var(--app-touch-target);
  white-space: nowrap;
}

/* На телефоне три вкладки помещаются без прокрутки */
@media (max-width: 639px) {
  .events-page__tabs :deep(.p-tab) {
    padding: 0 10px;
    font-size: 0.875rem;
  }
}

.events-page__toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.events-page__period :deep(.p-togglebutton) {
  min-height: var(--app-touch-target);
}

.events-page__list {
  display: grid;
  gap: 12px;
}

@media (min-width: 640px) {
  .events-page__list {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 16px;
  }
}

@media (min-width: 1024px) {
  .events-page__list {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

.events-page__status {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 16px 0;
}

.events-page__empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
  padding: 48px 16px;
  text-align: center;
  background: var(--p-surface-0);
  border: 1px dashed var(--app-border);
  border-radius: 12px;
}

.events-page__empty-text {
  margin: 0;
  color: var(--app-text-muted);
}
</style>
