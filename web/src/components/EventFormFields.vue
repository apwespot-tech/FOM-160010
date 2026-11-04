<script setup lang="ts">
/**
 * Поля мероприятия с подписями — общая форма окна создания и режима редактирования
 * в окне мероприятия. Сама форма (useEventForm) приходит через provide/inject.
 */
import Message from 'primevue/message'

import EventFieldInput from '@/components/EventFieldInput.vue'
import EventPhotosField from '@/components/EventPhotosField.vue'
import { injectEventForm } from '@/composables/eventFormContext'

/** Префикс id полей: окна создания и редактирования могут быть в DOM одновременно */
const props = defineProps<{ idPrefix: string }>()

const { generalError } = injectEventForm()
const id = (name: string) => `${props.idPrefix}-${name}`
</script>

<template>
  <div class="event-form">
    <div class="app-field event-form__wide">
      <label :for="id('title')">Название *</label>
      <EventFieldInput field="title" :input-id="id('title')" />
    </div>
    <div class="app-field">
      <label :for="id('category')">Категория *</label>
      <EventFieldInput field="categoryId" :input-id="id('category')" />
    </div>
    <div class="app-field">
      <label :for="id('starts-at')">Дата и время *</label>
      <EventFieldInput field="startsAt" :input-id="id('starts-at')" />
    </div>
    <div class="app-field">
      <label :for="id('duration')">Длительность</label>
      <EventFieldInput field="durationMinutes" :input-id="id('duration')" />
    </div>
    <div class="app-field">
      <label :for="id('max')">Максимум участников *</label>
      <EventFieldInput field="maxParticipants" :input-id="id('max')" />
    </div>
    <div class="app-field event-form__wide">
      <label :for="id('place')">Место *</label>
      <EventFieldInput field="place" :input-id="id('place')" />
    </div>
    <div class="app-field event-form__wide">
      <span class="event-form__label">Возраст</span>
      <EventFieldInput field="minAge" :input-id="id('age')" aria-label="Возраст" />
    </div>
    <div class="app-field event-form__wide">
      <label :for="id('description')">Описание *</label>
      <EventFieldInput field="description" :input-id="id('description')" />
    </div>
    <div class="app-field event-form__wide">
      <span class="event-form__label">Фото</span>
      <EventPhotosField :input-id="id('photos')" />
    </div>
    <Message
      v-if="generalError"
      severity="error"
      :closable="false"
      class="event-form__wide"
      data-testid="event-form-error"
    >
      {{ generalError }}
    </Message>
  </div>
</template>

<style scoped>
.event-form {
  display: grid;
  gap: 16px;
}

.event-form__label {
  font-weight: 500;
}

@media (min-width: 640px) {
  .event-form {
    grid-template-columns: 1fr 1fr;
  }

  .event-form__wide {
    grid-column: 1 / -1;
  }
}
</style>
