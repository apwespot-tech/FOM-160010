<script setup lang="ts">
/**
 * Обложка карточки 16:9: уменьшенная копия основного фото, а без фото (или если оно
 * не загрузилось) — уменьшенная копия картинки категории. Если не загрузилось и это —
 * нейтральный фон с иконкой категории. Плашки поверх — слоты, без градиентов.
 */
import { computed } from 'vue'

import type { Category } from '@/api/events'
import { loadCategoryCoverUrl, loadPhotoUrl, useImageUrl } from '@/composables/usePhotoUrl'
import { categoryIcon } from '@/utils/categories'

const props = defineProps<{
  eventId: string
  photoId: string | null
  category: Pick<Category, 'id' | 'icon' | 'cover_id'>
  alt: string
}>()

const key = computed(() => `${props.eventId}:${props.photoId ?? ''}:${props.category.cover_id}`)

async function load(): Promise<string> {
  if (props.photoId) {
    try {
      return await loadPhotoUrl(props.eventId, props.photoId, 'thumb')
    } catch {
      // Фото не загрузилось — показываем картинку категории
    }
  }
  return loadCategoryCoverUrl(props.category, 'thumb')
}

const { url, failed } = useImageUrl(() => load, key)
const icon = computed(() => categoryIcon(props.category.icon))
</script>

<template>
  <div class="event-cover" data-testid="event-cover">
    <img
      v-if="url"
      :src="url"
      :alt="alt"
      class="event-cover__img"
      loading="lazy"
      decoding="async"
      draggable="false"
      data-testid="event-cover-img"
    />
    <i
      v-else-if="failed"
      :class="['pi', icon, 'event-cover__fallback']"
      aria-hidden="true"
      data-testid="event-cover-fallback"
    />
    <div class="event-cover__overlay">
      <div class="event-cover__top">
        <slot name="top-start" />
        <slot name="top-end" />
      </div>
      <div class="event-cover__bottom">
        <slot name="bottom" />
      </div>
    </div>
  </div>
</template>

<style scoped>
.event-cover {
  position: relative;
  aspect-ratio: 16 / 9;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--p-surface-200);
}

.event-cover__img {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.event-cover__fallback {
  color: var(--app-text-muted);
  font-size: 2.5rem;
}

.event-cover__overlay {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  padding: 12px;
  pointer-events: none;
}

.event-cover__top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 8px;
  min-width: 0;
}

.event-cover__bottom {
  display: flex;
  min-width: 0;
}
</style>
