<script setup lang="ts">
/**
 * Карточка мероприятия в списке — ссылка на его окно. Обложка с тегом категории,
 * отметкой и датой; ниже название, возраст, место, места, статус и полоса заполненности.
 */
import { computed } from 'vue'
import { RouterLink, useRoute } from 'vue-router'

import type { EventItem } from '@/api/events'
import CategoryTag from '@/components/CategoryTag.vue'
import EventCover from '@/components/EventCover.vue'
import { useSessionStore } from '@/stores/session'
import { formatEventDate } from '@/utils/dates'
import { formatMinAge, formatPlaces } from '@/utils/format'

const props = defineProps<{ event: EventItem }>()

const session = useSessionStore()
const route = useRoute()
const isOrganizer = computed(() => props.event.organizer.id === session.profile?.id)

type CardState = 'organizer' | 'joined' | 'full' | 'free'

/** Приоритет: своё -> записан -> заполнено -> свободно */
const cardState = computed<CardState>(() => {
  if (isOrganizer.value) return 'organizer'
  if (props.event.is_joined) return 'joined'
  if (props.event.is_full) return 'full'
  return 'free'
})

const STATUS: Record<CardState, string> = {
  organizer: 'Организатор',
  joined: 'Записан',
  full: 'Заполнено',
  free: 'Свободно',
}

const MARK: Record<CardState, string | null> = {
  organizer: 'Вы организатор',
  joined: 'Вы записаны',
  full: 'Мест нет',
  free: null,
}

const filled = computed(() => {
  const { participants_count: count, max_participants: max } = props.event
  return max > 0 ? Math.min(100, Math.round((count / max) * 100)) : 0
})
const mainPhotoId = computed(() => props.event.photos[0]?.id ?? null)
</script>

<template>
  <!-- С текущим query: список под окном сохраняет вкладку и фильтры -->
  <RouterLink
    :to="{ path: `/events/${event.id}`, query: route.query }"
    class="event-card"
    :class="`event-card--${cardState}`"
    data-testid="event-card"
  >
    <EventCover
      :event-id="event.id"
      :photo-id="mainPhotoId"
      :category="event.category"
      :alt="event.title"
    >
      <template #top-start>
        <CategoryTag :category="event.category" />
      </template>
      <template #top-end>
        <span
          v-if="MARK[cardState]"
          class="event-card__mark"
          :class="`event-card__mark--${cardState}`"
          :data-testid="
            cardState === 'organizer'
              ? 'event-card-organizer'
              : cardState === 'joined'
                ? 'event-card-joined'
                : 'event-card-full'
          "
        >
          <i v-if="cardState !== 'full'" class="pi pi-check" aria-hidden="true" />
          {{ MARK[cardState] }}
        </span>
      </template>
      <template #bottom>
        <time class="event-card__date" :datetime="event.starts_at" data-testid="event-card-date">
          <i class="pi pi-calendar" aria-hidden="true" />
          {{ formatEventDate(event.starts_at) }}
        </time>
      </template>
    </EventCover>

    <div class="event-card__body">
      <div class="event-card__head">
        <h2 class="event-card__title app-break">{{ event.title }}</h2>
        <span v-if="event.min_age > 0" class="event-card__age" data-testid="event-card-age">
          {{ formatMinAge(event.min_age) }}
        </span>
      </div>
      <p class="event-card__place app-break">
        <i class="pi pi-map-marker" aria-hidden="true" />
        <span data-testid="event-card-place">{{ event.city.name }}, {{ event.place }}</span>
      </p>

      <div class="event-card__footer">
        <div class="event-card__places-row">
          <span
            class="event-card__places"
            :class="{ 'event-card__places--full': event.is_full }"
            data-testid="event-card-places"
          >
            {{ formatPlaces(event.free_places, event.max_participants) }}
          </span>
          <span
            class="event-card__status"
            :class="`event-card__status--${cardState}`"
            data-testid="event-card-status"
          >
            {{ STATUS[cardState] }}
          </span>
        </div>
        <div
          class="event-card__bar"
          role="progressbar"
          :aria-valuenow="filled"
          aria-valuemin="0"
          aria-valuemax="100"
          :aria-label="`Занято ${event.participants_count} из ${event.max_participants} мест`"
          data-testid="event-card-bar"
        >
          <span class="event-card__bar-fill" :style="{ width: `${filled}%` }" />
        </div>
      </div>
    </div>
  </RouterLink>
