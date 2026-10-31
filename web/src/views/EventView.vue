<script setup lang="ts">
/**
 * Страница мероприятия: данные, запись и отказ, управление для автора и администратора,
 * список участников. Права в интерфейсе — подсказки; проверяет их сервер, а после
 * каждого действия страница перезапрашивает актуальные данные.
 */
import Button from 'primevue/button'
import ProgressSpinner from 'primevue/progressspinner'
import { useConfirm } from 'primevue/useconfirm'
import { useToast } from 'primevue/usetoast'
import { computed, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'

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
import EventDetails from '@/components/EventDetails.vue'
import EventParticipants from '@/components/EventParticipants.vue'
import { eventErrorMessage } from '@/composables/useEventForm'
import { useSessionStore } from '@/stores/session'

const route = useRoute()
const router = useRouter()
const session = useSessionStore()
const toast = useToast()
const confirm = useConfirm()

const event = ref<EventItem | null>(null)
const participants = ref<Participant[] | null>(null)
const notFound = ref(false)
const loadError = ref(false)
const busy = ref(false)

const eventId = computed(() => String(route.params.id))
const isAdmin = computed(() => session.profile?.roles.includes('admin') === true)
const isOrganizer = computed(() => event.value?.organizer.id === session.profile?.id)
const isPast = computed(() => (event.value ? new Date(event.value.starts_at) <= new Date() : false))
const canManage = computed(() => (isOrganizer.value || isAdmin.value) && !isPast.value)
const canSeeParticipants = computed(() => event.value?.is_joined === true || isAdmin.value)
const ageLimit = computed(() => event.value?.min_age ?? 0)
const tooYoung = computed(() => (session.profile?.age ?? 0) < ageLimit.value)
const joinBlockedReason = computed(() => {
  if (!event.value) return null
  if (event.value.is_full) return 'Мест нет'
  if (tooYoung.value) return `Доступно с ${ageLimit.value} лет`
  return null
})

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

async function load(): Promise<void> {
  loadError.value = false
  try {
    event.value = await getEvent(eventId.value)
    notFound.value = false
  } catch (error) {
    event.value = null
    if (error instanceof ApiError && error.status === 404) notFound.value = true
    else loadError.value = true
    return
  }
  await loadParticipants()
}

watch(eventId, () => void load(), { immediate: true })

function showError(error: unknown): void {
  toast.add({
    severity: 'error',
    summary: eventErrorMessage(error, ageLimit.value),
    life: 4000,
  })
}

/** Действие с перезапросом данных после ответа сервера (успешного или нет). */
async function act(action: () => Promise<EventItem>, success: string): Promise<void> {
  busy.value = true
  try {
    event.value = await action()
    toast.add({ severity: 'success', summary: success, life: 3000 })
    await loadParticipants()
  } catch (error) {
    showError(error)
    if (error instanceof ApiError && error.status === 404) notFound.value = true
    await load()
  } finally {
    busy.value = false
  }
}

function join() {
  return act(() => joinEvent(eventId.value), 'Вы записаны')
}

function leave() {
  return act(() => leaveEvent(eventId.value), 'Вы отказались от участия')
}

function onSaved(updated: EventItem, changed: boolean) {
  event.value = updated
  if (changed) toast.add({ severity: 'success', summary: 'Мероприятие сохранено', life: 3000 })
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
    toast.add({ severity: 'success', summary: 'Мероприятие удалено', life: 3000 })
    await router.push('/')
  } catch (error) {
    showError(error)
    await load()
  } finally {
    busy.value = false
  }
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
  <main class="app-page">
    <section class="app-card app-card--wide event-page">
      <div v-if="notFound" class="event-page__status" data-testid="event-not-found">
        <h1 class="app-title">Мероприятие не найдено</h1>
        <p class="app-subtitle">Возможно, его удалили или ссылка неверная.</p>
        <RouterLink to="/" class="event-page__back">К мероприятиям</RouterLink>
      </div>

      <div v-else-if="loadError" class="event-page__status" data-testid="event-load-error">
        <p>Не удалось загрузить мероприятие</p>
        <Button type="button" label="Повторить" icon="pi pi-refresh" outlined @click="load" />
      </div>

      <template v-else-if="event">
        <EventDetails
          :event="event"
          :can-manage="canManage"
          :is-past="isPast"
          @saved="onSaved"
          @delete="confirmDelete"
        >
          <template #participation="{ editing }">
            <div v-if="!isPast" class="event-page__participation" data-testid="participation">
              <span v-if="isOrganizer" class="event-page__mark" data-testid="organizer-mark">
                Вы организатор
              </span>
              <Button
                v-else-if="event.is_joined"
                type="button"
                label="Отказаться"
                icon="pi pi-times"
                severity="secondary"
                outlined
                :loading="busy"
                :disabled="busy || editing"
                data-testid="leave"
                @click="leave"
              />
              <template v-else>
                <Button
                  type="button"
                  label="Записаться"
                  icon="pi pi-check"
                  :loading="busy"
                  :disabled="busy || editing || joinBlockedReason !== null"
                  data-testid="join"
                  @click="join"
                />
                <span
                  v-if="joinBlockedReason"
                  class="event-page__reason"
                  data-testid="join-blocked"
                >
                  {{ joinBlockedReason }}
                </span>
              </template>
            </div>
          </template>
        </EventDetails>

        <EventParticipants
          class="event-page__participants"
          :participants="participants"
          :organizer-id="event.organizer.id"
          :visible="canSeeParticipants"
          :can-remove="canManage"
          @remove="confirmRemoveParticipant"
        />
      </template>

      <div v-else class="event-page__status" data-testid="event-loading">
        <ProgressSpinner style="width: 40px; height: 40px" stroke-width="4" aria-label="Загрузка" />
      </div>
    </section>
  </main>
</template>

<style scoped>
.event-page {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.event-page__status {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  text-align: center;
}

.event-page__back {
  display: inline-flex;
  align-items: center;
  min-height: var(--app-touch-target);
  color: var(--p-primary-700);
  font-weight: 500;
}

.event-page__participation {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
  min-height: var(--app-touch-target);
}

.event-page__participation :deep(.p-button) {
  width: 100%;
}

@media (min-width: 640px) {
  .event-page__participation :deep(.p-button) {
    width: auto;
  }
}

.event-page__reason {
  color: var(--app-text-muted);
}

/* Оранжевый — только акцент */
.event-page__mark {
  display: inline-flex;
  align-items: center;
  min-height: 32px;
  padding: 0 12px;
  border-radius: 16px;
  background: var(--app-accent-soft);
  color: var(--app-accent-text);
  border: 1px solid var(--app-accent-border);
  font-weight: 500;
}

.event-page__participants {
  border-top: 1px solid var(--app-border);
  padding-top: 20px;
}
</style>
