
<script setup lang="ts">
import { computed, ref } from 'vue'

type Impression = {
  id: number
  title: string
  category: string
  date: string
  image: string
  size: 'large' | 'medium' | 'small'
}

const categories = [
  'Все',
  'Путешествия',
  'Книги',
  'Фильмы',
  'Города',
  'События',
  'Другое',
]

const activeCategory = ref('Все')
const searchQuery = ref('')

const isFormOpen = ref(false)
const selectedImage = ref('')

const newImpression = ref({
  title: '',
  category: 'Путешествия',
  date: new Date().toISOString().slice(0, 10),
  description: '',
})

function handleImageChange(event: Event) {
  const file = (event.target as HTMLInputElement).files?.[0]

  if (file) {
    selectedImage.value = URL.createObjectURL(file)
  }
}

function addImpression() {
  if (!newImpression.value.title.trim()) return

  impressions.value.unshift({
    id: Date.now(),
    title: newImpression.value.title.trim(),
    category: newImpression.value.category,
    date: new Date(newImpression.value.date).toLocaleDateString('ru-RU', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
    }),
    image: selectedImage.value || 'https://images.unsplash.com/photo-1470252649378-9c29740c9fa8?w=900',
    size: 'large',
  })

  newImpression.value = {
    title: '',
    category: 'Путешествия',
    date: new Date().toISOString().slice(0, 10),
    description: '',
  }

  selectedImage.value = ''
  isFormOpen.value = false
  activeCategory.value = 'Все'
}

const impressions = ref<Impression[]>([
  {
    id: 1,
    title: 'Санторини — навсегда в сердце',
    category: 'Путешествия',
    date: '12 июн 2026',
    image: 'https://images.unsplash.com/photo-1533105079780-92b9be482077?w=1000',
    size: 'large',
  },
  {
    id: 2,
    title: '«Нормальные люди»',
    category: 'Книги',
    date: '8 июн 2026',
    image: 'https://images.unsplash.com/photo-1519682337058-a94d519337bc?w=700',
    size: 'small',
  },
  {
    id: 3,
    title: 'Концерт, который запомнится',
    category: 'События',
    date: '3 июн 2026',
    image: 'https://images.unsplash.com/photo-1501386761578-eac5c94b800a?w=900',
    size: 'medium',
  },
  {
    id: 4,
    title: 'Прогулка по городу',
    category: 'Города',
    date: '28 мая 2026',
    image: 'https://images.unsplash.com/photo-1519501025264-65ba15a82390?w=700',
    size: 'small',
  },
  {
    id: 5,
    title: 'Выходные за городом',
    category: 'Путешествия',
    date: '19 мая 2026',
    image: 'https://images.unsplash.com/photo-1470770841072-f978cf4d019e?w=700',
    size: 'small',
  },
])

const filteredImpressions = computed(() => {
  return impressions.value.filter((item) => {
    const matchesCategory =
      activeCategory.value === 'Все' ||
      item.category === activeCategory.value

    const matchesSearch = item.title
      .toLowerCase()
      .includes(searchQuery.value.toLowerCase())

    return matchesCategory && matchesSearch
  })
})
</script>

