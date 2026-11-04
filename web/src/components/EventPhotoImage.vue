<script setup lang="ts">
/**
 * Фото мероприятия по id: загружается с токеном и берётся из кеша.
 * Пока грузится — нейтральный фон, при ошибке — иконка картинки без текста.
 */
import { usePhotoUrl } from '@/composables/usePhotoUrl'

const props = withDefaults(
  defineProps<{ eventId: string; photoId: string; alt: string; fit?: 'cover' | 'contain' }>(),
  { fit: 'cover' },
)

const { url, failed } = usePhotoUrl(
  () => props.eventId,
  () => props.photoId,
)
</script>

<template>
  <span class="event-photo" :class="`event-photo--${fit}`" data-testid="event-photo">
    <img v-if="url" :src="url" :alt="alt" class="event-photo__img" draggable="false" />
    <i
      v-else-if="failed"
      class="pi pi-image event-photo__fallback"
      aria-hidden="true"
      data-testid="event-photo-failed"
    />
  </span>
</template>

<style scoped>
.event-photo {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 100%;
  overflow: hidden;
  background: var(--p-surface-100);
}

.event-photo__img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.event-photo--contain {
  background: transparent;
}

.event-photo--contain .event-photo__img {
  object-fit: contain;
}

.event-photo__fallback {
  color: var(--app-text-muted);
  font-size: 1.5rem;
}
</style>
