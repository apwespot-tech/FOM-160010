<script setup lang="ts">
/** Фото по ссылке из профиля; без фото или если оно не загрузилось — инициалы. */
import { ref, watch } from 'vue'

import { initials } from '@/utils/format'

const props = withDefaults(
  defineProps<{ name: string; photoUrl: string | null; size?: 'normal' | 'large' }>(),
  { size: 'normal' },
)

const failed = ref(false)
watch(
  () => props.photoUrl,
  () => {
    failed.value = false
  },
)
</script>

<template>
  <span class="person-avatar" :class="`person-avatar--${size}`">
    <img
      v-if="photoUrl && !failed"
      :src="photoUrl"
      alt=""
      referrerpolicy="no-referrer"
      data-testid="avatar-photo"
      @error="failed = true"
    />
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
  border-radius: 50%;
  background: var(--p-primary-100);
  color: var(--p-primary-800);
  font-weight: 600;
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

.person-avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
</style>
