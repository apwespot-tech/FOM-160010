<script setup lang="ts">
/**
 * Окно «Новое мероприятие» по стандарту модальных окон (docs/rules.md):
 * на мобильной ширине — во весь экран, клик по фону закрывает только пустую форму,
 * кнопки в футере, основная справа. После создания — переход на страницу мероприятия.
 */
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import Message from 'primevue/message'
import { watch } from 'vue'
import { useRouter } from 'vue-router'

import EventFieldInput from '@/components/EventFieldInput.vue'
import { provideEventForm } from '@/composables/eventFormContext'
import { useCreateEventDialog } from '@/composables/useCreateEventDialog'
import { useEventForm } from '@/composables/useEventForm'
import { useIsMobile } from '@/utils/breakpoints'

const router = useRouter()
const isMobile = useIsMobile()
const { visible, close } = useCreateEventDialog()

const controller = useEventForm({ getInitial: () => null })
provideEventForm(controller)
const { generalError, saving, requiredFilled, dirty, reset, submit } = controller

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
      class="create-event__form"
      novalidate
      data-testid="create-event-form"
      @submit.prevent="onSubmit"
    >
      <div class="app-field create-event__wide">
        <label for="new-event-title">Название *</label>
        <EventFieldInput field="title" input-id="new-event-title" />
      </div>
      <div class="app-field">
        <label for="new-event-category">Категория *</label>
        <EventFieldInput field="categoryId" input-id="new-event-category" />
      </div>
      <div class="app-field">
        <label for="new-event-starts-at">Дата и время *</label>
        <EventFieldInput field="startsAt" input-id="new-event-starts-at" />
      </div>
      <div class="app-field">
        <label for="new-event-duration">Длительность</label>
        <EventFieldInput field="durationMinutes" input-id="new-event-duration" />
      </div>
      <div class="app-field">
        <label for="new-event-max">Максимум участников *</label>
        <EventFieldInput field="maxParticipants" input-id="new-event-max" />
      </div>
      <div class="app-field create-event__wide">
        <label for="new-event-place">Место *</label>
        <EventFieldInput field="place" input-id="new-event-place" />
      </div>
      <div class="app-field create-event__wide">
        <span id="new-event-age-label" class="create-event__label">Возраст</span>
        <EventFieldInput field="minAge" input-id="new-event-age" aria-label="Возраст" />
      </div>
      <div class="app-field create-event__wide">
        <label for="new-event-description">Описание *</label>
        <EventFieldInput field="description" input-id="new-event-description" />
      </div>
      <Message
        v-if="generalError"
        severity="error"
        :closable="false"
        class="create-event__wide"
        data-testid="create-event-error"
      >
        {{ generalError }}
      </Message>
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

.create-event__form {
  display: grid;
  gap: 16px;
}

.create-event__label {
  font-weight: 500;
}

.create-event__actions {
  width: 100%;
}

@media (min-width: 640px) {
  .create-event__form {
    grid-template-columns: 1fr 1fr;
  }

  .create-event__wide {
    grid-column: 1 / -1;
  }
}
</style>
