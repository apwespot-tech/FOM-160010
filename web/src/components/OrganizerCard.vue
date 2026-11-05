<script setup lang="ts">
/**
 * Блок организатора: аватар или инициалы, имя, когда создано мероприятие.
 * Имя и аватар — ссылки на профиль только для записанных и администратора: остальным
 * сервер профиль не отдаст (403), поэтому у них это обычный текст.
 * «Написать» — ссылка на Telegram; сервер отдаёт его только записанным и администратору.
 */
import Tag from 'primevue/tag'
import { computed } from 'vue'
import { RouterLink } from 'vue-router'

import type { PersonRef } from '@/api/events'
import PersonAvatar from '@/components/PersonAvatar.vue'
import { formatCreatedAt } from '@/utils/dates'
import { telegramUrl } from '@/utils/format'

const props = withDefaults(
  defineProps<{
    organizer: PersonRef
    createdAt: string
    /** false — это сам организатор, писать себе не нужно */
    canWrite?: boolean
    /** Профиль организатора доступен зрителю (записан или администратор) */
    linked?: boolean
  }>(),
  { canWrite: true, linked: false },
)

// Ссылка или обычный элемент — одна разметка для обоих случаев
const linkTag = computed(() => (props.linked ? RouterLink : 'span'))
const linkAttrs = computed(() => (props.linked ? { to: `/users/${props.organizer.id}` } : {}))
</script>

<template>
  <section class="organizer" data-testid="organizer-card">
    <component
      :is="linkTag"
      v-bind="linkAttrs"
      class="organizer__avatar-link"
      :aria-label="linked ? `Профиль: ${organizer.name}` : undefined"
      :tabindex="linked ? -1 : undefined"
      data-testid="organizer-avatar"
    >
      <PersonAvatar
        :name="organizer.name"
        :user-id="organizer.id"
        :avatar-id="organizer.avatar_id"
        size="large"
      />
    </component>
    <div class="organizer__info">
      <div class="organizer__name-row">
        <component
          :is="linkTag"
          v-bind="linkAttrs"
          class="organizer__name app-break"
          :class="{ 'organizer__name--link': linked }"
          data-testid="organizer-name"
        >
          {{ organizer.name }}
        </component>
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
  color: inherit;
  text-decoration: none;
}

.organizer__name--link:hover,
.organizer__name--link:focus-visible {
  color: var(--p-primary-700);
  text-decoration: underline;
}

.organizer__avatar-link {
  display: inline-flex;
  border-radius: 50%;
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
