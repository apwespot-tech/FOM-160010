<script setup lang="ts">
/** Список участников мероприятия; автору и админу — «Исключить» у каждого, кроме организатора. */
import Button from 'primevue/button'
import Tag from 'primevue/tag'

import type { Participant } from '@/api/events'

defineProps<{
  participants: Participant[] | null
  organizerId: string
  /** Список доступен (записан или администратор) */
  visible: boolean
  canRemove: boolean
}>()
const emit = defineEmits<{ remove: [participant: Participant] }>()
</script>

<template>
  <section class="participants" data-testid="participants">
    <h2 class="participants__title">Участники</h2>
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
        <span class="participants__name app-break">{{ participant.name }}</span>
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
  margin: 0 0 12px;
  font-size: 1.125rem;
  font-weight: 600;
}

.participants__hint {
  margin: 0;
  color: var(--app-text-muted);
}

.participants__list {
  margin: 0;
  padding: 0;
  list-style: none;
}

.participants__item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  min-height: var(--app-touch-target);
  border-bottom: 1px solid var(--app-border);
}

.participants__item:last-child {
  border-bottom: none;
}

.participants__name {
  min-width: 0;
}
</style>
