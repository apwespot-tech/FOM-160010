<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'

import { ApiError, api } from '@/api/client'
import type { EventItem } from '@/types'

const route = useRoute()
const router = useRouter()
const error = ref('')

onMounted(async () => {
  try {
    const code = encodeURIComponent(String(route.params.code))
    const event = await api<EventItem>(`/events/join/${code}`, { method: 'POST' })
    await router.replace({ name: 'event', params: { id: event.id } })
  } catch (e) {
    error.value = e instanceof ApiError ? e.message : 'Не удалось присоединиться'
  }
})
</script>

<template>
  <section class="card">
    <template v-if="error">
      <h1>Не получилось присоединиться</h1>
      <p class="error">{{ error }}</p>
      <RouterLink to="/" class="btn btn-ghost">К моим вечерам</RouterLink>
    </template>
    <p v-else class="muted">Присоединяемся к вечеру…</p>
  </section>
</template>