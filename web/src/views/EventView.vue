<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { RouterLink, useRoute } from 'vue-router'

import { ApiError, api } from '@/api/client'
import { useAuthStore } from '@/stores/auth'
import type { EventDetail, MovieResult, Results } from '@/types'
import { formatDate, plural } from '@/utils/format'

const route = useRoute()
const auth = useAuthStore()
const eventId = String(route.params.id)

const event = ref<EventDetail | null>(null)
const results = ref<Results | null>(null)
const error = ref('')
const actionError = ref('')
const copied = ref(false)

const genreFilter = ref('')
const brokenPosters = ref<number[]>([])
const voting = ref<number | null>(null)

const showForm = ref(false)
const newTitle = ref('')
const newGenre = ref('')
const newPoster = ref('')
const formError = ref('')
const adding = ref(false)

let timer: number | undefined

const inviteLink = computed(() =>
  event.value ? `${window.location.origin}/join/${event.value.invite_code}` : '',
)

const movies = computed(() => results.value?.movies ?? [])

const genres = computed(() => [...new Set(movies.value.map((m) => m.genre))].sort())

const activeGenre = computed(() => (genres.value.includes(genreFilter.value) ? genreFilter.value : ''))

const visibleMovies = computed(() =>
  activeGenre.value ? movies.value.filter((m) => m.genre === activeGenre.value) : movies.value,
)

const everyoneVoted = computed(
  () => !!event.value && !!results.value && results.value.total_votes >= event.value.participants_count,
)

function canDelete(movie: MovieResult): boolean {
  return movie.added_by === auth.user?.id || event.value?.owner_id === auth.user?.id
}

async function refresh(silent = false) {
  try {
    const [eventData, resultsData] = await Promise.all([
      api<EventDetail>(`/events/${eventId}`),
      api<Results>(`/events/${eventId}/results`),
    ])
    event.value = eventData
    results.value = resultsData
  } catch (e) {
    if (!silent) error.value = e instanceof ApiError ? e.message : 'Не удалось загрузить вечер'
  }
}

async function copyLink() {
  try {
    await navigator.clipboard.writeText(inviteLink.value)
    copied.value = true
    setTimeout(() => (copied.value = false), 2000)
  } catch {
    actionError.value = 'Не удалось скопировать, выдели ссылку и скопируй вручную'
  }
}

async function vote(movie: MovieResult) {
  actionError.value = ''
  voting.value = movie.id
  try {
    await api(`/events/${eventId}/votes`, { method: 'POST', body: { movie_id: movie.id } })
  } catch (e) {
    actionError.value = e instanceof ApiError ? e.message : 'Не удалось проголосовать'
  } finally {
    voting.value = null
    await refresh(true)
  }
}

async function addMovie() {
  formError.value = ''
  if (!newTitle.value.trim() || !newGenre.value.trim()) {
    formError.value = 'Укажите название и жанр'
    return
  }
  adding.value = true
  try {
    await api(`/events/${eventId}/movies`, {
      method: 'POST',
      body: {
        title: newTitle.value.trim(),
        genre: newGenre.value.trim(),
        poster_url: newPoster.value.trim() || null,
      },
    })
    newTitle.value = ''
    newGenre.value = ''
    newPoster.value = ''
    showForm.value = false
    await refresh(true)
  } catch (e) {
    formError.value = e instanceof ApiError ? e.message : 'Не удалось добавить фильм'
  } finally {
    adding.value = false
  }
}

async function removeMovie(movie: MovieResult) {
  if (!confirm(`Удалить «${movie.title}»?`)) return
  actionError.value = ''
  try {
    await api(`/events/${eventId}/movies/${movie.id}`, { method: 'DELETE' })
  } catch (e) {
    actionError.value = e instanceof ApiError ? e.message : 'Не удалось удалить фильм'
  }
  await refresh(true)
}

onMounted(async () => {
  await refresh()
  if (event.value) {
    timer = window.setInterval(() => refresh(true), 5000)
  }
})

onUnmounted(() => window.clearInterval(timer))
</script>

