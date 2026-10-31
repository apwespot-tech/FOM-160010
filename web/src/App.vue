<script setup lang="ts">
import ConfirmDialog from 'primevue/confirmdialog'
import Toast from 'primevue/toast'
import { watch } from 'vue'
import { RouterView, useRoute, useRouter } from 'vue-router'

import AppHeader from '@/components/AppHeader.vue'
import CreateEventDialog from '@/components/CreateEventDialog.vue'
import { useCreateEventDialog } from '@/composables/useCreateEventDialog'
import { useSessionStore } from '@/stores/session'
import { useIsMobile } from '@/utils/breakpoints'

const session = useSessionStore()
const route = useRoute()
const router = useRouter()
const isMobile = useIsMobile()
const { close: closeCreate } = useCreateEventDialog()

// Сессия завершилась (выход, не удалось обновить токены) — уводим со страниц для авторизованных
watch(
  () => session.isAuthenticated,
  (authenticated) => {
    if (authenticated) return
    closeCreate()
    if (!route.meta.guest) void router.replace('/login')
  },
)
</script>

<template>
  <AppHeader />

  <RouterView />

  <CreateEventDialog v-if="session.isProfileCompleted" />
  <ConfirmDialog :class="{ 'app-confirm--mobile': isMobile }" />
  <Toast :position="isMobile ? 'top-center' : 'top-right'" />
</template>

<style>
.p-confirmdialog.app-confirm--mobile {
  width: calc(100vw - 32px);
}

.p-confirmdialog {
  max-width: 480px;
}
</style>
