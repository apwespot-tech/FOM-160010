<script setup lang="ts">
/**
 * Мероприятие в модальном окне поверх списка (дочерний маршрут /events/:id).
 * Просмотр оформлен для чтения (плитки, блок организатора); по «Редактировать»
 * содержимое окна перестраивается в форму — ту же, что в окне создания
 * (стандарт «Окна и карточки с данными»: приоритет у просмотра).
 * Права в интерфейсе — подсказки; проверяет их сервер, после каждого действия
 * данные перезапрашиваются, а карточка в списке под окном обновляется.
 * На начавшемся мероприятии записанному показываются свои отзывы и срок окна отзывов.
 */
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import ProgressSpinner from 'primevue/progressspinner'
import Tag from 'primevue/tag'
import { useConfirm } from 'primevue/useconfirm'
import { useToast } from 'primevue/usetoast'
import { computed, nextTick, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { ApiError } from '@/api/client'
import {
  deleteEvent,
  getEvent,
  joinEvent,
  leaveEvent,
  listParticipants,
  removeParticipant,
  type EventItem,
  type Participant,
} from '@/api/events'
import { getMyReviews, type MyReviews, type Review } from '@/api/reviews'
import EventFormFields from '@/components/EventFormFields.vue'
import EventGallery from '@/components/EventGallery.vue'
import EventParticipants from '@/components/EventParticipants.vue'
import EventTile from '@/components/EventTile.vue'
import OrganizerCard from '@/components/OrganizerCard.vue'
import ReviewDialog from '@/components/ReviewDialog.vue'
import { provideEventForm } from '@/composables/eventFormContext'
import { injectEventListUpdates } from '@/composables/useEventList'
import { eventErrorMessage, useEventForm } from '@/composables/useEventForm'
import { useRequireCompletedProfile } from '@/composables/useRequireCompletedProfile'
import { useSessionStore } from '@/stores/session'
import { useIsMobile } from '@/utils/breakpoints'
import { formatDayTime, formatDuration, formatEventDay } from '@/utils/dates'
import { formatFreePlaces, formatMinAge } from '@/utils/format'

const route = useRoute()
const router = useRouter()
const session = useSessionStore()
const toast = useToast()
const requireCompletedProfile = useRequireCompletedProfile()
const confirm = useConfirm()
const isMobile = useIsMobile()
const list = injectEventListUpdates()

const event = ref<EventItem | null>(null)
const participants = ref<Participant[] | null>(null)
const notFound = ref(false)
const loadError = ref(false)
const busy = ref(false)
const editing = ref(false)
const myReviews = ref<MyReviews | null>(null)
const reviewTarget = ref<Participant | null>(null)
const reviewDialogVisible = ref(false)

const eventId = computed(() => String(route.params.id))
const isAdmin = computed(() => session.profile?.roles.includes('admin') === true)
const isOrganizer = computed(() => event.value?.organizer.id === session.profile?.id)
const isPast = computed(() => (event.value ? new Date(event.value.starts_at) <= new Date() : false))
const canManage = computed(() => (isOrganizer.value || isAdmin.value) && !isPast.value)
const canSeeParticipants = computed(() => event.value?.is_joined === true || isAdmin.value)
const ageLimit = computed(() => event.value?.min_age ?? 0)
const joinBlockedReason = computed(() => {
  if (!event.value) return null
  if (event.value.is_full) return 'Мест нет'
  // Без даты рождения возраст неизвестен: запись попросит сначала заполнить профиль
  const age = session.profile?.age ?? null
  if (age !== null && age < ageLimit.value) return `Доступно с ${ageLimit.value} лет`
  return null
})
const when = computed(() => (event.value ? formatEventDay(event.value.starts_at) : null))
const showFooter = computed(() => !!event.value && !isPast.value)

// Окно отзывов: границы приходят с сервером, он же проверяет их при сохранении
const reviewWindow = computed<'before' | 'open' | 'closed' | null>(() => {
  if (!myReviews.value) return null
  const now = new Date()
  if (now < new Date(myReviews.value.opens_at)) return 'before'
  if (now < new Date(myReviews.value.closes_at)) return 'open'
  return 'closed'
})
const canReview = computed(() => reviewWindow.value === 'open')
const reviewHint = computed(() => {
  if (!myReviews.value) return null
  if (reviewWindow.value === 'before')
    return `Оценить участников можно будет с ${formatDayTime(myReviews.value.opens_at)}`
  if (reviewWindow.value === 'open')
    return `Оценить участников можно до ${formatDayTime(myReviews.value.closes_at)}`
  return null
})
const reviewsByTarget = computed<Record<string, Review>>(() =>
  Object.fromEntries((myReviews.value?.items ?? []).map((review) => [review.target_id, review])),
)
const reviewKind = computed(() =>
  reviewTarget.value?.id === event.value?.organizer.id ? 'organizer' : 'participant',
)

// Если поля сохранились, а фото нет — окно и список уже показывают новые поля
const controller = useEventForm({ getInitial: () => event.value, onPartialSave: applyEvent })
provideEventForm(controller)
const { saving, requiredFilled, reset, submit } = controller

/** Закрыть окно: назад к списку, если пришли из него, иначе — на список с тем же query. */
function close(): void {
  const back = router.options.history.state.back
  if (typeof back === 'string' && back.split('?')[0] === '/') router.back()
  else void router.replace({ path: '/', query: route.query })
}

function onVisible(visible: boolean): void {
  if (!visible) close()
}

/** Новые данные мероприятия: и в окне, и в карточке списка. */
function applyEvent(updated: EventItem): void {
  event.value = updated
  list.replaceItem(updated)
}

async function loadParticipants(): Promise<void> {
  if (!canSeeParticipants.value) {
    participants.value = null
    return
  }
  try {
    participants.value = await listParticipants(eventId.value)
  } catch {
    participants.value = null
  }
}

/** Свои отзывы — только записанному на начавшемся мероприятии. */
async function loadMyReviews(): Promise<void> {
  if (!event.value?.is_joined || !isPast.value) {
    myReviews.value = null
    return
  }
  try {
    myReviews.value = await getMyReviews(eventId.value)
  } catch {
    myReviews.value = null
  }
}

async function load(): Promise<void> {
  loadError.value = false
  try {
    applyEvent(await getEvent(eventId.value))
    notFound.value = false
  } catch (error) {
    event.value = null
    // 422 — в адресе не UUID: такого мероприятия тоже нет, «Повторить» не поможет
    if (error instanceof ApiError && (error.status === 404 || error.status === 422)) {
      notFound.value = true
    } else loadError.value = true
    return
  }
  await Promise.all([loadParticipants(), loadMyReviews()])
}

watch(
  eventId,
  () => {
    editing.value = false
    void load()
  },
  { immediate: true },
)

function showError(error: unknown): void {
  toast.add({ severity: 'error', summary: eventErrorMessage(error, ageLimit.value), life: 4000 })
}

/** Действие с перезапросом данных после ответа сервера (успешного или нет). */
async function act(action: () => Promise<EventItem>, success: string): Promise<void> {
  busy.value = true
  try {
    applyEvent(await action())
    toast.add({ severity: 'success', summary: success, life: 3000 })
    await loadParticipants()
  } catch (error) {
    showError(error)
    await load()
  } finally {
    busy.value = false
  }
}

function join() {
  if (!requireCompletedProfile()) return
  return act(() => joinEvent(eventId.value), 'Вы записаны')
}

function leave() {
  return act(() => leaveEvent(eventId.value), 'Вы отказались от участия')
}

async function startEdit() {
  reset()
  editing.value = true
  await nextTick()
  document.querySelector<HTMLInputElement>('#event-edit-title')?.focus()
}

function cancelEdit() {
  reset()
  editing.value = false
}

async function save() {
  const before = event.value
  const saved = await submit()
  if (!saved) return
  editing.value = false
  if (saved !== before) {
    applyEvent(saved)
    toast.add({ severity: 'success', summary: 'Мероприятие сохранено', life: 3000 })
  }
}

function confirmDelete() {
  confirm.require({
    header: 'Удалить мероприятие?',
    message: 'Мероприятие и все записи участников будут удалены. Это действие нельзя отменить.',
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

async function remove() {
  busy.value = true
  try {
    await deleteEvent(eventId.value)
    list.removeItem(eventId.value)
    toast.add({ severity: 'success', summary: 'Мероприятие удалено', life: 3000 })
    close()
  } catch (error) {
    showError(error)
    await load()
  } finally {
    busy.value = false
  }
}

function openReview(participant: Participant): void {
  reviewTarget.value = participant
  reviewDialogVisible.value = true
}

/** Отзыв сохранён или удалён: своя оценка сразу, рейтинги — перезапросом. */
function onReviewChanged(review: Review, removed = false): void {
  if (myReviews.value) {
    const others = myReviews.value.items.filter((item) => item.id !== review.id)
    myReviews.value = { ...myReviews.value, items: removed ? others : [...others, review] }
  }
  void load()
}

function confirmRemoveParticipant(participant: Participant) {
  confirm.require({
    header: 'Исключить участника?',
    message: `${participant.name} будет исключён из мероприятия, место освободится.`,
    icon: 'pi pi-exclamation-triangle',
    rejectProps: {
      label: 'Отмена',
      severity: 'secondary',
      outlined: true,
      'data-testid': 'confirm-reject',
    },
    acceptProps: { label: 'Исключить', severity: 'danger', 'data-testid': 'confirm-accept' },
    accept: () =>
      void act(() => removeParticipant(eventId.value, participant.id), 'Участник исключён'),
  })
}
</script>

<template>
  <Dialog
    :visible="true"
    modal
    :dismissable-mask="!editing"
    :draggable="false"
    :class="['event-modal', { 'event-modal--fullscreen': isMobile }]"
    data-testid="event-modal"
    @update:visible="onVisible"
  >
    <template #header>
      <h2 v-if="editing" class="event-modal__edit-title" data-testid="event-edit-header">
        Редактирование мероприятия
      </h2>
      <div v-else-if="event" class="event-modal__head" data-testid="event-head">
        <div class="event-modal__tags">
          <Tag :value="event.category.name" class="event-modal__tag" data-testid="event-category">
            <template #icon><i class="pi pi-tag" aria-hidden="true" /></template>
          </Tag>
          <Tag
            v-if="isOrganizer"
            value="Вы организатор"
            class="event-modal__tag event-modal__tag--accent"
            data-testid="organizer-mark"
          >
            <template #icon><i class="pi pi-crown" aria-hidden="true" /></template>
          </Tag>
          <Tag
            v-if="isPast"
            value="Мероприятие прошло"
            severity="secondary"
            data-testid="event-past"
          />
        </div>
        <h2 class="event-modal__title app-break" data-testid="event-title">{{ event.title }}</h2>
      </div>
      <span v-else />
    </template>

    <div class="event-modal__body">
      <div v-if="notFound" class="event-modal__status" data-testid="event-not-found">
        <h2 class="app-title">Мероприятие не найдено</h2>
        <p class="app-subtitle">Возможно, его удалили или ссылка неверная.</p>
        <Button type="button" label="К мероприятиям" outlined @click="close" />
      </div>

      <div v-else-if="loadError" class="event-modal__status" data-testid="event-load-error">
        <p>Не удалось загрузить мероприятие</p>
        <Button type="button" label="Повторить" icon="pi pi-refresh" outlined @click="load" />
      </div>

      <!-- Редактирование: форма как в окне создания -->
      <form
        v-else-if="event && editing"
        id="event-edit-form"
        novalidate
        data-testid="event-edit-form"
        @submit.prevent="save"
      >
        <EventFormFields id-prefix="event-edit" />
      </form>

      <!-- Просмотр -->
      <template v-else-if="event && when">
        <EventGallery
          v-if="event.photos.length"
          :event-id="event.id"
          :photos="event.photos"
          :title="event.title"
        />

        <div class="event-modal__tiles">
          <EventTile icon="pi-calendar" label="Когда">
            <span data-testid="event-starts-at">{{ when.day }}</span>
            <template #hint>
              <span data-testid="event-time">{{ when.time }}</span>
            </template>
          </EventTile>

          <EventTile icon="pi-clock" label="Длительность">
            <span
              :class="{ 'event-modal__empty': event.duration_minutes === null }"
              data-testid="event-duration"
            >
              {{
                event.duration_minutes === null
                  ? 'не указана'
                  : `~ ${formatDuration(event.duration_minutes)}`
              }}
            </span>
          </EventTile>

          <EventTile icon="pi-map-marker" label="Где">
            <span data-testid="event-where">
              <span data-testid="event-city">{{ event.city.name }}</span
              >,
              <span data-testid="event-place">{{ event.place }}</span>
            </span>
          </EventTile>

          <EventTile icon="pi-users" label="Места и возраст">
            <span class="event-modal__places" data-testid="event-places">
              {{ event.participants_count }} из {{ event.max_participants }}
              <Tag
                v-if="event.min_age > 0"
                :value="formatMinAge(event.min_age)"
                severity="secondary"
                data-testid="event-age"
              />
            </span>
            <template #hint>
              <span data-testid="event-free">{{ formatFreePlaces(event.free_places) }}</span>
            </template>
          </EventTile>
        </div>

        <OrganizerCard
          :organizer="event.organizer"
          :created-at="event.created_at"
          :can-write="!isOrganizer"
          :linked="canSeeParticipants"
        />

        <section class="event-modal__section">
          <h3 class="event-modal__section-title">Описание</h3>
          <p class="event-modal__description app-break" data-testid="event-description">
            {{ event.description }}
          </p>
        </section>

        <EventParticipants
          :participants="participants"
          :organizer-id="event.organizer.id"
          :count="event.participants_count"
          :max="event.max_participants"
          :visible="canSeeParticipants"
          :can-remove="canManage"
          :current-user-id="session.profile?.id ?? null"
          :reviews="reviewsByTarget"
          :can-review="canReview"
          :review-hint="reviewHint"
          @remove="confirmRemoveParticipant"
          @review="openReview"
        />

        <ReviewDialog
          v-if="reviewTarget"
          v-model:visible="reviewDialogVisible"
          :event-id="event.id"
          :target="reviewTarget"
          :kind="reviewKind"
          :review="reviewsByTarget[reviewTarget.id] ?? null"
          @saved="onReviewChanged"
          @deleted="onReviewChanged($event, true)"
          @stale="load"
        />
      </template>

      <div v-else class="event-modal__status" data-testid="event-loading">
        <ProgressSpinner style="width: 40px; height: 40px" stroke-width="4" aria-label="Загрузка" />
      </div>
    </div>

    <template v-if="showFooter && event" #footer>
      <!-- Редактирование: «Отмена» и «Сохранить» на месте «Удалить» и «Редактировать» -->
      <div v-if="editing" class="event-modal__footer" data-testid="event-footer">
        <span class="event-modal__footer-spacer" />
        <Button
          type="button"
          label="Отмена"
          severity="secondary"
          outlined
          data-testid="event-cancel"
          @click="cancelEdit"
        />
        <Button
          type="submit"
          form="event-edit-form"
          label="Сохранить"
          icon="pi pi-check"
          :loading="saving"
          :disabled="!requiredFilled || saving"
          data-testid="event-save"
        />
      </div>

      <div v-else class="event-modal__footer" data-testid="event-footer">
        <Button
          v-if="canManage"
          type="button"
          label="Удалить"
          icon="pi pi-trash"
          severity="danger"
          outlined
          :disabled="busy"
          data-testid="event-delete"
          @click="confirmDelete"
        />

        <span class="event-modal__footer-spacer" />

        <!-- Участие: организатор не записывается и не отказывается -->
        <template v-if="!isOrganizer">
          <span
            v-if="!event.is_joined && joinBlockedReason"
            class="event-modal__reason"
            data-testid="join-blocked"
          >
            {{ joinBlockedReason }}
          </span>
          <Button
            v-if="event.is_joined"
            type="button"
            label="Отказаться"
            icon="pi pi-times"
            severity="secondary"
            outlined
            :loading="busy"
            :disabled="busy"
            data-testid="leave"
            @click="leave"
          />
          <Button
            v-else
            type="button"
            label="Записаться"
            icon="pi pi-check"
            :loading="busy"
            :disabled="busy || joinBlockedReason !== null"
            data-testid="join"
            @click="join"
          />
        </template>

        <Button
          v-if="canManage"
          type="button"
          label="Редактировать"
          icon="pi pi-pencil"
          :disabled="busy"
          data-testid="event-edit"
          @click="startEdit"
        />
      </div>
    </template>
  </Dialog>
</template>

<style>
/* Dialog рендерится в body (teleport), поэтому стили не scoped */
.event-modal.p-dialog {
  width: min(640px, calc(100vw - 32px));
  max-height: calc(100dvh - 32px);
  border-radius: 16px;
}

.event-modal--fullscreen.p-dialog {
  width: 100vw;
  height: 100dvh;
  max-height: 100dvh;
  margin: 0;
  border-radius: 0;
}

.event-modal .p-dialog-header {
  align-items: flex-start;
  gap: 12px;
  border-bottom: 1px solid var(--app-border);
}

.event-modal .p-dialog-footer {
  border-top: 1px solid var(--app-border);
  padding-top: 16px;
}

.event-modal__head {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.event-modal__tags {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}

.event-modal__tag {
  background: var(--p-primary-50);
  color: var(--p-primary-700);
  border: 1px solid var(--p-primary-100);
}

/* Оранжевый — только акцент */
.event-modal__tag--accent {
  background: var(--app-accent-soft);
  color: var(--app-accent-text);
  border-color: var(--app-accent-border);
}

.event-modal__title,
.event-modal__edit-title {
  margin: 0;
  font-size: 1.375rem;
  font-weight: 700;
  line-height: 1.3;
}

.event-modal__edit-title {
  font-size: 1.25rem;
}

.event-modal__body {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding-top: 16px;
}

.event-modal__status {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 32px 0;
  text-align: center;
}

.event-modal__tiles {
  display: grid;
  gap: 12px;
}

@media (min-width: 640px) {
  .event-modal__tiles {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

.event-modal__places {
  display: inline-flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}

.event-modal__empty {
  color: var(--app-text-muted);
  font-style: italic;
  font-weight: 400;
}

.event-modal__section {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.event-modal__section-title {
  margin: 0;
  color: var(--app-text-muted);
  font-size: 0.75rem;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.event-modal__description {
  margin: 0;
  padding: 14px 16px;
  background: var(--p-surface-50);
  border: 1px solid var(--app-border);
  border-radius: 12px;
  white-space: pre-line;
}

.event-modal__footer {
  width: 100%;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px 12px;
}

.event-modal__footer-spacer {
  flex: 1;
}

.event-modal__reason {
  color: var(--app-text-muted);
  font-size: 0.875rem;
}

/* На мобильном кнопки футера делят строку поровну */
@media (max-width: 639px) {
  .event-modal__footer .p-button {
    flex: 1 1 0;
    min-width: 0;
  }

  .event-modal__footer-spacer {
    display: none;
  }

  .event-modal__reason {
    flex-basis: 100%;
    order: -1;
  }
}
</style>
