<script setup lang="ts">
/**
 * Карточка профиля: просмотр и редактирование в одной раскладке
 * (стандарт «Окна и карточки с данными», docs/rules.md). По «Редактировать»
 * значения заменяются полями на своих местах; телефон, аватар и возраст остаются текстом.
 */
import Avatar from 'primevue/avatar'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import Message from 'primevue/message'
import { nextTick, ref } from 'vue'

import type { Profile } from '@/api/profile'
import BirthDateInput from '@/components/BirthDateInput.vue'
import { useProfileForm } from '@/composables/useProfileForm'
import { formatRuDate } from '@/utils/dates'
import { formatAge, formatPhone, initials } from '@/utils/format'

const props = defineProps<{ profile: Profile }>()
const emit = defineEmits<{ saved: [profile: Profile, changed: boolean] }>()

const NOT_SET = 'не указано'

const editing = ref(false)
const nameInput = ref<{ $el: HTMLInputElement } | null>(null)
const { form, serverErrors, generalError, saving, requiredFilled, errorFor, touch, reset, submit } =
  useProfileForm(() => props.profile)

async function startEdit() {
  reset(props.profile)
  editing.value = true
  await nextTick()
  nameInput.value?.$el.focus()
}

function cancel() {
  reset(props.profile)
  editing.value = false
}

async function save() {
  if (!editing.value) return
  const before = props.profile
  const profile = await submit()
  if (!profile) return
  editing.value = false
  emit('saved', profile, profile !== before)
}

function onBirthDate(value: Date | null) {
  form.birthDate = value
  touch('birthDate')
}
</script>

<template>
  <form
    class="profile-card"
    :class="{ 'profile-card--editing': editing }"
    novalidate
    data-testid="profile-card"
    @submit.prevent="save"
  >
    <div class="profile-card__head">
      <Avatar
        v-if="profile.photo_url"
        :image="profile.photo_url"
        shape="circle"
        size="xlarge"
        data-testid="profile-avatar-image"
      />
      <Avatar
        v-else
        :label="initials(profile.name)"
        shape="circle"
        size="xlarge"
        class="profile-card__avatar--initials"
        data-testid="profile-avatar-initials"
      />

      <div class="profile-card__title">
        <template v-if="editing">
          <InputText
            id="profile-name"
            ref="nameInput"
            v-model="form.name"
            aria-label="Имя"
            placeholder="Имя"
            autocomplete="name"
            maxlength="100"
            class="profile-card__name-input"
            :invalid="errorFor('name') !== null"
            data-testid="field-name"
            @blur="touch('name')"
          />
          <small v-if="errorFor('name')" class="app-field-error" data-testid="error-name">
            {{ errorFor('name') }}
          </small>
        </template>
        <h1 v-else class="app-title app-break" data-testid="profile-name">{{ profile.name }}</h1>
        <p v-if="profile.age !== null" class="profile-card__age" data-testid="profile-age">
          {{ formatAge(profile.age) }}
        </p>
      </div>
    </div>

    <dl class="profile-card__rows">
      <div class="profile-card__row">
        <dt><label for="profile-birth-date">Дата рождения</label></dt>
        <dd v-if="editing">
          <BirthDateInput
            :model-value="form.birthDate"
            input-id="profile-birth-date"
            :invalid="errorFor('birthDate') !== null"
            @update:model-value="onBirthDate"
          />
          <small
            v-if="errorFor('birthDate')"
            class="app-field-error"
            data-testid="error-birth-date"
          >
            {{ errorFor('birthDate') }}
          </small>
        </dd>
        <dd
          v-else
          :class="{ 'profile-card__empty': !profile.birth_date }"
          data-testid="profile-birth-date"
        >
          {{ profile.birth_date ? formatRuDate(profile.birth_date) : NOT_SET }}
        </dd>
      </div>

      <div class="profile-card__row">
        <dt>Телефон</dt>
        <!-- Телефон — логин; в своём профиле не редактируется и остаётся текстом -->
        <dd class="app-break" data-testid="profile-phone">{{ formatPhone(profile.phone) }}</dd>
      </div>

      <div class="profile-card__row">
        <dt><label for="profile-email">Email</label></dt>
        <dd v-if="editing">
          <InputText
            id="profile-email"
            v-model="form.email"
            type="email"
            inputmode="email"
            autocomplete="email"
            placeholder="name@example.com"
            :invalid="errorFor('email') !== null"
            data-testid="field-email"
            @blur="touch('email')"
            @input="delete serverErrors.email"
          />
          <small v-if="errorFor('email')" class="app-field-error" data-testid="error-email">
            {{ errorFor('email') }}
          </small>
        </dd>
        <dd
          v-else
          class="app-break"
          :class="{ 'profile-card__empty': !profile.email }"
          data-testid="profile-email"
        >
          {{ profile.email ?? NOT_SET }}
        </dd>
      </div>

      <div class="profile-card__row">
        <dt><label for="profile-telegram">Telegram</label></dt>
        <dd v-if="editing">
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
        </dd>
        <dd
          v-else
          class="app-break"
          :class="{ 'profile-card__empty': !profile.telegram }"
          data-testid="profile-telegram"
        >
          {{ profile.telegram ?? NOT_SET }}
        </dd>
      </div>
    </dl>

    <Message
      v-if="editing && generalError"
      severity="error"
      :closable="false"
      class="profile-card__wide"
    >
      {{ generalError }}
    </Message>

    <!-- «Редактировать» и «Сохранить»/«Отмена» — на одном и том же месте -->
    <div
      class="app-actions app-actions--inline profile-card__wide profile-card__actions"
      data-testid="profile-actions"
    >
      <template v-if="editing">
        <Button
          type="submit"
          label="Сохранить"
          icon="pi pi-check"
          :loading="saving"
          :disabled="!requiredFilled || saving"
          data-testid="profile-submit"
        />
        <Button
          type="button"
          label="Отмена"
          severity="secondary"
          outlined
          data-testid="profile-cancel"
          @click="cancel"
        />
      </template>
      <Button
        v-else
        type="button"
        label="Редактировать"
        icon="pi pi-pencil"
        data-testid="profile-edit"
        @click="startEdit"
      />
    </div>
  </form>
