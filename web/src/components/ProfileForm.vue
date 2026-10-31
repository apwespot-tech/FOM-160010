<script setup lang="ts">
/** Форма заполнения профиля (онбординг). Редактирование профиля — в ProfileCard. */
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import Message from 'primevue/message'

import type { Profile } from '@/api/profile'
import BirthDateInput from '@/components/BirthDateInput.vue'
import { useProfileForm } from '@/composables/useProfileForm'

const props = defineProps<{
  /** Текущий профиль: база для отправки только изменённых полей */
  initial: Profile
}>()
const emit = defineEmits<{ saved: [profile: Profile] }>()

const { form, serverErrors, generalError, saving, requiredFilled, errorFor, touch, submit } =
  useProfileForm(() => props.initial)

async function onSubmit() {
  const profile = await submit()
  if (profile) emit('saved', profile)
}

function onBirthDate(value: Date | null) {
  form.birthDate = value
  touch('birthDate')
}
</script>

<template>
  <form class="app-form" novalidate data-testid="profile-form" @submit.prevent="onSubmit">
    <div class="app-field">
      <label for="profile-name">Имя *</label>
      <InputText
        id="profile-name"
        v-model="form.name"
        autocomplete="name"
        maxlength="100"
        :invalid="errorFor('name') !== null"
        data-testid="field-name"
        @blur="touch('name')"
      />
      <small v-if="errorFor('name')" class="app-field-error" data-testid="error-name">
        {{ errorFor('name') }}
      </small>
    </div>

    <div class="app-field">
      <label for="profile-birth-date">Дата рождения *</label>
      <BirthDateInput
        :model-value="form.birthDate"
        input-id="profile-birth-date"
        :invalid="errorFor('birthDate') !== null"
        @update:model-value="onBirthDate"
      />
      <small v-if="errorFor('birthDate')" class="app-field-error" data-testid="error-birth-date">
        {{ errorFor('birthDate') }}
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
        :invalid="errorFor('email') !== null"
        data-testid="field-email"
        @blur="touch('email')"
        @input="delete serverErrors.email"
      />
      <small v-if="errorFor('email')" class="app-field-error" data-testid="error-email">
        {{ errorFor('email') }}
      </small>
    </div>

    <div class="app-field">
      <label for="profile-telegram">Telegram</label>
      <InputText
        id="profile-telegram"
        v-model="form.telegram"
        placeholder="@username"
        autocapitalize="off"
        :invalid="errorFor('telegram') !== null"
        data-testid="field-telegram"
        @blur="touch('telegram')"
      />
      <small v-if="errorFor('telegram')" class="app-field-error" data-testid="error-telegram">
        {{ errorFor('telegram') }}
      </small>
    </div>

    <Message v-if="generalError" severity="error" :closable="false">{{ generalError }}</Message>

    <div class="app-actions">
      <Button
        type="submit"
        label="Сохранить"
        :loading="saving"
        :disabled="!requiredFilled || saving"
        data-testid="profile-submit"
      />
    </div>
  </form>
</template>
