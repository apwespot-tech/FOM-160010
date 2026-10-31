<script setup lang="ts">
/**
 * Шапка: логотип и «Мероприятия» ведут на главную; для заполненного профиля —
 * «Создать мероприятие», уведомления и меню профиля. На мобильной ширине — иконки.
 */
import Button from 'primevue/button'
import { RouterLink } from 'vue-router'

import NotificationsButton from '@/components/NotificationsButton.vue'
import ProfileMenu from '@/components/ProfileMenu.vue'
import { useCreateEventDialog } from '@/composables/useCreateEventDialog'
import { useSessionStore } from '@/stores/session'
import { useIsMobile } from '@/utils/breakpoints'

const session = useSessionStore()
const isMobile = useIsMobile()
const { open: openCreate } = useCreateEventDialog()
</script>

<template>
  <header class="app-header">
    <div class="app-header__inner">
      <div class="app-header__left">
        <RouterLink to="/" class="app-header__brand" aria-label="Ищу компанию — главная">
          <i class="pi pi-users app-header__logo" aria-hidden="true" />
          <span class="app-header__brand-text">Ищу компанию</span>
        </RouterLink>
        <nav v-if="session.isProfileCompleted && !isMobile" class="app-header__nav">
          <RouterLink
            to="/"
            class="app-header__link"
            exact-active-class="app-header__link--active"
            data-testid="nav-events"
          >
            Мероприятия
          </RouterLink>
        </nav>
      </div>

      <div v-if="session.isProfileCompleted" class="app-header__actions">
        <Button
          type="button"
          icon="pi pi-plus"
          :label="isMobile ? undefined : 'Создать мероприятие'"
          aria-label="Создать мероприятие"
          :rounded="isMobile"
          data-testid="create-event"
          @click="openCreate"
        />
        <NotificationsButton />
        <ProfileMenu />
      </div>
    </div>
  </header>
</template>

<style scoped>
.app-header {
  position: sticky;
  top: 0;
  z-index: 10;
  background: var(--p-surface-0);
  border-bottom: 1px solid var(--app-border);
}

.app-header__inner {
  height: var(--app-header-height);
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 var(--app-gutter);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.app-header__left {
  display: flex;
  align-items: center;
  gap: 24px;
  min-width: 0;
}

.app-header__brand {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  color: var(--p-primary-700);
  font-weight: 700;
  font-size: 1.125rem;
  text-decoration: none;
  min-height: var(--app-touch-target);
  white-space: nowrap;
}

.app-header__logo {
  color: var(--app-accent);
  font-size: 1.25rem;
}

/* На самых узких экранах остаётся только иконка логотипа */
@media (max-width: 379px) {
  .app-header__brand-text {
    display: none;
  }
}

.app-header__link {
  display: inline-flex;
  align-items: center;
  min-height: var(--app-touch-target);
  color: var(--app-text-muted);
  font-weight: 500;
  text-decoration: none;
  border-bottom: 2px solid transparent;
}

.app-header__link:hover {
  color: var(--p-primary-700);
}

.app-header__link--active {
  color: var(--p-primary-700);
  border-bottom-color: var(--p-primary-700);
}

.app-header__actions {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-shrink: 0;
}

@media (min-width: 640px) {
  .app-header__actions {
    gap: 8px;
  }
}
</style>
