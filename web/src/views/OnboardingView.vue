<script setup lang="ts">
import { useRouter } from 'vue-router'

import ProfileForm from '@/components/ProfileForm.vue'
import { useSessionStore } from '@/stores/session'

const router = useRouter()
const session = useSessionStore()

async function onSaved() {
  await router.replace('/profile')
}
</script>

<template>
  <main class="app-page">
    <section class="app-card">
      <h1 class="app-title">Расскажите о себе</h1>
      <p class="app-subtitle">Имя и дата рождения обязательны, остальное — по желанию</p>
      <ProfileForm v-if="session.profile" :initial="session.profile" @saved="onSaved" />
    </section>
  </main>
</template>
