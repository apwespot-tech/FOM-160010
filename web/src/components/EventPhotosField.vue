<script setup lang="ts">
/**
 * Блок фото в форме мероприятия: плитки по порядку, первое — основное.
 * Все действия — кнопками (без перетаскивания), изменения уходят на сервер
 * только по «Создать»/«Сохранить».
 */
import Button from 'primevue/button'
import Message from 'primevue/message'
import { computed, ref } from 'vue'

import { MAX_PHOTOS, PHOTO_TYPES } from '@/api/events'
import EventPhotoImage from '@/components/EventPhotoImage.vue'
import { injectEventForm } from '@/composables/eventFormContext'
import { PHOTO_LIMIT } from '@/utils/photos'

const props = defineProps<{ inputId: string }>()

const {
  photos,
  photoEventId,
  rejectedPhotos,
  photoNotice,
  photoError,
  photoErrorKey,
  saving,
  addPhotos,
  removePhoto,
  movePhoto,
  makeMainPhoto,
} = injectEventForm()

const input = ref<HTMLInputElement | null>(null)
const full = computed(() => photos.value.length >= MAX_PHOTOS)
const accept = PHOTO_TYPES.join(',')

function pick(): void {
  input.value?.click()
}

function onChange(event: Event): void {
  const target = event.target as HTMLInputElement
  addPhotos([...(target.files ?? [])])
  // Тот же файл можно выбрать снова после удаления
  target.value = ''
}
</script>

<template>
  <div class="photos-field" data-testid="photos-field">
    <ul v-if="photos.length" class="photos-field__grid" aria-label="Выбранные фото">
      <li
        v-for="(photo, index) in photos"
        :key="photo.key"
        class="photos-field__tile"
        :class="{ 'photos-field__tile--error': photo.key === photoErrorKey }"
        data-testid="photo-tile"
      >
        <div class="photos-field__preview">
          <img
            v-if="photo.kind === 'new'"
            :src="photo.previewUrl"
            :alt="`Новое фото ${index + 1}`"
            class="photos-field__img"
          />
          <EventPhotoImage
            v-else-if="photoEventId"
            :event-id="photoEventId"
            :photo-id="photo.id"
            :alt="`Фото ${index + 1}`"
          />
          <span v-if="index === 0" class="photos-field__main" data-testid="photo-main-mark">
            Основное
          </span>
          <Button
            type="button"
            icon="pi pi-trash"
            rounded
            severity="secondary"
            class="photos-field__remove"
            :disabled="saving"
            :aria-label="`Удалить фото ${index + 1}`"
            data-testid="photo-remove"
            @click="removePhoto(photo.key)"
          />
        </div>
        <div class="photos-field__actions">
          <Button
            type="button"
            icon="pi pi-chevron-left"
            text
            rounded
            severity="secondary"
            :disabled="index === 0 || saving"
            :aria-label="`Сдвинуть фото ${index + 1} влево`"
            data-testid="photo-left"
            @click="movePhoto(photo.key, -1)"
          />
          <Button
            v-if="index > 0"
            type="button"
            icon="pi pi-star"
            text
            rounded
            severity="secondary"
            :disabled="saving"
            :aria-label="`Сделать фото ${index + 1} основным`"
            data-testid="photo-make-main"
            @click="makeMainPhoto(photo.key)"
          />
          <Button
            type="button"
            icon="pi pi-chevron-right"
            text
            rounded
            severity="secondary"
            :disabled="index === photos.length - 1 || saving"
            :aria-label="`Сдвинуть фото ${index + 1} вправо`"
            data-testid="photo-right"
            @click="movePhoto(photo.key, 1)"
          />
        </div>
      </li>
    </ul>

    <div class="photos-field__add">
      <Button
        type="button"
        label="Добавить фото"
        icon="pi pi-images"
        outlined
        :disabled="full || saving"
        data-testid="photo-add"
        @click="pick"
      />
      <span v-if="full" class="photos-field__hint" data-testid="photo-limit">{{
        PHOTO_LIMIT
      }}</span>
      <span v-else class="photos-field__hint"
        >JPEG, PNG или WebP до 2 МБ, до {{ MAX_PHOTOS }} шт.</span
      >
      <input
        :id="props.inputId"
        ref="input"
        type="file"
        multiple
        :accept="accept"
        class="photos-field__input"
        tabindex="-1"
        aria-hidden="true"
        data-testid="photo-input"
        @change="onChange"
      />
    </div>

    <ul
      v-if="rejectedPhotos.length || photoNotice"
      class="photos-field__rejected"
      data-testid="photo-rejected"
    >
      <li v-for="file in rejectedPhotos" :key="file.name">
        <span class="app-break">«{{ file.name }}»</span> — {{ file.reason }}
      </li>
      <li v-if="photoNotice">{{ photoNotice }}</li>
    </ul>

    <Message v-if="photoError" severity="error" :closable="false" data-testid="photo-error">
      {{ photoError }}
    </Message>
  </div>
</template>

<style scoped>
.photos-field {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-width: 0;
}

.photos-field__grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  margin: 0;
  padding: 0;
  list-style: none;
}

@media (min-width: 640px) {
  .photos-field__grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

.photos-field__tile {
  display: flex;
  flex-direction: column;
  border: 1px solid var(--app-border);
  border-radius: 12px;
  overflow: hidden;
  background: var(--p-surface-0);
}

.photos-field__tile--error {
  border-color: var(--p-red-500);
  box-shadow: 0 0 0 1px var(--p-red-500);
}

/* Пропорция 4:3 не зависит от снимка: картинка лежит поверх, обрезаясь по краям */
.photos-field__preview {
  position: relative;
  aspect-ratio: 4 / 3;
  overflow: hidden;
  background: var(--p-surface-100);
}

.photos-field__preview > .photos-field__img,
.photos-field__preview > .event-photo {
  position: absolute;
  inset: 0;
}

.photos-field__img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.photos-field__remove.p-button {
  position: absolute;
  top: 4px;
  right: 4px;
  width: 44px;
  height: 44px;
  background: rgb(255 255 255 / 0.9);
  border: 1px solid var(--app-border);
  color: var(--p-red-600);
}

.photos-field__main {
  position: absolute;
  top: 6px;
  left: 6px;
  padding: 2px 8px;
  border-radius: 999px;
  background: var(--p-primary-color);
  color: var(--p-primary-contrast-color);
  font-size: 0.75rem;
  font-weight: 600;
}

/* Три кнопки по 44 px помещаются в строку даже на плитке шириной 150 px */
.photos-field__actions {
  display: flex;
  justify-content: space-between;
  padding: 2px;
}

.photos-field__actions .p-button {
  width: 44px;
  height: 44px;
}

.photos-field__add {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px 12px;
}

.photos-field__hint {
  color: var(--app-text-muted);
  font-size: 0.875rem;
}

.photos-field__input {
  display: none;
}

.photos-field__rejected {
  margin: 0;
  padding-left: 18px;
  color: var(--p-red-600);
  font-size: 0.875rem;
}
</style>
