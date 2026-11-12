<script setup lang="ts">
/**
 * Редактирование своего профиля: страница перестраивается в форму с подписями
 * (стандарт «Окна и карточки с данными»). Логика — useProfileForm, кнопки — в шапке профиля.
 */
import InputText from 'primevue/inputtext'
import Message from 'primevue/message'
import Select from 'primevue/select'
import Textarea from 'primevue/textarea'
import { computed } from 'vue'

import { ABOUT_MAX_LENGTH, type Profile } from '@/api/profile'
import BirthDateInput from '@/components/BirthDateInput.vue'
import ProfileImageField from '@/components/ProfileImageField.vue'
import { useCategories } from '@/composables/useCategories'
import { useCities } from '@/composables/useCities'
import { injectProfileForm } from '@/composables/useProfileForm'
import { categoryIcon } from '@/utils/categories'
import { formatPhone } from '@/utils/format'

defineProps<{ profile: Profile }>()
const emit = defineEmits<{ submit: [] }>()

const controller = injectProfileForm()
const { form, serverErrors } = controller
const { categories } = useCategories()
const { cities } = useCities()

const aboutLength = computed(() => form.about.trim().length)

function onBirthDate(value: Date | null) {
  form.birthDate = value
  controller.touch('birthDate')
}

function onCity(value: unknown) {
  form.cityId = typeof value === 'number' ? value : null
}

function clearEmailError() {
  delete serverErrors.email
}
</script>

<template>
  <form
    id="profile-edit-form"
    class="profile-edit"
    novalidate
    data-testid="profile-card"
    @submit.prevent="emit('submit')"
  >
    <div class="profile-edit__images">
      <ProfileImageField
        kind="avatar"
        label="Аватар"
        :user-id="profile.id"
        :saved-id="profile.avatar_id"
        :draft="controller.images.avatar"
        :error="controller.imageErrors.avatar"
        :disabled="controller.saving.value"
        @select="controller.selectImage('avatar', $event)"
        @remove="controller.removeImage('avatar')"
      />
      <ProfileImageField
        kind="cover"
        label="Обложка"
        :user-id="profile.id"
        :saved-id="profile.cover_id"
        :draft="controller.images.cover"
        :error="controller.imageErrors.cover"
        :disabled="controller.saving.value"
        @select="controller.selectImage('cover', $event)"
        @remove="controller.removeImage('cover')"
      />
    </div>

    <div class="profile-edit__grid">
      <div class="app-field">
        <label for="profile-name">Имя *</label>
        <InputText
          id="profile-name"
          v-model="form.name"
          autocomplete="name"
          maxlength="100"
          :invalid="controller.errorFor('name') !== null"
          data-testid="field-name"
          @blur="controller.touch('name')"
        />
        <small v-if="controller.errorFor('name')" class="app-field-error" data-testid="error-name">
          {{ controller.errorFor('name') }}
        </small>
      </div>

      <div class="app-field">
        <label for="profile-birth-date">Дата рождения *</label>
        <BirthDateInput
          :model-value="form.birthDate"
          input-id="profile-birth-date"
          :invalid="controller.errorFor('birthDate') !== null"
          @update:model-value="onBirthDate"
          @blur="controller.touch('birthDate')"
        />
        <small
          v-if="controller.errorFor('birthDate')"
          class="app-field-error"
          data-testid="error-birth-date"
        >
          {{ controller.errorFor('birthDate') }}
        </small>
      </div>

      <div class="app-field">
        <label for="profile-email">Email</label>
        <InputText
          id="profile-email"
          v-model="form.email"
          type="email"
          inputmode="email"
          autocomplete="email"
          placeholder="name@example.com"
          :invalid="controller.errorFor('email') !== null"
          data-testid="field-email"
          @blur="controller.touch('email')"
          @input="clearEmailError"
        />
        <small
          v-if="controller.errorFor('email')"
          class="app-field-error"
          data-testid="error-email"
        >
          {{ controller.errorFor('email') }}
        </small>
      </div>

      <div class="app-field">
        <label for="profile-telegram">Telegram</label>
        <InputText
          id="profile-telegram"
          v-model="form.telegram"
          placeholder="@username"
          autocapitalize="off"
          :invalid="controller.errorFor('telegram') !== null"
          data-testid="field-telegram"
          @blur="controller.touch('telegram')"
        />
        <small
          v-if="controller.errorFor('telegram')"
          class="app-field-error"
          data-testid="error-telegram"
        >
          {{ controller.errorFor('telegram') }}
        </small>
      </div>

      <div class="app-field">
        <label for="profile-city">Город</label>
        <Select
          input-id="profile-city"
          :model-value="form.cityId"
          :options="cities"
          option-label="name"
          option-value="id"
          placeholder="Не указан"
          filter
          filter-placeholder="Найти город"
          show-clear
          :invalid="controller.errorFor('cityId') !== null"
          data-testid="field-city"
          @update:model-value="onCity"
        />
        <small
          v-if="controller.errorFor('cityId')"
          class="app-field-error"
          data-testid="error-city"
        >
          {{ controller.errorFor('cityId') }}
        </small>
      </div>

      <div class="app-field">
        <span class="profile-edit__label">Телефон</span>
        <!-- Телефон — логин; в своём профиле не редактируется -->
        <span class="profile-edit__static" data-testid="profile-phone">
          {{ formatPhone(profile.phone) }}
        </span>
      </div>

      <div class="app-field profile-edit__wide">
        <label for="profile-about">О себе</label>
        <Textarea
          id="profile-about"
          v-model="form.about"
          rows="4"
          auto-resize
          :invalid="controller.errorFor('about') !== null"
          data-testid="field-about"
          @blur="controller.touch('about')"
        />
        <div class="profile-edit__about-meta">
          <small
            v-if="controller.errorFor('about')"
            class="app-field-error"
            data-testid="error-about"
          >
            {{ controller.errorFor('about') }}
          </small>
          <small
            class="profile-edit__counter"
            :class="{ 'profile-edit__counter--over': aboutLength > ABOUT_MAX_LENGTH }"
            data-testid="about-counter"
          >
            {{ aboutLength }} / {{ ABOUT_MAX_LENGTH }}
          </small>
        </div>
      </div>

      <fieldset class="app-field profile-edit__wide profile-edit__interests">
        <legend class="profile-edit__label">Интересы</legend>
        <div class="profile-edit__chips">
          <button
            v-for="category in categories"
            :key="category.id"
            type="button"
            class="profile-edit__chip"
            :class="{ 'profile-edit__chip--on': form.interestIds.includes(category.id) }"
            :aria-pressed="form.interestIds.includes(category.id)"
            :data-testid="`interest-${category.id}`"
            @click="controller.toggleInterest(category.id)"
          >
            <i :class="['pi', categoryIcon(category.icon)]" aria-hidden="true" />
            {{ category.name }}
          </button>
        </div>
      </fieldset>
    </div>

    <Message v-if="controller.generalError.value" severity="error" :closable="false">
      {{ controller.generalError.value }}
    </Message>
  </form>
