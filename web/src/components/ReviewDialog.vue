<script setup lang="ts">
/**
 * Окно отзыва о человеке по итогам мероприятия: звёзды (обязательно), комментарий,
 * «Оставить анонимно». Для существующего отзыва поля заполнены и есть «Удалить отзыв».
 * Окно отзывов проверяет сервер: 409 показывается сообщением, после чего родитель
 * перезапрашивает данные (событие `stale`).
 */
import Button from 'primevue/button'
import Checkbox from 'primevue/checkbox'
import Dialog from 'primevue/dialog'
import Rating from 'primevue/rating'
import Textarea from 'primevue/textarea'
import { useConfirm } from 'primevue/useconfirm'
import { useToast } from 'primevue/usetoast'
import { computed, ref, watch } from 'vue'

import { ApiError } from '@/api/client'
import {
  REVIEW_TEXT_MAX_LENGTH,
  createReview,
  deleteReview,
  updateReview,
  type Review,
  type ReviewKind,
} from '@/api/reviews'
import { useIsMobile } from '@/utils/breakpoints'

const props = defineProps<{
  visible: boolean
  eventId: string
  target: { id: string; name: string }
  kind: ReviewKind
  review: Review | null
}>()
const emit = defineEmits<{
  'update:visible': [visible: boolean]
  saved: [review: Review]
  deleted: [review: Review]
  stale: []
}>()

const toast = useToast()
const confirm = useConfirm()
const isMobile = useIsMobile()

const stars = ref<number | null>(null)
const text = ref('')
const anonymous = ref(false)
const starsError = ref<string | null>(null)
const busy = ref(false)

const kindLabel = computed(() =>
  props.kind === 'organizer' ? 'как об организаторе' : 'как об участнике',
)

watch(
  () => [props.visible, props.review] as const,
  ([visible]) => {
    if (!visible) return
    stars.value = props.review?.stars ?? null
    text.value = props.review?.text ?? ''
    anonymous.value = props.review?.anonymous ?? false
    starsError.value = null
  },
  { immediate: true },
)

const STALE_MESSAGES: Record<string, string> = {
  review_closed: 'Время для отзыва истекло',
  review_not_open: 'Отзыв можно оставить через сутки после начала мероприятия',
  review_exists: 'Вы уже оставили отзыв',
}

function close(): void {
  emit('update:visible', false)
}

function handleError(error: unknown): void {
  const code = error instanceof ApiError ? error.code : null
  const stale = code ? STALE_MESSAGES[code] : undefined
  if (stale) {
    toast.add({ severity: 'warn', summary: stale, life: 4000 })
    close()
    emit('stale')
    return
  }
  toast.add({ severity: 'error', summary: 'Не удалось сохранить отзыв', life: 4000 })
}

async function save(): Promise<void> {
  if (!stars.value) {
    starsError.value = 'Поставьте оценку'
    return
  }
  starsError.value = null
  busy.value = true
  const body = { stars: stars.value, text: text.value.trim() || null, anonymous: anonymous.value }
  try {
    const saved = props.review
      ? await updateReview(props.review.id, body)
      : await createReview(props.eventId, { target_id: props.target.id, ...body })
    toast.add({ severity: 'success', summary: 'Отзыв сохранён', life: 3000 })
    emit('saved', saved)
    close()
  } catch (error) {
    handleError(error)
  } finally {
    busy.value = false
  }
}

function confirmDelete(): void {
  confirm.require({
    header: 'Удалить отзыв?',
    message: 'Отзыв перестанет учитываться в рейтинге.',
    icon: 'pi pi-exclamation-triangle',
    rejectProps: {
      label: 'Отмена',
      severity: 'secondary',
      outlined: true,
      'data-testid': 'confirm-reject',
    },
    acceptProps: { label: 'Удалить', severity: 'danger', 'data-testid': 'confirm-accept' },
    accept: () => void remove(),
  })
}

async function remove(): Promise<void> {
  const review = props.review
  if (!review) return
  busy.value = true
  try {
    await deleteReview(review.id)
    toast.add({ severity: 'success', summary: 'Отзыв удалён', life: 3000 })
    emit('deleted', review)
    close()
  } catch (error) {
    handleError(error)
  } finally {
    busy.value = false
  }
}

