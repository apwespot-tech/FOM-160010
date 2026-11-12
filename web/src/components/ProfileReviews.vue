<script setup lang="ts">
/**
 * Отзывы о пользователе: вкладки «Как организатор» и «Как участник», новые первыми,
 * подгрузка по 20. Автор анонимного отзыва скрыт сервером; администратор видит его
 * с отметкой «анонимно» и может удалить любой отзыв.
 */
import Button from 'primevue/button'
import Tab from 'primevue/tab'
import TabList from 'primevue/tablist'
import Tabs from 'primevue/tabs'
import Tag from 'primevue/tag'
import { useConfirm } from 'primevue/useconfirm'
import { useToast } from 'primevue/usetoast'
import { ref, watch } from 'vue'
import { RouterLink } from 'vue-router'

import {
  deleteReview,
  listUserReviews,
  type ProfileRatings,
  type Review,
  type ReviewKind,
} from '@/api/reviews'
import PersonAvatar from '@/components/PersonAvatar.vue'
import { formatLongDate } from '@/utils/dates'

const props = defineProps<{
  userId: string
  ratings: ProfileRatings
  isAdmin: boolean
}>()
const emit = defineEmits<{ changed: [] }>()

const toast = useToast()
const confirm = useConfirm()

const STARS = [1, 2, 3, 4, 5]

const kind = ref<ReviewKind>('organizer')
const items = ref<Review[]>([])
const total = ref(0)
const loading = ref(false)
const loadError = ref(false)
// Ответ на устаревший запрос (сменили вкладку или профиль) не должен затирать новый
let request = 0

async function load(append = false): Promise<void> {
  const current = ++request
  loading.value = true
  loadError.value = false
  try {
    const page = await listUserReviews(props.userId, kind.value, append ? items.value.length : 0)
    if (current !== request) return
    items.value = append ? [...items.value, ...page.items] : page.items
    total.value = page.total
  } catch {
    if (current === request) loadError.value = true
  } finally {
    if (current === request) loading.value = false
  }
}

watch(
  () => props.userId,
  () => {
    kind.value = 'organizer'
    void load()
  },
  { immediate: true },
)

function onTab(value: string | number): void {
  kind.value = value as ReviewKind
  items.value = []
  total.value = 0
  void load()
}

function confirmDelete(review: Review): void {
  confirm.require({
    header: 'Удалить отзыв?',
    message: 'Отзыв будет удалён и перестанет учитываться в рейтинге.',
    icon: 'pi pi-exclamation-triangle',
    rejectProps: {
      label: 'Отмена',
      severity: 'secondary',
      outlined: true,
      'data-testid': 'confirm-reject',
    },
    acceptProps: { label: 'Удалить', severity: 'danger', 'data-testid': 'confirm-accept' },
    accept: () => void remove(review),
  })
}

async function remove(review: Review): Promise<void> {
  try {
    await deleteReview(review.id)
    toast.add({ severity: 'success', summary: 'Отзыв удалён', life: 3000 })
  } catch {
    toast.add({ severity: 'error', summary: 'Не удалось удалить отзыв', life: 4000 })
  }
  await load()
  emit('changed')
}
</script>

