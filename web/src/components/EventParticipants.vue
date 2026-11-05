<script setup lang="ts">
/**
 * Участники мероприятия: аватар или инициалы, имя (ссылки на профиль), Telegram ссылкой;
 * автору и админу — «Исключить» у каждого, кроме организатора.
 * Рейтинг: у организатора — как организатора, у остальных — как участника.
 * В открытом окне отзывов у каждого, кроме себя, — «Оценить» или своя оценка и «Изменить».
 */
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import { RouterLink } from 'vue-router'

import type { Participant } from '@/api/events'
import type { Review } from '@/api/reviews'
import PersonAvatar from '@/components/PersonAvatar.vue'
import RatingBadge from '@/components/RatingBadge.vue'
import { telegramUrl } from '@/utils/format'

withDefaults(
  defineProps<{
    participants: Participant[] | null
    organizerId: string
    count: number
    max: number
    /** Список доступен (записан или администратор) */
    visible: boolean
    canRemove: boolean
    /** Текущий пользователь: себя не оценивают */
    currentUserId?: string | null
    /** Свои отзывы по получателю */
    reviews?: Record<string, Review>
    /** Окно отзывов открыто, и пользователь записан */
    canReview?: boolean
    /** Срок отзывов: «Оценить участников можно до …» */
    reviewHint?: string | null
  }>(),
  { currentUserId: null, reviews: () => ({}), canReview: false, reviewHint: null },
)
const emit = defineEmits<{
  remove: [participant: Participant]
  review: [participant: Participant]
}>()

const STARS = [1, 2, 3, 4, 5]
</script>

<template>
  <section class="participants" data-testid="participants">
    <h3 class="participants__title" data-testid="participants-title">
      Участники ({{ count }}/{{ max }})
    </h3>
    <p v-if="visible && reviewHint" class="participants__review-hint" data-testid="review-hint">
      {{ reviewHint }}
    </p>
    <p v-if="!visible" class="participants__hint" data-testid="participants-hidden">
      Список участников виден после записи
    </p>
    <ul v-else-if="participants" class="participants__list" data-testid="participants-list">
      <li
        v-for="participant in participants"
        :key="participant.id"
        class="participants__item"
        data-testid="participant"
      >
        <RouterLink
          :to="`/users/${participant.id}`"
          :aria-label="`Профиль: ${participant.name}`"
          tabindex="-1"
          class="participants__avatar-link"
        >
          <PersonAvatar
            :name="participant.name"
            :user-id="participant.id"
            :avatar-id="participant.avatar_id"
          />
        </RouterLink>
        <div class="participants__info">
          <span class="participants__name-row">
            <RouterLink
              :to="`/users/${participant.id}`"
              class="participants__name app-break"
              data-testid="participant-name"
            >
              {{ participant.name }}
            </RouterLink>
            <RatingBadge
              :value="participant.rating"
              :label="participant.id === organizerId ? 'Рейтинг организатора' : 'Рейтинг участника'"
            />
          </span>
          <a
            v-if="participant.telegram"
            :href="telegramUrl(participant.telegram)"
            target="_blank"
            rel="noopener noreferrer"
            class="participants__telegram"
            data-testid="participant-telegram"
          >
            {{ participant.telegram }}
          </a>
        </div>
        <div
          v-if="participant.id !== currentUserId && (reviews[participant.id] || canReview)"
          class="participants__review"
          data-testid="participant-review"
        >
          <span
            v-if="reviews[participant.id]"
            class="participants__my-stars"
            :aria-label="`Ваша оценка: ${reviews[participant.id]?.stars} из 5`"
            data-testid="participant-my-stars"
          >
            <i
              v-for="star in STARS"
              :key="star"
              :class="[
                'pi',
                star <= (reviews[participant.id]?.stars ?? 0) ? 'pi-star-fill' : 'pi-star',
              ]"
              aria-hidden="true"
            />
          </span>
          <Button
            v-if="canReview"
            type="button"
            :label="reviews[participant.id] ? 'Изменить' : 'Оценить'"
            :icon="reviews[participant.id] ? 'pi pi-pencil' : 'pi pi-star'"
            text
            size="small"
            :aria-label="`${reviews[participant.id] ? 'Изменить отзыв' : 'Оценить'}: ${participant.name}`"
            data-testid="participant-review-button"
            @click="emit('review', participant)"
          />
        </div>
        <Tag
          v-if="participant.id === organizerId"
          value="Организатор"
          severity="secondary"
          data-testid="participant-organizer"
        />
        <Button
          v-else-if="canRemove"
          type="button"
          label="Исключить"
          icon="pi pi-user-minus"
          severity="danger"
          text
          :aria-label="`Исключить ${participant.name}`"
          data-testid="participant-remove"
          @click="emit('remove', participant)"
        />
      </li>
    </ul>
  </section>
</template>

<style scoped>
.participants__title {
  margin: 0 0 10px;
  color: var(--p-primary-700);
  font-size: 0.75rem;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.participants__review-hint {
  margin: 0 0 10px;
  color: var(--app-text-muted);
  font-size: 0.875rem;
}

.participants__name-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 4px 8px;
}

.participants__review {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 4px;
}

.participants__review .p-button {
  min-height: 44px;
}

.participants__my-stars {
  display: inline-flex;
  gap: 2px;
  color: var(--app-accent);
  font-size: 0.75rem;
}

.participants__hint {
  margin: 0;
  color: var(--app-text-muted);
}

.participants__list {
  margin: 0;
  padding: 0;
  list-style: none;
  display: grid;
  gap: 8px;
}

.participants__item {
  display: flex;
  align-items: center;
  gap: 12px;
  min-height: 60px;
  padding: 8px 12px;
  border: 1px solid var(--app-border);
  border-radius: 12px;
}

.participants__info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.participants__name {
  font-weight: 600;
  color: inherit;
  text-decoration: none;
}

.participants__name:hover,
.participants__name:focus-visible {
  color: var(--p-primary-700);
  text-decoration: underline;
}

.participants__avatar-link {
  display: inline-flex;
  border-radius: 50%;
}

.participants__telegram {
  color: var(--p-primary-700);
  font-size: 0.875rem;
  text-decoration: none;
  overflow-wrap: anywhere;
}

.participants__telegram:hover {
  text-decoration: underline;
}
</style>
