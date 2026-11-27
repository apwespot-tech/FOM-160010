<script setup lang="ts"></script>

<template>
  <header class="header">
    <div class="container header-inner">
      <span class="logo">
        <span class="logo-bold">КИНО</span><span class="logo-light">ПЯТНИЦА</span>
      </span>
    </div>
  </header>

  <main class="container">
    <section class="card">
      <h1>Выбираем фильм вместе</h1>
      <p class="muted">Создай вечер, позови друзей и проголосуйте за фильм.</p>
      <button class="btn">Создать вечер</button>
    </section>
  </main>
</template>

<style scoped>
.header {
  padding: 20px 0;
}

.logo {
  font-size: 1.6rem;
  letter-spacing: 0.02em;
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
</style>