</template>

<style scoped>
.profile-card {
  display: grid;
  gap: 24px;
}

.profile-card__head {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  gap: 12px;
}

.profile-card__title {
  width: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}

/* Место под имя той же высоты, что и поле ввода имени */
.profile-card__title > h1,
.profile-card__name-input {
  min-height: var(--app-touch-target);
  margin: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* Поле имени занимает место заголовка; та же высота, что у остальных полей */
.profile-card__name-input {
  width: 100%;
  font-weight: 600;
  text-align: center;
}

.profile-card__avatar--initials {
  background: var(--p-primary-100);
  color: var(--p-primary-800);
  font-weight: 600;
}

.profile-card__age {
  margin: 0;
  color: var(--app-text-muted);
}

.profile-card__rows {
  margin: 0;
  display: grid;
  gap: 14px;
}

.profile-card__row {
  display: grid;
  gap: 2px;
}

.profile-card__row dt {
  color: var(--app-text-muted);
  font-size: 0.875rem;
}

/*
 * Высота ячейки значения = высоте поля ввода (44 px) и в режиме просмотра,
 * чтобы при переключении в редактирование размер карточки не менялся.
 */
.profile-card__row dd {
  margin: 0;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 4px;
  min-width: 0;
  min-height: var(--app-touch-target);
}

/* В режиме редактирования поля во всю ширину ячейки значения */
.profile-card__row dd :deep(.p-inputtext),
.profile-card__row dd :deep(.p-datepicker) {
  width: 100%;
}

.profile-card__empty {
  color: var(--app-text-muted);
  font-style: italic;
}

/*
 * На мобильной ширине пара «Сохранить»/«Отмена» — в одну строку по половине ширины,
 * чтобы высота карточки не менялась относительно одной кнопки «Редактировать».
 */
@media (max-width: 639px) {
  .profile-card__actions {
    flex-direction: row-reverse;
  }

  .profile-card__actions :deep(.p-button) {
    flex: 1 1 0;
    min-width: 0;
  }
}

/* Компьютер: аватар слева, данные справа; действия — на всю ширину */
@media (min-width: 1024px) {
  .profile-card {
    grid-template-columns: 180px 1fr;
    align-items: start;
    gap: 24px 32px;
  }

  .profile-card__wide {
    grid-column: 1 / -1;
  }

  .profile-card__row {
    grid-template-columns: 140px 1fr;
    align-items: center;
    gap: 12px;
  }
}
</style>
