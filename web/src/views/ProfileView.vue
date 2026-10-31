<script setup lang="ts">
import { useToast } from 'primevue/usetoast'
import { onMounted } from 'vue'

import ProfileCard from '@/components/ProfileCard.vue'
import { useSessionStore } from '@/stores/session'

const session = useSessionStore()
const toast = useToast()

onMounted(() => {
  // Актуальные данные (возраст, правки администратора); ошибки — оставляем то, что есть
  session.loadProfile().catch(() => undefined)
})

function onSaved(_profile: unknown, changed: boolean) {
  if (changed) toast.add({ severity: 'success', summary: 'Профиль сохранён', life: 3000 })
}
</script>

<template>
  <main class="app-page">
    <section class="app-card app-card--wide">
      <ProfileCard v-if="session.profile" :profile="session.profile" @saved="onSaved" />
    </section>
  </main>
</template>
