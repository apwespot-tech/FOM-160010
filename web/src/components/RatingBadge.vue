<script setup lang="ts">
/** Рейтинг: звезда и число с одним знаком («4,8»); при null ничего не показывается. */
import { formatRating } from '@/utils/format'

defineProps<{ value: number | null; label?: string }>()
</script>

<template>
  <span
    v-if="value !== null"
    class="rating-badge"
    :aria-label="`${label ?? 'Рейтинг'} ${formatRating(value)}`"
    data-testid="rating-badge"
  >
    <i class="pi pi-star-fill rating-badge__icon" aria-hidden="true" />
    {{ formatRating(value) }}
  </span>
</template>

<style scoped>
.rating-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-weight: 600;
  font-size: 0.875rem;
  color: var(--app-text);
  white-space: nowrap;
}

.rating-badge__icon {
  color: var(--app-accent);
  font-size: 0.875rem;
}
</style>
