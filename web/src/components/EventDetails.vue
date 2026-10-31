<script setup lang="ts">
/**
 * Карточка мероприятия: просмотр и редактирование в одной раскладке
 * (стандарт «Окна и карточки с данными», docs/rules.md). По «Редактировать»
 * значения заменяются полями на своих местах; организатор и число записавшихся — текстом.
 */
import Button from 'primevue/button'
import Message from 'primevue/message'
import Tag from 'primevue/tag'
import { nextTick, ref } from 'vue'

import type { EventItem } from '@/api/events'
import EventFieldInput from '@/components/EventFieldInput.vue'
import { provideEventForm } from '@/composables/eventFormContext'
import { useEventForm } from '@/composables/useEventForm'
import { formatDuration, formatEventDate } from '@/utils/dates'
import { formatMinAge } from '@/utils/format'

const props = defineProps<{
  event: EventItem
  /** Показывать «Редактировать» и «Удалить» */
  canManage: boolean
  isPast: boolean
}>()
const emit = defineEmits<{ saved: [event: EventItem, changed: boolean]; delete: [] }>()

const editing = ref(false)
const root = ref<HTMLFormElement | null>(null)
const controller = useEventForm({ getInitial: () => props.event })
provideEventForm(controller)
const { generalError, saving, requiredFilled, reset, submit } = controller

async function startEdit() {
  reset()
  editing.value = true
  await nextTick()
  root.value?.querySelector<HTMLInputElement>('#event-title')?.focus()
}

function cancel() {
  reset()
  editing.value = false
}

async function save() {
  if (!editing.value) return
  const before = props.event
  const event = await submit()
  if (!event) return
  editing.value = false
  emit('saved', event, event !== before)
}
</script>

<template>
  <form
    ref="root"
    class="event-details"
    novalidate
    data-testid="event-details"
    @submit.prevent="save"
  >
    <div class="event-details__head">
      <div class="event-details__category">
        <EventFieldInput
          v-if="editing"
          field="categoryId"
          input-id="event-category"
          aria-label="Категория"
        />
        <span v-else class="event-details__category-name" data-testid="event-category">
          {{ event.category.name }}
        </span>
      </div>
      <Tag v-if="isPast" value="Мероприятие прошло" severity="secondary" data-testid="event-past" />
    </div>

    <div class="event-details__title">
      <EventFieldInput v-if="editing" field="title" input-id="event-title" aria-label="Название" />
      <h1 v-else class="app-break" data-testid="event-title">{{ event.title }}</h1>
    </div>

    <dl class="event-details__rows">
      <div class="event-details__row">
        <dt><label for="event-starts-at">Когда</label></dt>
        <dd v-if="editing"><EventFieldInput field="startsAt" input-id="event-starts-at" /></dd>
        <dd v-else data-testid="event-starts-at">{{ formatEventDate(event.starts_at) }}</dd>
      </div>
      <div class="event-details__row">
        <dt><label for="event-duration">Длительность</label></dt>
        <dd v-if="editing">
          <EventFieldInput field="durationMinutes" input-id="event-duration" />
        </dd>
        <dd
          v-else
          :class="{ 'event-details__empty': event.duration_minutes === null }"
          data-testid="event-duration"
        >
          {{
            event.duration_minutes === null ? 'не указана' : formatDuration(event.duration_minutes)
          }}
        </dd>
      </div>
      <div class="event-details__row">
        <dt><label for="event-place">Где</label></dt>
        <dd v-if="editing"><EventFieldInput field="place" input-id="event-place" /></dd>
        <dd v-else class="app-break" data-testid="event-place">{{ event.place }}</dd>
      </div>
      <div class="event-details__row">
        <dt><span id="event-age-label">Возраст</span></dt>
        <dd v-if="editing">
          <EventFieldInput field="minAge" input-id="event-age" aria-label="Возраст" />
        </dd>
        <dd v-else data-testid="event-age">
          {{ event.min_age > 0 ? formatMinAge(event.min_age) : 'без ограничений' }}
        </dd>
      </div>
      <div class="event-details__row">
        <dt><label for="event-max">Места</label></dt>
        <dd v-if="editing" class="event-details__places-edit">
          <span class="event-details__places-count">{{ event.participants_count }} из</span>
          <EventFieldInput field="maxParticipants" input-id="event-max" />
        </dd>
        <dd v-else data-testid="event-places">
          {{ event.participants_count }} из {{ event.max_participants }}
          <span v-if="event.is_full" class="event-details__muted">— мест нет</span>
        </dd>
      </div>
      <div class="event-details__row">
        <dt>Организатор</dt>
        <dd class="app-break" data-testid="event-organizer">{{ event.organizer.name }}</dd>
      </div>
      <div class="event-details__row event-details__row--wide">
        <dt><label for="event-description">Описание</label></dt>
        <dd v-if="editing"><EventFieldInput field="description" input-id="event-description" /></dd>
        <dd v-else class="event-details__description app-break" data-testid="event-description">
          {{ event.description }}
        </dd>
      </div>
    </dl>

    <!-- Запись и отказ: место не меняется при редактировании -->
    <slot name="participation" :editing="editing" />

    <Message v-if="editing && generalError" severity="error" :closable="false">
      {{ generalError }}
    </Message>

    <!-- «Редактировать»/«Удалить» и «Сохранить»/«Отмена» — на одном и том же месте -->
    <div
      v-if="canManage"
      class="app-actions app-actions--inline event-details__actions"
      data-testid="event-manage-actions"
    >
      <template v-if="editing">
        <Button
          type="submit"
          label="Сохранить"
          icon="pi pi-check"
          :loading="saving"
          :disabled="!requiredFilled || saving"
          data-testid="event-save"
        />
        <Button
          type="button"
          label="Отмена"
          severity="secondary"
          outlined
          data-testid="event-cancel"
          @click="cancel"
        />
      </template>
      <template v-else>
        <Button
          type="button"
          label="Редактировать"
          icon="pi pi-pencil"
          data-testid="event-edit"
          @click="startEdit"
        />
        <Button
          type="button"
          label="Удалить"
          icon="pi pi-trash"
          severity="danger"
          outlined
          data-testid="event-delete"
          @click="emit('delete')"
        />
      </template>
    </div>
  </form>
