<script setup lang="ts">
/**
 * Кнопка уведомлений. Пока уведомлений на сервере нет — панель-заглушка
 * без запросов и без счётчика.
 */
import Button from 'primevue/button'
import Popover from 'primevue/popover'
import { ref } from 'vue'

const panel = ref<InstanceType<typeof Popover> | null>(null)

function toggle(event: Event) {
  panel.value?.toggle(event)
}
</script>

<template>
  <Button
    type="button"
    icon="pi pi-bell"
    text
    rounded
    severity="secondary"
    aria-label="Уведомления"
    aria-haspopup="true"
    data-testid="notifications-button"
    @click="toggle"
  />
  <Popover ref="panel" data-testid="notifications-panel">
    <div class="notifications">
      <div class="notifications__title">Уведомления</div>
      <p class="notifications__empty">Уведомлений пока нет</p>
    </div>
  </Popover>
</template>

<style scoped>
.notifications {
  width: min(280px, calc(100vw - 48px));
}

.notifications__title {
  font-weight: 600;
  margin-bottom: 8px;
}

.notifications__empty {
  margin: 0;
  color: var(--app-text-muted);
}
</style>