</template>

<style scoped>
.profile-edit {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.profile-edit__images {
  display: grid;
  gap: 16px;
}

.profile-edit__grid {
  display: grid;
  gap: 16px;
}

@media (min-width: 640px) {
  .profile-edit__images,
  .profile-edit__grid {
    grid-template-columns: 1fr 1fr;
  }

  .profile-edit__wide {
    grid-column: 1 / -1;
  }
}

.profile-edit__grid :deep(.p-inputtext),
.profile-edit__grid :deep(.p-select),
.profile-edit__grid :deep(.p-datepicker),
.profile-edit__grid :deep(.p-textarea) {
  width: 100%;
}

.profile-edit__label {
  font-weight: 500;
}

.profile-edit__static {
  display: flex;
  align-items: center;
  min-height: var(--app-touch-target);
  color: var(--app-text-muted);
}

.profile-edit__about-meta {
  display: flex;
  justify-content: space-between;
  gap: 8px;
}

.profile-edit__counter {
  margin-left: auto;
  color: var(--app-text-muted);
}

.profile-edit__counter--over {
  color: var(--p-red-600);
}

.profile-edit__interests {
  margin: 0;
  padding: 0;
  border: 0;
}

.profile-edit__chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 6px;
}

.profile-edit__chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-height: var(--app-touch-target);
  padding: 0 14px;
  border: 1px solid var(--app-border);
  border-radius: 10px;
  background: var(--p-surface-0);
  color: var(--p-text-color);
  font: inherit;
  font-weight: 500;
  cursor: pointer;
}

.profile-edit__chip:focus-visible {
  outline: 2px solid var(--p-primary-600);
  outline-offset: 2px;
}

.profile-edit__chip--on {
  background: var(--p-primary-50);
  border-color: var(--p-primary-300);
  color: var(--p-primary-700);
}
</style>
