<script setup lang="ts">
/** Кнопка с инициалами и выпадающее меню: имя и телефон, «Профиль», «Выйти». */
import Button from 'primevue/button'
import Menu from 'primevue/menu'
import type { MenuItem } from 'primevue/menuitem'
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'

import { useSessionStore } from '@/stores/session'
import { formatPhone, initials } from '@/utils/format'

const session = useSessionStore()
const router = useRouter()
const menu = ref<InstanceType<typeof Menu> | null>(null)

const name = computed(() => session.profile?.name ?? '')

const items = computed<MenuItem[]>(() => [
  {
    label: 'Профиль',
    icon: 'pi pi-user',
    command: () => void router.push('/profile'),
  },
  { separator: true },
  {
    label: 'Выйти',
    icon: 'pi pi-sign-out',
    command: () => void logout(),
  },
])

async function logout() {
  await session.logout()
  await router.replace('/login')
}

function toggle(event: Event) {
  menu.value?.toggle(event)
}
</script>

<template>
  <Button
    type="button"
    :label="initials(name)"
    rounded
    severity="secondary"
    aria-label="Меню профиля"
    aria-haspopup="true"
    aria-controls="profile-menu"
    class="profile-menu__button"
    data-testid="profile-menu-button"
    @click="toggle"
  />
  <Menu id="profile-menu" ref="menu" :model="items" popup data-testid="profile-menu">
    <template #start>
      <div class="profile-menu__header" data-testid="profile-menu-header">
        <div class="profile-menu__name app-break">{{ name }}</div>
        <div class="profile-menu__phone">{{ formatPhone(session.profile?.phone ?? '') }}</div>
      </div>
    </template>
    <template #item="{ item, props }">
      <a
        v-bind="props.action"
        class="profile-menu__item"
        :data-testid="item.label === 'Выйти' ? 'logout' : 'menu-profile'"
      >
        <span :class="item.icon" aria-hidden="true" />
        <span>{{ item.label }}</span>
      </a>
    </template>
  </Menu>
</template>

<style scoped>
.profile-menu__button {
  width: var(--app-touch-target);
  height: var(--app-touch-target);
  padding: 0;
  background: var(--p-primary-100);
  border-color: var(--p-primary-100);
  color: var(--p-primary-800);
  font-weight: 600;
}

.profile-menu__header {
  padding: 12px 16px 8px;
  max-width: 260px;
}

.profile-menu__name {
  font-weight: 600;
}

.profile-menu__phone {
  color: var(--app-text-muted);
  font-size: 0.875rem;
}

.profile-menu__item {
  display: flex;
  align-items: center;
  gap: 10px;
  min-height: var(--app-touch-target);
  padding: 0 16px;
}
</style>
