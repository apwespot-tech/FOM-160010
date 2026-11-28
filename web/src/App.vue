<script setup lang="ts">
import { RouterLink, RouterView, useRouter } from 'vue-router'

import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const router = useRouter()

function logout() {
  auth.logout()
  router.push({ name: 'login' })
}
</script>

<template>
  <header class="header">
    <div class="container header-inner">
      <RouterLink to="/" class="logo">
        <span class="logo-bold">КИНО</span><span class="logo-light">ПЯТНИЦА</span>
      </RouterLink>

      <div v-if="auth.isAuthenticated" class="user">
        <span class="muted">{{ auth.user?.name }}</span>
        <button class="btn btn-ghost" @click="logout">Выйти</button>
      </div>
    </div>
  </header>

  <main class="container">
    <RouterView />
  </main>
</template>

<style scoped>
.header {
  padding: 20px 0;
}

.header-inner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.logo {
  font-size: 1.6rem;
  letter-spacing: 0.02em;
  text-decoration: none;
  color: var(--text);
}

.logo-bold {
  font-weight: 900;
  background: var(--gradient);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}

.logo-light {
  font-weight: 300;
  margin-left: 6px;
}

.user {
  display: flex;
  align-items: center;
  gap: 12px;
}
</style>