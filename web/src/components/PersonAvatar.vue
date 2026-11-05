<script setup lang="ts">
/**
 * Аватар пользователя по avatar_id: загружается с токеном и берётся из кеша.
 * Пока грузится, без аватара или если он не загрузился — инициалы имени.
 */
import { computed } from 'vue'

import type { ImageSize } from '@/api/events'
import { loadUserImageUrl, useImageUrl } from '@/composables/usePhotoUrl'
import { initials } from '@/utils/format'

const props = withDefaults(
  defineProps<{
    name: string | null
    userId: string
    avatarId: string | null
    size?: 'normal' | 'large' | 'xlarge'
    shape?: 'circle' | 'rounded'
  }>(),
  { size: 'normal', shape: 'circle' },
)

// Крупный аватар профиля — исходник, в списках — уменьшенная копия
const imageSize = computed<ImageSize>(() => (props.size === 'xlarge' ? 'full' : 'thumb'))
const { url } = useImageUrl(
  () => {
    const avatar = props.avatarId
    return avatar ? () => loadUserImageUrl(props.userId, avatar, imageSize.value) : null
  },
  () => (props.avatarId ? `avatar:${props.avatarId}:${imageSize.value}` : null),
)
</script>

<template>
  <span class="person-avatar" :class="[`person-avatar--${size}`, `person-avatar--${shape}`]">
    <img v-if="url" :src="url" alt="" draggable="false" data-testid="avatar-photo" />
    <span v-else aria-hidden="true" data-testid="avatar-initials">{{ initials(name) }}</span>
  </span>
</template>

<style scoped>
.person-avatar {
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  background: var(--p-primary-100);
  color: var(--p-primary-800);
  font-weight: 600;
}

.person-avatar--circle {
  border-radius: 50%;
}

.person-avatar--rounded {
  border-radius: 20px;
}

.person-avatar--normal {
  width: 40px;
  height: 40px;
  font-size: 0.875rem;
}

.person-avatar--large {
  width: 52px;
  height: 52px;
  font-size: 1.125rem;
}

.person-avatar--xlarge {
  width: 120px;
  height: 120px;
  font-size: 2.25rem;
}

@media (min-width: 640px) {
  .person-avatar--xlarge {
    width: 144px;
    height: 144px;
  }
}

.person-avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
</style>