<template>
  <RouterLink to="/" class="back">← Мои вечера</RouterLink>

  <p v-if="error && (!event || !results)" class="error">{{ error }}</p>
  <p v-else-if="!event || !results" class="muted">Загружаем…</p>

  <template v-else>
    <section class="card block">
      <h1>{{ event.title }}</h1>
      <p class="muted">{{ formatDate(event.event_date) }}</p>
      <p v-if="event.description">{{ event.description }}</p>
    </section>

    <section class="card block">
      <h3>Пригласи друзей</h3>
      <div class="invite">
        <input class="input" type="text" readonly :value="inviteLink" />
        <button class="btn" @click="copyLink">
          {{ copied ? 'Скопировано' : 'Скопировать' }}
        </button>
      </div>
    </section>

    <section class="card block winner">
      <p v-if="results.total_votes === 0" class="muted">Пока никто не проголосовал</p>
      <template v-else-if="results.winner">
        <p class="muted">{{ everyoneVoted ? 'Победитель' : 'Сейчас лидирует' }}</p>
        <h2 class="gradient-text">{{ results.winner.title }}</h2>
        <p class="muted">
          {{ results.winner.votes }} {{ plural(results.winner.votes, ['голос', 'голоса', 'голосов']) }}
          из {{ results.total_votes }}
        </p>
      </template>
      <template v-else>
        <h2>Ничья</h2>
        <p class="muted">Нужно ещё голосов, чтобы выбрать фильм</p>
      </template>
    </section>

    <section class="block">
      <div class="movies-top">
        <h2>Фильмы</h2>
        <button class="btn" @click="showForm = !showForm">
          {{ showForm ? 'Отмена' : 'Добавить фильм' }}
        </button>
      </div>

      <form v-if="showForm" class="card form" @submit.prevent="addMovie">
        <label class="field">
          <span class="muted">Название</span>
          <input v-model="newTitle" class="input" type="text" maxlength="200" />
        </label>
        <label class="field">
          <span class="muted">Жанр</span>
          <input v-model="newGenre" class="input" type="text" maxlength="50" />
        </label>
        <label class="field">
          <span class="muted">Ссылка на постер (необязательно)</span>
          <input
            v-model="newPoster"
            class="input"
            type="text"
            placeholder="https://..."
          />
        </label>
        <p v-if="formError" class="error">{{ formError }}</p>
        <button class="btn" type="submit" :disabled="adding">
          {{ adding ? 'Добавляем…' : 'Добавить' }}
        </button>
      </form>

      <p v-if="actionError" class="error">{{ actionError }}</p>

      <div v-if="genres.length > 1" class="chips">
        <button class="chip" :class="{ active: activeGenre === '' }" @click="genreFilter = ''">
          Все
        </button>
        <button
          v-for="genre in genres"
          :key="genre"
          class="chip"
          :class="{ active: activeGenre === genre }"
          @click="genreFilter = genre"
        >
          {{ genre }}
        </button>
      </div>

      <p v-if="movies.length === 0" class="muted">
        Фильмов пока нет. Добавь первого кандидата.
      </p>

      <div v-else class="grid">
        <article
          v-for="movie in visibleMovies"
          :key="movie.id"
          class="card movie"
          :class="{ mine: results.my_vote_movie_id === movie.id }"
        >
          <div class="poster">
            <img
              v-if="movie.poster_url && !brokenPosters.includes(movie.id)"
              :src="movie.poster_url"
              :alt="movie.title"
              loading="lazy"
              @error="brokenPosters.push(movie.id)"
            />
            <div v-else class="poster-empty">{{ movie.title.slice(0, 1).toUpperCase() }}</div>
          </div>

          <h3>{{ movie.title }}</h3>
          <p class="muted">{{ movie.genre }}</p>
          <p class="votes">
            {{ movie.votes }} {{ plural(movie.votes, ['голос', 'голоса', 'голосов']) }}
          </p>

          <div class="actions">
            <button v-if="results.my_vote_movie_id === movie.id" class="btn" disabled>
              Ваш голос
            </button>
            <button
              v-else
              class="btn"
              :disabled="results.my_vote_movie_id !== null || voting !== null"
              @click="vote(movie)"
            >
              Проголосовать
            </button>
            <button v-if="canDelete(movie)" class="btn btn-ghost" @click="removeMovie(movie)">
              Удалить
            </button>
          </div>
        </article>
      </div>
    </section>

    <section class="card block">
      <h3>Участники ({{ event.participants_count }})</h3>
      <ul class="people">
        <li v-for="person in event.participants" :key="person.id">{{ person.name }}</li>
      </ul>
    </section>
  </template>
</template>

<style scoped>
.back {
  display: inline-block;
  margin-bottom: 16px;
  text-decoration: none;
}

.block {
  margin-bottom: 16px;
}

.invite {
  display: flex;
  gap: 12px;
}

.winner h2 {
  margin: 0 0 6px;
}

.gradient-text {
  background: var(--gradient);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}

.movies-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
}

.movies-top h2 {
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

.chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 16px;
}

.chip {
  padding: 8px 16px;
  border: 1px solid var(--border);
  border-radius: 999px;
  background: transparent;
  color: var(--text-muted);
  font: inherit;
  font-weight: 600;
  cursor: pointer;
}

.chip.active {
  color: #fff;
  background: var(--surface-2);
  border-color: var(--pink);
}

.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 16px;
}

.movie {
  display: flex;
  flex-direction: column;
  padding: 16px;
}

.movie.mine {
  border-color: var(--orange);
}

.poster {
  aspect-ratio: 2 / 3;
  margin-bottom: 12px;
  border-radius: 12px;
  overflow: hidden;
  background: var(--surface-2);
}

.poster img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.poster-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 100%;
  font-size: 3rem;
  font-weight: 900;
  background: var(--gradient);
}

.movie h3 {
  margin-bottom: 4px;
}

.movie p {
  margin: 0 0 4px;
}

.votes {
  font-weight: 700;
}

.actions {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: auto;
  padding-top: 12px;
}

.people {
  margin: 0;
  padding-left: 20px;
}
</style>