<script setup lang="ts">
/** Поле картинки профиля в форме: превью, «Загрузить/Заменить», «Удалить», ошибка у поля. */
import Button from 'primevue/button'
import { computed, ref } from 'vue'

import { PHOTO_TYPES } from '@/api/events'
import type { ProfileImageKind } from '@/api/profile'
import { loadUserImageUrl, useImageUrl } from '@/composables/usePhotoUrl'
import type { ImageDraft } from '@/composables/useProfileForm'

const props = defineProps<{
  kind: ProfileImageKind
  label: string
  userId: string
  /** Сохранённая картинка */
  savedId: string | null
  draft: ImageDraft
  error: string | undefined
  disabled: boolean
}>()
const emit = defineEmits<{ select: [file: File]; remove: [] }>()

const input = ref<HTMLInputElement | null>(null)
const accept = PHOTO_TYPES.join(',')

const { url: savedUrl } = useImageUrl(
  () => {
    const id = props.savedId
    return id ? () => loadUserImageUrl(props.userId, id, 'thumb') : null
  },
  () => (props.savedId ? `form:${props.savedId}` : null),
)

const preview = computed(() => {
  if (props.draft.state === 'new') return props.draft.previewUrl
  if (props.draft.state === 'remove') return null
  return savedUrl.value
})
const hasImage = computed(
  () => props.draft.state === 'new' || (props.draft.state === 'keep' && props.savedId !== null),
)

function onChange(event: Event): void {
  const target = event.target as HTMLInputElement
  const file = target.files?.[0]
  if (file) emit('select', file)
  // Тот же файл можно выбрать снова
  target.value = ''
}
</script>

<template>
  <div class="image-field" :data-testid="`image-field-${kind}`">
    <span class="image-field__label">{{ label }}</span>
    <div class="image-field__row">
      <span class="image-field__preview" :class="`image-field__preview--${kind}`">
        <img v-if="preview" :src="preview" alt="" :data-testid="`image-preview-${kind}`" />
        <i v-else class="pi pi-image" aria-hidden="true" />
      </span>
      <div class="image-field__actions">
        <Button
          type="button"
          :label="hasImage ? 'Заменить' : 'Загрузить'"
          icon="pi pi-upload"
          outlined
          :disabled="disabled"
          :data-testid="`image-pick-${kind}`"
          @click="input?.click()"
        />
        <Button
          v-if="hasImage"
          type="button"
          label="Удалить"
          icon="pi pi-trash"
          severity="danger"
          text
          :disabled="disabled"
          :data-testid="`image-remove-${kind}`"
          @click="emit('remove')"
        />
        <input
          ref="input"
          type="file"
          :accept="accept"
          class="image-field__input"
          tabindex="-1"
          aria-hidden="true"
          :data-testid="`image-input-${kind}`"
          @change="onChange"
        />
      </div>
    </div>
    <small class="image-field__hint">JPEG, PNG или WebP до 2 МБ</small>
    <small v-if="error" class="app-field-error" :data-testid="`error-image-${kind}`">
      {{ error }}
    </small>
  </div>
</template>

<style scoped>
.image-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.image-field__label {
  font-weight: 500;
}

.image-field__row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
}

.image-field__preview {
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  background: var(--p-surface-100);
  color: var(--app-text-muted);
  font-size: 1.5rem;
}

.image-field__preview--avatar {
  width: 72px;
  height: 72px;
  border-radius: 16px;
}

.image-field__preview--cover {
  width: 192px;
  max-width: 100%;
  aspect-ratio: 4 / 1;
  border-radius: 10px;
}

.image-field__preview img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.image-field__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.image-field__hint {
  color: var(--app-text-muted);
}

.image-field__input {
  display: none;
}
</style>
