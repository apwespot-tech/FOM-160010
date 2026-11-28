<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { ApiError } from '@/api/client'
import { useAuthStore } from '@/stores/auth'

type Mode = 'login' | 'register'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()

const mode = ref<Mode>('login')
const name = ref('')
const email = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)

const isRegister = computed(() => mode.value === 'register')

function switchMode(next: Mode) {
  mode.value = next
  error.value = ''
}

async function submit() {
  error.value = ''
  if (isRegister.value) {
    if (!name.value.trim()) {
      error.value = 'Введите имя'
      return
    }
    if (password.value.length < 8) {
      error.value = 'Пароль должен быть не короче 8 символов'
      return
    }
  }

  loading.value = true
  try {
    if (isRegister.value) {
      await auth.register(name.value.trim(), email.value.trim(), password.value)
    } else {
      await auth.login(email.value.trim(), password.value)
    }
    const target = route.query.redirect
    const redirect =
      typeof target === 'string' && target.startsWith('/') && !target.startsWith('//')
        ? target
        : '/'
    await router.push(redirect)
  } catch (e) {
    error.value = e instanceof ApiError ? e.message : 'Что-то пошло не так'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <section class="card auth-card">
    <div class="tabs">
      <button
        type="button"
        class="tab"
        :class="{ active: mode === 'login' }"
        @click="switchMode('login')"
      >
        Вход
      </button>
      <button
        type="button"
        class="tab"
        :class="{ active: mode === 'register' }"
        @click="switchMode('register')"
      >
        Регистрация
      </button>
    </div>

    <form class="form" @submit.prevent="submit">
      <label v-if="isRegister" class="field">
        <span class="muted">Имя</span>
        <input v-model="name" class="input" type="text" autocomplete="name" />
      </label>

      <label class="field">
        <span class="muted">Email</span>
        <input v-model="email" class="input" type="email" required autocomplete="email" />
      </label>

      <label class="field">
        <span class="muted">Пароль</span>
        <input
          v-model="password"
          class="input"
          type="password"
          required
          :autocomplete="isRegister ? 'new-password' : 'current-password'"
        />
      </label>

      <p v-if="error" class="error">{{ error }}</p>

      <button class="btn" type="submit" :disabled="loading">
        {{ loading ? 'Подождите…' : isRegister ? 'Зарегистрироваться' : 'Войти' }}
      </button>
    </form>
  </section>
</template>

<style scoped>
.auth-card {
  max-width: 420px;
  margin: 32px auto;
}

.tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 20px;
}

.tab {
  flex: 1;
  padding: 10px;
  border: 1px solid var(--border);
  border-radius: 12px;
  background: transparent;
  color: var(--text-muted);
  font: inherit;
  font-weight: 700;
  cursor: pointer;
}

.tab.active {
  color: #fff;
  background: var(--surface-2);
  border-color: var(--pink);
}

.form {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
</style>