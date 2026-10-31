<script setup lang="ts">
import Button from 'primevue/button'
import Toast from 'primevue/toast'
import { watch } from 'vue'
import { RouterView, useRoute, useRouter } from 'vue-router'

import { useSessionStore } from '@/stores/session'
import { useIsMobile } from '@/utils/breakpoints'

const session = useSessionStore()
const route = useRoute()
const router = useRouter()
const isMobile = useIsMobile()

// Сессия завершилась (выход, не удалось обновить токены) — уводим со страниц для авторизованных
watch(
  () => session.isAuthenticated,
  (authenticated) => {
    if (!authenticated && !route.meta.guest) router.replace('/login')
  },
)

async function logout() {
  await session.logout()
  await router.replace('/login')
}
</script>

<template>
  <header class="app-header">
    <div class="app-header__inner">
      <RouterLink to="/" class="app-header__brand">
        <i class="pi pi-users app-header__logo" aria-hidden="true" />
        <span>Ищу компанию</span>
      </RouterLink>
      <Button
        v-if="session.isAuthenticated"
        icon="pi pi-sign-out"
        :label="isMobile ? undefined : 'Выйти'"
        aria-label="Выйти"
        severity="secondary"
        text
        data-testid="logout"
        @click="logout"
      />
    </div>
  </header>

  <RouterView />

  <Toast :position="isMobile ? 'top-center' : 'top-right'" />
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

.app-header__brand {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  color: var(--p-primary-700);
  font-weight: 700;
  font-size: 1.125rem;
  text-decoration: none;
  min-height: var(--app-touch-target);
}

.app-header__logo {
  color: var(--app-accent);
  font-size: 1.25rem;
}
</style>
