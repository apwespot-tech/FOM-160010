<script setup lang="ts">
/**
 * Участники мероприятия: аватар или инициалы, имя (ссылки на профиль), Telegram ссылкой;
 * автору и админу — «Исключить» у каждого, кроме организатора.
 */
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import { RouterLink } from 'vue-router'

import type { Participant } from '@/api/events'
import PersonAvatar from '@/components/PersonAvatar.vue'
import { telegramUrl } from '@/utils/format'

defineProps<{
  participants: Participant[] | null
  organizerId: string
  count: number
  max: number
  /** Список доступен (записан или администратор) */
  visible: boolean
  canRemove: boolean
}>()
const emit = defineEmits<{ remove: [participant: Participant] }>()
</script>

<template>
  <section class="participants" data-testid="participants">
    <h3 class="participants__title" data-testid="participants-title">
      Участники ({{ count }}/{{ max }})
    </h3>
    <p v-if="!visible" class="participants__hint" data-testid="participants-hidden">
      Список участников виден после записи
    </p>
    <ul v-else-if="participants" class="participants__list" data-testid="participants-list">
      <li
        v-for="participant in participants"
        :key="participant.id"
        class="participants__item"
        data-testid="participant"
      >
        <RouterLink
          :to="`/users/${participant.id}`"
          :aria-label="`Профиль: ${participant.name}`"
          tabindex="-1"
          class="participants__avatar-link"
        >
          <PersonAvatar
            :name="participant.name"
            :user-id="participant.id"
            :avatar-id="participant.avatar_id"
          />
        </RouterLink>
        <div class="participants__info">
          <RouterLink
            :to="`/users/${participant.id}`"
            class="participants__name app-break"
            data-testid="participant-name"
          >
            {{ participant.name }}
          </RouterLink>
          <a
            v-if="participant.telegram"
            :href="telegramUrl(participant.telegram)"
            target="_blank"
            rel="noopener noreferrer"
            class="participants__telegram"
            data-testid="participant-telegram"
          >
            {{ participant.telegram }}
          </a>
        </div>
        <Tag
          v-if="participant.id === organizerId"
          value="Организатор"
          severity="secondary"
          data-testid="participant-organizer"
        />
        <Button
          v-else-if="canRemove"
          type="button"
          label="Исключить"
          icon="pi pi-user-minus"
          severity="danger"
          text
          :aria-label="`Исключить ${participant.name}`"
          data-testid="participant-remove"
          @click="emit('remove', participant)"
        />
      </li>
    </ul>
  </section>
</template>

<style scoped>
.participants__title {
  margin: 0 0 10px;
  color: var(--p-primary-700);
  font-size: 0.75rem;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.participants__hint {
  margin: 0;
  color: var(--app-text-muted);
}

.participants__list {
  margin: 0;
  padding: 0;
  list-style: none;
  display: grid;
  gap: 8px;
}

.participants__item {
  display: flex;
  align-items: center;
  gap: 12px;
  min-height: 60px;
  padding: 8px 12px;
  border: 1px solid var(--app-border);
  border-radius: 12px;
}

.participants__info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.participants__name {
  font-weight: 600;
  color: inherit;
  text-decoration: none;
}

.participants__name:hover,
.participants__name:focus-visible {
  color: var(--p-primary-700);
  text-decoration: underline;
}

.participants__avatar-link {
  display: inline-flex;
  border-radius: 50%;
}

.participants__telegram {
  color: var(--p-primary-700);
  font-size: 0.875rem;
  text-decoration: none;
  overflow-wrap: anywhere;
}

.participants__telegram:hover {
  text-decoration: underline;
}
</style>
