<script setup lang="ts">
/**
 * Окно «Новое мероприятие» по стандарту модальных окон (docs/rules.md):
 * на мобильной ширине — во весь экран, клик по фону закрывает только пустую форму,
 * кнопки в футере, основная справа. После создания — переход на страницу мероприятия.
 */
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import { watch } from 'vue'
import { useRouter } from 'vue-router'

import EventFormFields from '@/components/EventFormFields.vue'
import { provideEventForm } from '@/composables/eventFormContext'
import { useCreateEventDialog } from '@/composables/useCreateEventDialog'
import { useEventForm } from '@/composables/useEventForm'
import { useIsMobile } from '@/utils/breakpoints'

const router = useRouter()
const isMobile = useIsMobile()
const { visible, close } = useCreateEventDialog()

const controller = useEventForm({ getInitial: () => null })
provideEventForm(controller)
const { saving, requiredFilled, dirty, reset, submit } = controller

// Каждое открытие — с чистой формой
watch(visible, (open) => {
  if (open) reset()
})

async function onSubmit() {
  const event = await submit()
  if (!event) return
  close()
  await router.push(`/events/${event.id}`)
}
</script>

<template>
  <Dialog
    :visible="visible"
    modal
    header="Новое мероприятие"
    :dismissable-mask="!dirty"
    :draggable="false"
    :class="['create-event', { 'create-event--fullscreen': isMobile }]"
    data-testid="create-event-dialog"
    @update:visible="!$event && close()"
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
          @click="close"
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
