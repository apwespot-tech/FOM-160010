<script setup lang="ts">
/**
 * Кнопка уведомлений: точка при непрочитанных, панель с последними уведомлениями.
 * Открытие панели загружает список и отмечает показанное прочитанным; выделение
 * непрочитанных сохраняется, пока панель открыта.
 */
import Button from 'primevue/button'
import Popover from 'primevue/popover'
import { computed, ref } from 'vue'
import { RouterLink } from 'vue-router'

import { type AppNotification, listNotifications, markNotificationsRead } from '@/api/notifications'
import { useUnreadNotifications } from '@/composables/useUnreadNotifications'
import { useSessionStore } from '@/stores/session'
import { formatCreatedAt } from '@/utils/dates'
import { notificationText } from '@/utils/notifications'

type PanelState = 'loading' | 'error' | 'ready'

const session = useSessionStore()
const { unreadCount, clear } = useUnreadNotifications()
const panel = ref<InstanceType<typeof Popover> | null>(null)
const state = ref<PanelState>('loading')
const items = ref<AppNotification[]>([])

const hasUnread = computed(() => unreadCount.value > 0)
const label = computed(() => (hasUnread.value ? 'Уведомления, есть непрочитанные' : 'Уведомления'))

function toggle(event: Event): void {
  // Popover сообщает об открытии только после анимации: решаем по состоянию до переключения
  const wasOpen = (panel.value as { visible?: boolean } | null)?.visible ?? false
  panel.value?.toggle(event)
  if (!wasOpen) void load()
}

function hide(): void {
  panel.value?.hide()
}

async function load(): Promise<void> {
  state.value = 'loading'
  try {
    const list = await listNotifications()
    items.value = list.items
    state.value = 'ready'
  } catch {
    state.value = 'error'
    return
  }
  const newest = items.value[0]
  if (!newest) return
  try {
    await markNotificationsRead(newest.created_at)
    clear()
  } catch {
    // Не отметилось — точка останется до следующего открытия
  }
}

function text(item: AppNotification): string {
  return notificationText(item, session.profile?.id ?? null)
}
</script>

<template>
  <span class="notifications-button">
    <Button
      type="button"
      icon="pi pi-bell"
      text
      rounded
      severity="secondary"
      :aria-label="label"
      aria-haspopup="true"
      data-testid="notifications-button"
      @click="toggle"
    />
    <span v-if="hasUnread" class="notifications-button__dot" data-testid="notifications-dot" />
  </span>
  <Popover ref="panel" data-testid="notifications-panel">
    <div class="notifications">
      <div class="notifications__title">Уведомления</div>
      <p v-if="state === 'loading'" class="notifications__note">Загрузка…</p>
      <p v-else-if="state === 'error'" class="notifications__note">
        Не удалось загрузить уведомления
      </p>
      <p v-else-if="items.length === 0" class="notifications__note">Уведомлений пока нет</p>
      <ul v-else class="notifications__list">
        <li v-for="item in items" :key="item.id">
          <RouterLink
            v-if="item.event.id"
            :to="`/events/${item.event.id}`"
            class="notifications__item notifications__item--link"
            :class="{ 'notifications__item--unread': !item.read }"
            data-testid="notification-item"
            @click="hide"
          >
            <span class="notifications__text">{{ text(item) }}</span>
            <span class="notifications__time">{{ formatCreatedAt(item.created_at) }}</span>
          </RouterLink>
          <div
            v-else
            class="notifications__item"
            :class="{ 'notifications__item--unread': !item.read }"
            data-testid="notification-item"
          >
            <span class="notifications__text">{{ text(item) }}</span>
            <span class="notifications__time">{{ formatCreatedAt(item.created_at) }}</span>
          </div>
        </li>
      </ul>
    </div>
  </Popover>
</template>

<style scoped>
.notifications-button {
  position: relative;
  display: inline-flex;
}

.notifications-button__dot {
  position: absolute;
  top: 8px;
  right: 8px;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--app-accent);
  box-shadow: 0 0 0 2px var(--p-surface-0);
  pointer-events: none;
}

.notifications {
  width: min(320px, calc(100vw - 48px));
}

.notifications__title {
  font-weight: 600;
  margin-bottom: 8px;
}

.notifications__note {
  margin: 0;
  color: var(--app-text-muted);
}

.notifications__list {
  list-style: none;
  margin: 0 -8px;
  padding: 0;
  max-height: min(420px, 60vh);
  overflow-y: auto;
}

.notifications__item {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 8px;
  border-radius: 6px;
  color: var(--app-text);
  text-decoration: none;
  overflow-wrap: anywhere;
}

.notifications__item--link:hover,
.notifications__item--link:focus-visible {
  background: var(--p-surface-100);
}

.notifications__item--unread {
  background: var(--app-accent-soft);
}

.notifications__item--unread .notifications__text {
  font-weight: 600;
}

.notifications__time {
  font-size: 0.8125rem;
  color: var(--app-text-muted);
}
</style>
