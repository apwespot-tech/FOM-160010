<script setup lang="ts">
/** Карточка мероприятия в списке — ссылка на его страницу. */
import Tag from 'primevue/tag'
import { computed } from 'vue'
import { RouterLink } from 'vue-router'

import type { EventItem } from '@/api/events'
import { useSessionStore } from '@/stores/session'
import { formatEventDate } from '@/utils/dates'
import { formatMinAge, formatPlaces } from '@/utils/format'

const props = defineProps<{ event: EventItem }>()

const session = useSessionStore()
const isOrganizer = computed(() => props.event.organizer.id === session.profile?.id)
</script>

<template>
  <RouterLink :to="`/events/${event.id}`" class="event-card" data-testid="event-card">
    <div class="event-card__top">
      <span class="event-card__category">{{ event.category.name }}</span>
      <time class="event-card__date" :datetime="event.starts_at">
        {{ formatEventDate(event.starts_at) }}
      </time>
    </div>
    <h2 class="event-card__title app-break">{{ event.title }}</h2>
    <p class="event-card__place app-break">
      <i class="pi pi-map-marker" aria-hidden="true" />
      {{ event.place }}
    </p>
    <div class="event-card__bottom">
      <span
        class="event-card__places"
        :class="{ 'event-card__places--full': event.is_full }"
        data-testid="event-card-places"
      >
        {{ formatPlaces(event.free_places, event.max_participants) }}
      </span>
      <span class="event-card__tags">
        <Tag v-if="event.min_age > 0" :value="formatMinAge(event.min_age)" severity="secondary" />
        <Tag
          v-if="isOrganizer"
          value="Вы организатор"
          class="event-card__mark"
          data-testid="event-card-organizer"
        />
        <Tag
          v-else-if="event.is_joined"
          value="Вы записаны"
          class="event-card__mark"
          data-testid="event-card-joined"
        />
      </span>
    </div>
  </RouterLink>
</template>

<style scoped>
.event-card {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 16px;
  background: var(--p-surface-0);
  border: 1px solid var(--app-border);
  border-radius: 12px;
  color: inherit;
  text-decoration: none;
  transition: border-color 0.15s;
}

.event-card:hover,
.event-card:focus-visible {
  border-color: var(--p-primary-300);
}

.event-card:focus-visible {
  outline: 2px solid var(--p-primary-600);
  outline-offset: 2px;
}

.event-card__top {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  gap: 4px 12px;
  font-size: 0.875rem;
}

.event-card__category {
  color: var(--p-primary-700);
  font-weight: 500;
}

.event-card__date {
  color: var(--app-text-muted);
}

.event-card__title {
  margin: 0;
  font-size: 1.125rem;
  font-weight: 600;
  line-height: 1.3;
}

.event-card__place {
  margin: 0;
  color: var(--app-text-muted);
}

.event-card__bottom {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-top: 4px;
}

.event-card__places {
  font-weight: 500;
}

.event-card__places--full {
  color: var(--app-text-muted);
}

.event-card__tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

/* Оранжевый — только акцент: отметки «Вы записаны» и «Вы организатор» */
.event-card__mark {
  background: var(--app-accent-soft);
  color: var(--app-accent-text);
  border: 1px solid var(--app-accent-border);
}
</style>
