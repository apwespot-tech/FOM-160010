<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'

import { ApiError, api } from '@/api/client'
import type { EventItem } from '@/types'
import { formatDate } from '@/utils/format'

const router = useRouter()

const events = ref<EventItem[]>([])
const loading = ref(true)
const listError = ref('')

const showForm = ref(false)
const title = ref('')
const description = ref('')
const eventDate = ref('')
const formError = ref('')
const creating = ref(false)

const joinCode = ref('')
const joinError = ref('')

async function load() {
  loading.value = true
  listError.value = ''
  try {
    events.value = await api<EventItem[]>('/events')
  } catch (e) {
    listError.value = e instanceof ApiError ? e.message : 'Не удалось загрузить вечера'
  } finally {
    loading.value = false
  }
}

async function createEvent() {
  formError.value = ''
  if (!title.value.trim()) {
    formError.value = 'Введите название'
    return
  }
  if (!eventDate.value) {
    formError.value = 'Выберите дату и время'
    return
  }
  creating.value = true
  try {
    const created = await api<EventItem>('/events', {
      method: 'POST',
      body: {
        title: title.value.trim(),
        description: description.value.trim(),
        event_date: eventDate.value,
      },
    })
    await router.push({ name: 'event', params: { id: created.id } })
  } catch (e) {
    formError.value = e instanceof ApiError ? e.message : 'Не удалось создать вечер'
  } finally {
    creating.value = false
  }
}

function joinByCode() {
  joinError.value = ''
  const code = joinCode.value.trim().split('/').pop() ?? ''
  if (!code) {
    joinError.value = 'Вставьте код или ссылку-приглашение'
    return
  }
  router.push({ name: 'join', params: { code } })
}

onMounted(load)
</script>

<template>
  <section class="top">
    <h1>Мои вечера</h1>
    <button class="btn" @click="showForm = !showForm">
      {{ showForm ? 'Отмена' : 'Создать вечер' }}
    </button>
  </section>

  <form v-if="showForm" class="card form" @submit.prevent="createEvent">
    <label class="field">
      <span class="muted">Название</span>
      <input v-model="title" class="input" type="text" maxlength="200" />
    </label>
    <label class="field">
      <span class="muted">Дата и время</span>
      <input v-model="eventDate" class="input" type="datetime-local" />
    </label>
    <label class="field">
      <span class="muted">Описание</span>
      <textarea v-model="description" class="input" rows="3" maxlength="2000"></textarea>
    </label>
    <p v-if="formError" class="error">{{ formError }}</p>
    <button class="btn" type="submit" :disabled="creating">
      {{ creating ? 'Создаём…' : 'Создать' }}
    </button>
  </form>

  <form class="card join" @submit.prevent="joinByCode">
    <input
      v-model="joinCode"
      class="input"
      type="text"
      placeholder="Код или ссылка-приглашение"
    />
    <button class="btn btn-ghost" type="submit">Присоединиться</button>
  </form>
  <p v-if="joinError" class="error">{{ joinError }}</p>

  <p v-if="loading" class="muted">Загружаем…</p>
  <p v-else-if="listError" class="error">{{ listError }}</p>
  <p v-else-if="events.length === 0" class="muted">
    Вечеров пока нет. Создай первый или присоединись по коду.
  </p>

  <div v-else class="grid">
    <RouterLink
      v-for="event in events"
      :key="event.id"
      :to="{ name: 'event', params: { id: event.id } }"
      class="card event-card"
    >
      <h3>{{ event.title }}</h3>
      <p class="muted">{{ formatDate(event.event_date) }}</p>
      <p class="muted">Участников: {{ event.participants_count }}</p>
    </RouterLink>
  </div>
</template>

<style scoped>
.top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
}

.top h1 {
  margin: 0;
}

.form {
  display: flex;
  flex-direction: column;
  gap: 14px;
  margin-bottom: 16px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.join {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
}

.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 16px;
}

.event-card {
  text-decoration: none;
  color: var(--text);
  transition: border-color 0.2s, box-shadow 0.2s;
}

.event-card:hover {
  border-color: var(--pink);
  box-shadow: var(--glow);
}

.event-card h3 {
  margin-bottom: 8px;
}

.event-card p {
  margin: 0 0 4px;
}
</style>