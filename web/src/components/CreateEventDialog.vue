<script setup lang="ts">
/**
 * Окно «Новое мероприятие» по стандарту модальных окон (docs/rules.md):
 * на мобильной ширине — во весь экран, клик по фону закрывает только пустую форму,
 * кнопки в футере, основная справа. После создания — переход на страницу мероприятия.
 * Если мероприятие создано, а фото не сохранились, окно остаётся открытым: повтор
 * «Создать» отправляет только фото, а закрытие открывает созданное мероприятие.
 */
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import { watch } from 'vue'
import { useRouter } from 'vue-router'

import EventFormFields from '@/components/EventFormFields.vue'
import { provideEventForm } from '@/composables/eventFormContext'
import { useCreateEventDialog } from '@/composables/useCreateEventDialog'
import { useEventForm } from '@/composables/useEventForm'
import { useSessionStore } from '@/stores/session'
import { useIsMobile } from '@/utils/breakpoints'

const router = useRouter()
const isMobile = useIsMobile()
const { visible, close, notifyCreated } = useCreateEventDialog()

const session = useSessionStore()
// Город нового мероприятия по умолчанию — из профиля
const controller = useEventForm({
  getInitial: () => null,
  defaultCityId: () => session.profile?.city?.id ?? null,
})
provideEventForm(controller)
const { saving, requiredFilled, dirty, created, reset, submit, releasePhotos } = controller

// Каждое открытие — с чистой формой; при закрытии освобождаются превью фото
watch(visible, (open) => {
  if (open) reset()
  else releasePhotos()
})

async function onSubmit() {
  const wasCreated = created.value !== null
  const event = await submit()
  // Мероприятие только что создано (даже если фото не сохранились) — показать его в списке
  // (`created` заполнен только при частичном сохранении, при полном успехе приходит `event`)
  if (!wasCreated && (event || created.value)) notifyCreated()
  if (!event) return
  close()
  await router.push(`/events/${event.id}`)
}

/** Закрытие без сохранения; если мероприятие уже создано — открыть его. */
async function dismiss() {
  const event = created.value
  close()
  if (event) await router.push(`/events/${event.id}`)
}
</script>

<template>
  <Dialog
    :visible="visible"
    modal
    header="Новое мероприятие"
    :dismissable-mask="!dirty && !created"
    :draggable="false"
    :class="['create-event', { 'create-event--fullscreen': isMobile }]"
    data-testid="create-event-dialog"
    @update:visible="!$event && dismiss()"
  >
    <form
      id="create-event-form"
      novalidate
      data-testid="create-event-form"
      @submit.prevent="onSubmit"
    >
      <EventFormFields id-prefix="new-event" />
    </form>

    <template #footer>
      <div class="app-actions app-actions--inline create-event__actions">
        <Button
          type="submit"
          form="create-event-form"
          label="Создать"
          icon="pi pi-check"
          :loading="saving"
          :disabled="!requiredFilled || saving"
          data-testid="create-event-submit"
        />
        <Button
          type="button"
          label="Отмена"
          severity="secondary"
          outlined
          data-testid="create-event-cancel"
          @click="dismiss"
        />
      </div>
    </template>
  </Dialog>
</template>

<style>
/* Dialog рендерится в body (teleport), поэтому стили не scoped */
.create-event.p-dialog {
  width: min(640px, calc(100vw - 32px));
  max-height: calc(100dvh - 32px);
}

.create-event--fullscreen.p-dialog {
  width: 100vw;
  height: 100dvh;
  max-height: 100dvh;
  margin: 0;
  border-radius: 0;
}

.create-event__actions {
  width: 100%;
}
</style>
