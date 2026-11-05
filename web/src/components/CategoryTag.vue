<script setup lang="ts">
/** Тег категории с её иконкой: на обложке — светлая сплошная плашка, в профиле — мягкий тег. */
import { computed } from 'vue'

import type { Category } from '@/api/events'
import { categoryIcon } from '@/utils/categories'

const props = withDefaults(
  defineProps<{ category: Pick<Category, 'name' | 'icon'>; variant?: 'overlay' | 'soft' }>(),
  { variant: 'overlay' },
)

const icon = computed(() => categoryIcon(props.category.icon))
</script>

<template>
  <span class="category-tag" :class="`category-tag--${variant}`" data-testid="category-tag">
    <i :class="['pi', icon]" aria-hidden="true" data-testid="category-tag-icon" />
    {{ category.name }}
  </span>
</template>

<style scoped>
.category-tag {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  max-width: 100%;
  padding: 4px 10px;
  border-radius: 8px;
  background: rgb(255 255 255 / 0.94);
  color: var(--p-primary-700);
  font-size: 0.8125rem;
  font-weight: 600;
  line-height: 1.3;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.category-tag--soft {
  padding: 6px 12px;
  background: var(--p-primary-50);
  border: 1px solid var(--p-primary-100);
  font-size: 0.875rem;
}

.category-tag .pi {
  font-size: 0.8125rem;
}
</style>
