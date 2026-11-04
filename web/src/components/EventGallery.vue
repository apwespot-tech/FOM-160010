<script setup lang="ts">
/**
 * Галерея в окне мероприятия: основное фото 16:9, под ним миниатюры остальных.
 * Нажатие открывает полноэкранный просмотр с листанием; Esc закрывает только просмотр.
 */
import Button from 'primevue/button'
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'

import type { PhotoRef } from '@/api/events'
import EventPhotoImage from '@/components/EventPhotoImage.vue'

const props = defineProps<{ eventId: string; photos: PhotoRef[]; title: string }>()

const main = computed(() => props.photos[0] ?? null)
const rest = computed(() => props.photos.slice(1))
const viewerIndex = ref<number | null>(null)
const viewerPhoto = computed(() =>
  viewerIndex.value === null ? null : (props.photos[viewerIndex.value] ?? null),
)

function alt(index: number): string {
  return `Фото ${index + 1} — ${props.title}`
}

async function open(index: number): Promise<void> {
  viewerIndex.value = index
  await nextTick()
  // Фокус на «Закрыть»: просмотр — отдельный слой поверх окна
  document.querySelector<HTMLElement>('[data-testid="photo-viewer-close"]')?.focus()
}

function close(): void {
  viewerIndex.value = null
}

function step(delta: number): void {
  if (viewerIndex.value === null) return
  const next = viewerIndex.value + delta
  if (next >= 0 && next < props.photos.length) viewerIndex.value = next
}

/**
 * Клавиши просмотра ловим на window в фазе захвата: так Esc не доходит до окна
 * мероприятия (PrimeVue слушает document) и закрывается только просмотр.
 */
function onKeydown(event: KeyboardEvent): void {
  if (viewerIndex.value === null) return
  if (event.key === 'Escape') {
    event.stopImmediatePropagation()
    event.preventDefault()
    close()
  } else if (event.key === 'ArrowLeft') {
    step(-1)
  } else if (event.key === 'ArrowRight') {
    step(1)
  }
}

watch(viewerIndex, (index, previous) => {
  if (index !== null && previous === null) window.addEventListener('keydown', onKeydown, true)
  if (index === null && previous !== null) window.removeEventListener('keydown', onKeydown, true)
})

// Набор фото сменился (сохранение) — просмотр не должен указывать за пределы
watch(
  () => props.photos.length,
  (length) => {
    if (viewerIndex.value !== null && viewerIndex.value >= length) close()
  },
)

onBeforeUnmount(() => window.removeEventListener('keydown', onKeydown, true))
</script>

<template>
  <section
    v-if="main"
    class="event-gallery"
    aria-label="Фото мероприятия"
    data-testid="event-gallery"
  >
    <button
      type="button"
      class="event-gallery__main"
      :aria-label="`Открыть фото 1 из ${photos.length}`"
      data-testid="gallery-main"
      @click="open(0)"
    >
      <EventPhotoImage :event-id="eventId" :photo-id="main.id" :alt="alt(0)" />
    </button>

    <div v-if="rest.length" class="event-gallery__thumbs" data-testid="gallery-thumbs">
      <button
        v-for="(photo, index) in rest"
        :key="photo.id"
        type="button"
        class="event-gallery__thumb"
        :aria-label="`Открыть фото ${index + 2} из ${photos.length}`"
        data-testid="gallery-thumb"
        @click="open(index + 1)"
      >
        <EventPhotoImage :event-id="eventId" :photo-id="photo.id" :alt="alt(index + 1)" />
      </button>
    </div>

    <Teleport to="body">
      <div
        v-if="viewerPhoto && viewerIndex !== null"
        class="photo-viewer"
        role="dialog"
        aria-modal="true"
        aria-label="Просмотр фото"
        data-testid="photo-viewer"
        @click.self="close"
      >
        <div class="photo-viewer__bar">
          <span class="photo-viewer__counter" data-testid="photo-viewer-counter">
            {{ viewerIndex + 1 }} из {{ photos.length }}
          </span>
          <Button
            type="button"
            icon="pi pi-times"
            text
            rounded
            aria-label="Закрыть просмотр"
            class="photo-viewer__button"
            data-testid="photo-viewer-close"
            @click="close"
          />
        </div>

        <div class="photo-viewer__stage" @click.self="close">
          <EventPhotoImage
            :key="viewerPhoto.id"
            :event-id="eventId"
            :photo-id="viewerPhoto.id"
            :alt="alt(viewerIndex)"
            fit="contain"
          />
        </div>

        <Button
          v-if="viewerIndex > 0"
          type="button"
          icon="pi pi-chevron-left"
          text
          rounded
          aria-label="Предыдущее фото"
          class="photo-viewer__button photo-viewer__nav photo-viewer__nav--prev"
          data-testid="photo-viewer-prev"
          @click="step(-1)"
        />
        <Button
          v-if="viewerIndex < photos.length - 1"
          type="button"
          icon="pi pi-chevron-right"
          text
          rounded
          aria-label="Следующее фото"
          class="photo-viewer__button photo-viewer__nav photo-viewer__nav--next"
          data-testid="photo-viewer-next"
          @click="step(1)"
        />
      </div>
    </Teleport>
  </section>
</template>

<style scoped>
.event-gallery {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-width: 0;
}

.event-gallery__main,
.event-gallery__thumb {
  display: block;
  padding: 0;
  border: 0;
  border-radius: 12px;
  overflow: hidden;
  cursor: zoom-in;
  background: none;
}

.event-gallery__main {
  position: relative;
  width: 100%;
  aspect-ratio: 16 / 9;
}

/* Пропорция не зависит от снимка: портретное фото обрезается, а не растягивает блок */
.event-gallery__main > .event-photo {
  position: absolute;
  inset: 0;
}

.event-gallery__main:focus-visible,
.event-gallery__thumb:focus-visible {
  outline: 2px solid var(--p-primary-color);
  outline-offset: 2px;
}

/* Миниатюры — одна строка с прокруткой внутри блока, окно не прокручивается вбок */
.event-gallery__thumbs {
  display: flex;
  gap: 8px;
  overflow-x: auto;
  overscroll-behavior-x: contain;
  scrollbar-width: thin;
  padding-bottom: 2px;
}

.event-gallery__thumb {
  flex: 0 0 auto;
  width: 72px;
  height: 54px;
  border-radius: 8px;
}

@media (min-width: 640px) {
  .event-gallery__thumb {
    width: 96px;
    height: 72px;
  }
}

.photo-viewer {
  position: fixed;
  inset: 0;
  z-index: 5000;
  display: flex;
  flex-direction: column;
  background: rgb(0 0 0 / 0.92);
}

.photo-viewer__bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 8px 8px 16px;
  color: #fff;
}

.photo-viewer__counter {
  font-weight: 600;
}

.photo-viewer__stage {
  flex: 1;
  min-height: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0 16px 16px;
}

.photo-viewer__button.p-button {
  width: 44px;
  height: 44px;
  color: #fff;
}

.photo-viewer__nav.p-button {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  background: rgb(0 0 0 / 0.4);
}

.photo-viewer__nav--prev.p-button {
  left: 8px;
}

.photo-viewer__nav--next.p-button {
  right: 8px;
}
</style>
