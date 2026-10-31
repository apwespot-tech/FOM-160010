<script setup lang="ts">
/**
 * Блок организатора: фото или инициалы, имя, когда создано мероприятие.
 * «Написать» — ссылка на Telegram; сервер отдаёт его только записанным и администратору.
 */
import Tag from 'primevue/tag'

import type { PersonRef } from '@/api/events'
import PersonAvatar from '@/components/PersonAvatar.vue'
import { formatCreatedAt } from '@/utils/dates'
import { telegramUrl } from '@/utils/format'

/** canWrite: false — это сам организатор, писать себе не нужно */
withDefaults(defineProps<{ organizer: PersonRef; createdAt: string; canWrite?: boolean }>(), {
  canWrite: true,
})
</script>

<template>
  <section class="organizer" data-testid="organizer-card">
    <PersonAvatar :name="organizer.name" :photo-url="organizer.photo_url" size="large" />
    <div class="organizer__info">
      <div class="organizer__name-row">
        <span class="organizer__name app-break" data-testid="organizer-name">
          {{ organizer.name }}
        </span>
        <Tag value="Организатор" class="organizer__tag" />
      </div>
      <span class="organizer__created" data-testid="organizer-created">
        Создал мероприятие {{ formatCreatedAt(createdAt) }}
      </span>
    </div>
    <a
      v-if="canWrite && organizer.telegram"
      :href="telegramUrl(organizer.telegram)"
      target="_blank"
      rel="noopener noreferrer"
      class="organizer__write"
      data-testid="organizer-write"
    >
      <i class="pi pi-send" aria-hidden="true" />
      Написать
    </a>
  </section>
</template>

<style scoped>
.organizer {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px 14px;
  padding: 16px;
  background: var(--p-primary-50);
  border: 1px solid var(--p-primary-100);
  border-radius: 12px;
}

.organizer__info {
  flex: 1 1 180px;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.organizer__name-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}

.organizer__name {
  font-weight: 600;
}

.organizer__tag {
  background: var(--p-primary-100);
  color: var(--p-primary-800);
}

.organizer__created {
  color: var(--app-text-muted);
  font-size: 0.875rem;
}

.organizer__write {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-height: var(--app-touch-target);
  padding: 0 12px;
  border-radius: 8px;
  color: var(--p-primary-700);
  font-weight: 600;
  text-decoration: none;
}

.organizer__write:hover,
.organizer__write:focus-visible {
  background: var(--p-primary-100);
}
</style>