<template>
  <div class="app">
    <aside class="sidebar">
      <div class="brand">
        <span class="brand-symbol">✳</span>
        <span>Коллекционер<br />впечатлений</span>
      </div>

      <nav class="navigation">
        <a class="nav-item active" href="#">
          <span>⌂</span> Главная
        </a>
        <a class="nav-item" href="#">
          <span>♡</span> Избранное
        </a>
        <a class="nav-item" href="#">
          <span>▥</span> Статистика
        </a>
        <a class="nav-item" href="#">
          <span>⚙</span> Настройки
        </a>
      </nav>

      <div class="sidebar-collection">
        <div class="collection-image"></div>
        <p>Собрано</p>
        <strong>24</strong>
        <span>впечатления</span>
      </div>

      <div class="profile">
        <div class="avatar">D</div>
        <span>Мой профиль</span>
        <span class="profile-arrow">⌄</span>
      </div>
    </aside>

    <main class="main-content">
      <header class="topbar">
        <div class="search">
          <span>⌕</span>
          <input
            v-model="searchQuery"
            placeholder="Поиск по впечатлениям..."
          />
        </div>
        <button class="add-button" @click="isFormOpen = true">
          <span>＋</span> Добавить
        </button>
      </header>

      <section class="intro">
        <div>
          <p class="eyebrow">ТВОЯ КОЛЛЕКЦИЯ МОМЕНТОВ</p>
          <h1>Собирай<br />моменты.</h1>
          <p class="intro-description">
            Путешествия, книги, люди, места —<br />
            всё, что делает жизнь особенной.
          </p>
        </div>
        <div class="intro-decoration">
          <span>Моменты,<br />которые остаются.</span>
        </div>
      </section>

      <section class="stats">
        <div class="stat-card">
          <span class="stat-icon">▱</span>
          <div><strong>24</strong><span>впечатления</span></div>
        </div>
        <div class="stat-card">
          <span class="stat-icon">▧</span>
          <div><strong>6</strong><span>категорий</span></div>
        </div>
        <div class="stat-card">
          <span class="stat-icon">♡</span>
          <div><strong>12</strong><span>избранных</span></div>
        </div>
      </section>

      <section class="collection">
        <div class="collection-heading">
          <div class="category-list">
            <button
              v-for="category in categories"
              :key="category"
              :class="{ selected: activeCategory === category }"
              @click="activeCategory = category"
            >
              {{ category }}
            </button>
          </div>
          <span class="result-count">
            {{ filteredImpressions.length }} записей
          </span>
        </div>

        <div class="impression-grid">
          <article
            v-for="item in filteredImpressions"
            :key="item.id"
            class="impression-card"
            :class="item.size"
            :style="{ backgroundImage: `url(${item.image})` }"
          >
            <span class="card-category">{{ item.category }}</span>
            <div class="card-bottom">
              <span class="card-date">{{ item.date }}</span>
              <h2>{{ item.title }}</h2>
            </div>
            <button class="favorite-button" aria-label="В избранное">♡</button>
          </article>

          <div v-if="filteredImpressions.length === 0" class="empty-state">
            <span>⌕</span>
            <h2>Ничего не нашлось</h2>
            <p>Попробуй изменить запрос или выбрать другую категорию.</p>
          </div>
        </div>
      </section>

      <footer class="footer">
        <span>КОЛЛЕКЦИОНЕР ВПЕЧАТЛЕНИЙ</span>
        <span>Твоя история — в твоих моментах.</span>
      </footer>

<!-- Форма добавления впечатления -->
<div v-if="isFormOpen" class="modal-overlay" @click.self="isFormOpen = false">
  <form class="impression-form" @submit.prevent="addImpression">
    <div class="form-header">
      <div>
        <p class="eyebrow">ТВОЯ КОЛЛЕКЦИЯ</p>
        <h2>Новое впечатление</h2>
      </div>
      <button type="button" class="close-button" @click="isFormOpen = false">
        ×
      </button>
    </div>

    <label class="upload-area">
      <img v-if="selectedImage" :src="selectedImage" alt="Предпросмотр фотографии" />
      <template v-else>
        <span class="upload-icon">＋</span>
        <strong>Добавь фотографию</strong>
        <span>Нажми, чтобы выбрать изображение</span>
      </template>
      <input type="file" accept="image/*" @change="handleImageChange" hidden />
    </label>

    <label class="form-label">
      Название впечатления *
      <input
        v-model="newImpression.title"
        type="text"
        placeholder="Например, поездка в горы"
        required
        maxlength="100"
      />
    </label>

    <div class="form-row">
      <label class="form-label">
        Категория
        <select v-model="newImpression.category">
          <option v-for="category in categories.slice(1)" :key="category">
            {{ category }}
          </option>
        </select>
      </label>

      <label class="form-label">
        Дата
        <input v-model="newImpression.date" type="date" required />
      </label>
    </div>

    <label class="form-label">
      Описание
      <textarea
        v-model="newImpression.description"
        placeholder="Расскажи, что особенно запомнилось..."
        rows="3"
      ></textarea>
    </label>

    <div class="form-actions">
      <button type="button" class="cancel-button" @click="isFormOpen = false">
        Отмена
      </button>
      <button type="submit" class="add-button">
        Сохранить впечатление
      </button>
    </div>
  </form>
</div>

    </main>
  </div>
</template>