function onStars(value: number | null): void {
  stars.value = value
  if (value) starsError.value = null
}
</script>

<template>
  <Dialog
    :visible="visible"
    modal
    :draggable="false"
    :dismissable-mask="false"
    :class="['review-dialog', { 'review-dialog--fullscreen': isMobile }]"
    data-testid="review-dialog"
    @update:visible="emit('update:visible', $event)"
  >
    <template #header>
      <div class="review-dialog__head">
        <h2 class="review-dialog__title app-break" data-testid="review-title">
          Отзыв: {{ target.name }}
        </h2>
        <span class="review-dialog__kind" data-testid="review-kind">{{ kindLabel }}</span>
      </div>
    </template>

    <form id="review-form" class="review-dialog__form" novalidate @submit.prevent="save">
      <div class="review-dialog__field">
        <span id="review-stars-label" class="review-dialog__label">Оценка</span>
        <Rating
          :model-value="stars ?? undefined"
          :stars="5"
          class="review-dialog__stars"
          aria-labelledby="review-stars-label"
          data-testid="review-stars"
          @update:model-value="onStars"
        />
        <small v-if="starsError" class="app-field-error" data-testid="review-stars-error">
          {{ starsError }}
        </small>
      </div>

      <div class="review-dialog__field">
        <label for="review-text" class="review-dialog__label">Комментарий</label>
        <Textarea
          id="review-text"
          v-model="text"
          :maxlength="REVIEW_TEXT_MAX_LENGTH"
          rows="4"
          auto-resize
          placeholder="Необязательно"
          data-testid="review-text"
        />
        <small class="review-dialog__counter" data-testid="review-counter">
          {{ text.length }}/{{ REVIEW_TEXT_MAX_LENGTH }}
        </small>
      </div>

      <div class="review-dialog__check">
        <Checkbox
          v-model="anonymous"
          input-id="review-anonymous"
          binary
          data-testid="review-anonymous"
        />
        <label for="review-anonymous">Оставить анонимно</label>
      </div>

      <Button
        v-if="review"
        type="button"
        label="Удалить отзыв"
        icon="pi pi-trash"
        severity="danger"
        text
        class="review-dialog__delete"
        :disabled="busy"
        data-testid="review-delete"
        @click="confirmDelete"
      />
    </form>

    <template #footer>
      <div class="app-actions app-actions--inline review-dialog__actions">
        <Button
          type="submit"
          form="review-form"
          label="Сохранить"
          icon="pi pi-check"
          :loading="busy"
          :disabled="busy"
          data-testid="review-save"
        />
        <Button
          type="button"
          label="Отмена"
          severity="secondary"
          outlined
          :disabled="busy"
          data-testid="review-cancel"
          @click="close"
        />
      </div>
    </template>
  </Dialog>
</template>

<style scoped>
.review-dialog__head {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.review-dialog__title {
  margin: 0;
  font-size: 1.25rem;
}

.review-dialog__kind {
  color: var(--app-text-muted);
  font-size: 0.875rem;
}

.review-dialog__form {
  display: grid;
  gap: 16px;
}

.review-dialog__field {
  display: grid;
  gap: 6px;
}

.review-dialog__label {
  font-weight: 600;
}

/* Звёзды крупные: цель нажатия не меньше 44 px */
.review-dialog__stars :deep(.p-rating-option) {
  width: 44px;
  height: 44px;
  justify-content: center;
}

.review-dialog__stars :deep(.p-rating-icon) {
  width: 28px;
  height: 28px;
}

.review-dialog__counter {
  justify-self: end;
  color: var(--app-text-muted);
}

.review-dialog__check {
  display: flex;
  align-items: center;
  gap: 10px;
  min-height: 44px;
}

.review-dialog__delete {
  justify-self: start;
}
</style>

<style>
/* Dialog рендерится в body (teleport), поэтому стили не scoped */
.review-dialog.p-dialog {
  width: min(480px, calc(100vw - 32px));
  max-height: calc(100dvh - 32px);
  border-radius: 16px;
}

.review-dialog--fullscreen.p-dialog {
  width: 100vw;
  height: 100dvh;
  max-height: 100dvh;
  margin: 0;
  border-radius: 0;
}

.review-dialog__actions {
  width: 100%;
}
</style>
