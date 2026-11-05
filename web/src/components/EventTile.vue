<script setup lang="ts">
/** Плитка данных мероприятия в режиме просмотра: иконка, подпись, значение и подстрочник. */
defineProps<{ icon: string; label: string }>()
</script>

<template>
  <div class="event-tile">
    <span class="event-tile__icon" aria-hidden="true"><i :class="['pi', icon]" /></span>
    <div class="event-tile__body">
      <span class="event-tile__label">{{ label }}</span>
      <div class="event-tile__value"><slot /></div>
      <div v-if="$slots.hint" class="event-tile__hint"><slot name="hint" /></div>
    </div>
  </div>
</template>

<style scoped>
.event-tile {
  display: flex;
  gap: 12px;
  padding: 14px;
  min-width: 0;
  background: var(--p-surface-50);
  border: 1px solid var(--app-border);
  border-radius: 12px;
}

.event-tile__icon {
  flex-shrink: 0;
  width: 40px;
  height: 40px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 10px;
  background: var(--p-primary-100);
  color: var(--p-primary-700);
  font-size: 1.125rem;
}

.event-tile__body {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.event-tile__label {
  color: var(--app-text-muted);
  font-size: 0.75rem;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.event-tile__value {
  font-weight: 600;
  overflow-wrap: anywhere;
}

.event-tile__hint {
  color: var(--app-text-muted);
  font-size: 0.875rem;
}
</style>