</template>

<style scoped>
.event-card {
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: var(--p-surface-0);
  border: 1px solid var(--app-border);
  border-radius: 16px;
  color: inherit;
  text-decoration: none;
  transition:
    border-color 0.15s,
    box-shadow 0.15s;
}

.event-card:hover {
  border-color: var(--p-primary-200);
  box-shadow: 0 6px 20px rgb(15 23 42 / 0.08);
}

.event-card:focus-visible {
  outline: 2px solid var(--p-primary-600);
  outline-offset: 2px;
}

/* Отметки на обложке — сплошные плашки, без градиентов */
.event-card__mark {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  flex-shrink: 0;
  padding: 4px 10px;
  border-radius: 8px;
  font-size: 0.8125rem;
  font-weight: 600;
  line-height: 1.3;
  white-space: nowrap;
}

.event-card__mark .pi {
  font-size: 0.75rem;
}

.event-card__mark--organizer,
.event-card__mark--joined {
  background: var(--app-accent);
  color: #fff;
}

.event-card__mark--full {
  background: rgb(15 23 42 / 0.82);
  color: #fff;
}

.event-card__date {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  max-width: 100%;
  padding: 4px 10px;
  border-radius: 8px;
  background: rgb(0 0 0 / 0.55);
  color: #fff;
  font-size: 0.8125rem;
  font-weight: 600;
  white-space: nowrap;
}

.event-card__body {
  display: flex;
  flex-direction: column;
  gap: 8px;
  flex: 1;
  padding: 16px 20px 20px;
}

.event-card__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.event-card__title {
  margin: 0;
  font-size: 1.125rem;
  font-weight: 700;
  line-height: 1.3;
}

.event-card--organizer .event-card__title,
.event-card--joined .event-card__title {
  color: var(--p-primary-700);
}

.event-card__age {
  flex-shrink: 0;
  padding: 2px 8px;
  border: 1px solid var(--app-border);
  border-radius: 6px;
  background: var(--p-surface-50);
  color: var(--app-text-muted);
  font-size: 0.75rem;
  font-weight: 600;
}

.event-card__place {
  display: flex;
  align-items: baseline;
  gap: 8px;
  margin: 0;
  color: var(--app-text-muted);
  font-size: 0.9375rem;
}

.event-card__footer {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: auto;
  padding-top: 8px;
}

.event-card__places-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.event-card__places {
  font-size: 0.9375rem;
  font-weight: 600;
}

.event-card__places--full {
  color: var(--app-text-muted);
}

.event-card__status {
  padding: 2px 8px;
  border-radius: 6px;
  font-size: 0.8125rem;
  font-weight: 600;
}

.event-card__status--free {
  background: #f0fdf4;
  color: #15803d;
}

.event-card__status--joined,
.event-card__status--organizer {
  background: var(--app-accent-soft);
  color: var(--app-accent-text);
}

.event-card__status--full {
  background: var(--p-surface-100);
  color: var(--app-text-muted);
}

.event-card__bar {
  height: 6px;
  overflow: hidden;
  border-radius: 999px;
  background: var(--p-surface-100);
}

.event-card__bar-fill {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: var(--p-primary-600);
}

.event-card--joined .event-card__bar-fill,
.event-card--organizer .event-card__bar-fill {
  background: var(--app-accent);
}

.event-card--full .event-card__bar-fill {
  background: var(--p-surface-400);
}
</style>
