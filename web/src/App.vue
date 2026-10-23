<script setup lang="ts">
import { onMounted, ref } from 'vue'

type Health = { status: string; database: string }

const health = ref<Health | null>(null)
const error = ref('')

async function check() {
  error.value = ''
  health.value = null
  try {
    const res = await fetch('/health')
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    health.value = await res.json()
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  }
}

onMounted(check)
</script>

<template>
  <main class="page">
    <h1>FOM-160010 · Y.Novikova</h1>
    <p class="lead">Рабочее окружение: Vue 3 + Laravel API + PostgreSQL</p>

    <ul class="checks">
      <li><span class="ok">●</span> Vue — страница открылась</li>
      <li>
        <span :class="health ? 'ok' : error ? 'bad' : 'wait'">●</span>
        Laravel API — {{ health ? health.status : error || 'проверяем…' }}
      </li>
      <li>
        <span :class="health?.database === 'ok' ? 'ok' : error || health ? 'bad' : 'wait'">●</span>
        PostgreSQL — {{ health ? health.database : error ? 'нет ответа API' : 'проверяем…' }}
      </li>
    </ul>

    <button @click="check">Проверить ещё раз</button>
  </main>
</template>

<style>
body {
  margin: 0;
  font-family: system-ui, sans-serif;
  background: #f6f7f9;
  color: #1d2129;
}
.page {
  max-width: 560px;
  margin: 64px auto;
  padding: 0 16px;
}
h1 { margin-bottom: 4px; }
.lead { color: #5b6270; margin-top: 0; }
.checks { list-style: none; padding: 0; line-height: 2; font-size: 18px; }
.checks span { margin-right: 8px; }
.ok { color: #1f9d55; }
.bad { color: #d64545; }
.wait { color: #b0b5bd; }
button {
  padding: 8px 16px;
  border: 1px solid #c9ced6;
  border-radius: 6px;
  background: #fff;
  cursor: pointer;
}
</style>