<template>
  <section class="profile-reviews app-card" aria-labelledby="profile-reviews-title">
    <h2 id="profile-reviews-title" class="profile-reviews__title">Отзывы</h2>

    <Tabs :value="kind" @update:value="onTab">
      <TabList>
        <Tab value="organizer" data-testid="reviews-tab-organizer">
          Как организатор ({{ ratings.as_organizer.count }})
        </Tab>
        <Tab value="participant" data-testid="reviews-tab-participant">
          Как участник ({{ ratings.as_participant.count }})
        </Tab>
      </TabList>
    </Tabs>

    <p v-if="loadError" class="profile-reviews__empty">
      Не удалось загрузить отзывы
      <Button type="button" label="Повторить" text @click="load()" />
    </p>
    <p
      v-else-if="!loading && items.length === 0"
      class="profile-reviews__empty"
      data-testid="reviews-empty"
    >
      Отзывов пока нет
    </p>

    <ul v-if="items.length" class="profile-reviews__list" data-testid="reviews-list">
      <li
        v-for="review in items"
        :key="review.id"
        class="profile-reviews__item"
        data-testid="review-item"
      >
        <div class="profile-reviews__head">
          <RouterLink
            v-if="review.author"
            :to="`/users/${review.author.id}`"
            class="profile-reviews__author"
            data-testid="review-author"
          >
            <PersonAvatar
              :name="review.author.name"
              :user-id="review.author.id"
              :avatar-id="review.author.avatar_id"
            />
            <span class="app-break">{{ review.author.name }}</span>
          </RouterLink>
          <span v-else class="profile-reviews__author" data-testid="review-author-anonymous">
            <span class="profile-reviews__anonymous-icon">
              <i class="pi pi-user" aria-hidden="true" />
            </span>
            Анонимно
          </span>
          <Tag
            v-if="review.author && review.anonymous"
            value="анонимно"
            severity="secondary"
            data-testid="review-anonymous-mark"
          />
          <span
            class="profile-reviews__stars"
            :aria-label="`Оценка ${review.stars} из 5`"
            data-testid="review-stars"
          >
            <i
              v-for="star in STARS"
              :key="star"
              :class="['pi', star <= review.stars ? 'pi-star-fill' : 'pi-star']"
              aria-hidden="true"
            />
          </span>
        </div>

        <p v-if="review.text" class="profile-reviews__text app-break" data-testid="review-text">
          {{ review.text }}
        </p>

        <div class="profile-reviews__meta">
          <RouterLink
            v-if="review.event.id"
            :to="`/events/${review.event.id}`"
            class="profile-reviews__event app-break"
            data-testid="review-event"
          >
            {{ review.event.title }}
          </RouterLink>
          <span v-else class="profile-reviews__event app-break" data-testid="review-event">
            {{ review.event.title }}
          </span>
          <span data-testid="review-date">{{ formatLongDate(review.created_at) }}</span>
          <Button
            v-if="isAdmin"
            type="button"
            label="Удалить"
            icon="pi pi-trash"
            severity="danger"
            text
            size="small"
            class="profile-reviews__delete"
            data-testid="review-admin-delete"
            @click="confirmDelete(review)"
          />
        </div>
      </li>
    </ul>

    <Button
      v-if="items.length < total"
      type="button"
      label="Показать ещё"
      outlined
      :loading="loading"
      class="profile-reviews__more"
      data-testid="reviews-more"
      @click="load(true)"
    />
  </section>
</template>

<style scoped>
.profile-reviews {
  display: flex;
  flex-direction: column;
  gap: 16px;
  /* app-card узкая (форма входа), раздел отзывов — во всю ширину профиля */
  max-width: none;
  width: 100%;
}

.profile-reviews__title {
  margin: 0;
  font-size: 1.25rem;
}

.profile-reviews__empty {
  margin: 0;
  color: var(--app-text-muted);
}

.profile-reviews__list {
  margin: 0;
  padding: 0;
  list-style: none;
  display: grid;
  gap: 12px;
}

.profile-reviews__item {
  display: grid;
  gap: 8px;
  padding: 16px;
  border: 1px solid var(--app-border);
  border-radius: 12px;
}

.profile-reviews__head {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px 12px;
}

.profile-reviews__author {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
  font-weight: 600;
  color: inherit;
  text-decoration: none;
}

a.profile-reviews__author:hover {
  text-decoration: underline;
}

.profile-reviews__anonymous-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: var(--p-surface-100);
  color: var(--app-text-muted);
}

.profile-reviews__stars {
  display: inline-flex;
  gap: 2px;
  margin-left: auto;
  color: var(--app-accent);
}

.profile-reviews__text {
  margin: 0;
  white-space: pre-line;
}

.profile-reviews__meta {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 4px 12px;
  color: var(--app-text-muted);
  font-size: 0.875rem;
}

.profile-reviews__event {
  color: inherit;
}

.profile-reviews__delete {
  margin-left: auto;
  min-height: 44px;
}

.profile-reviews__more {
  align-self: center;
  min-height: 44px;
}
</style>