</template>

<style scoped>
.event-details {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.event-details__head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  min-height: var(--app-touch-target);
}

.event-details__category {
  min-width: 0;
  flex: 1 1 200px;
  max-width: 280px;
}

.event-details__category-name {
  display: inline-flex;
  align-items: center;
  min-height: var(--app-touch-target);
  color: var(--p-primary-700);
  font-weight: 500;
}

/* Место под название той же высоты, что и поле ввода */
.event-details__title h1 {
  margin: 0;
  min-height: var(--app-touch-target);
  display: flex;
  align-items: center;
  font-size: 1.5rem;
  font-weight: 600;
  line-height: 1.3;
}

.event-details__title :deep(.p-inputtext) {
  font-size: 1.125rem;
  font-weight: 600;
}

.event-details__rows {
  margin: 0;
  display: grid;
  gap: 12px;
}

.event-details__row {
  display: grid;
  gap: 2px;
}

.event-details__row dt {
  color: var(--app-text-muted);
  font-size: 0.875rem;
}

/* Высота значения = высоте поля (44 px), чтобы режимы не меняли размер карточки */
.event-details__row dd {
  margin: 0;
  min-width: 0;
  min-height: var(--app-touch-target);
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.event-details__row dd.event-details__places-edit {
  flex-direction: row;
  align-items: flex-start;
  gap: 8px;
}

.event-details__places-count {
  min-height: var(--app-touch-target);
  display: inline-flex;
  align-items: center;
  white-space: nowrap;
}

.event-details__places-edit > :last-child {
  flex: 1;
  max-width: 200px;
}

/* Описание в просмотре занимает столько же, сколько поле ввода, текст — сверху, как в поле */
.event-details__row dd.event-details__description {
  min-height: var(--app-textarea-min-height);
  justify-content: flex-start;
  padding-top: 10px;
  white-space: pre-line;
}

.event-details__empty,
.event-details__muted {
  color: var(--app-text-muted);
}

.event-details__empty {
  font-style: italic;
}

/* На мобильном пары кнопок — в одну строку по половине ширины, основная справа */
@media (max-width: 639px) {
  .event-details__actions {
    flex-direction: row-reverse;
  }

  .event-details__actions :deep(.p-button) {
    flex: 1 1 0;
    min-width: 0;
  }
}

@media (min-width: 1024px) {
  .event-details__row {
    grid-template-columns: 160px 1fr;
    align-items: start;
    gap: 16px;
  }

  .event-details__row dt {
    min-height: var(--app-touch-target);
    display: flex;
    align-items: center;
  }
}
</style>
