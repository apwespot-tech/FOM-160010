<script setup lang="ts">
/**
 * Профиль пользователя (/users/:id) — одна страница для своего и чужого профиля.
 * Чужой профиль виден участникам общих мероприятий (проверяет сервер), без доступа —
 * «Профиль недоступен». На своём профиле «Редактировать» перестраивает страницу в форму.
 */
import Button from 'primevue/button'
import ProgressSpinner from 'primevue/progressspinner'
import { useToast } from 'primevue/usetoast'
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { ApiError } from '@/api/client'
import { getUserProfile, type Profile } from '@/api/profile'
import CategoryTag from '@/components/CategoryTag.vue'
import PersonAvatar from '@/components/PersonAvatar.vue'
import ProfileEditForm from '@/components/ProfileEditForm.vue'
import { loadUserImageUrl, useImageUrl } from '@/composables/usePhotoUrl'
import { provideProfileForm, useProfileForm } from '@/composables/useProfileForm'
import { useSessionStore } from '@/stores/session'
import { formatMemberSince, formatRuDate } from '@/utils/dates'
import { formatAge, formatPhone } from '@/utils/format'
import { shareLink } from '@/utils/share'

const NOT_SET = 'не указано'

const route = useRoute()
const router = useRouter()
const session = useSessionStore()
const toast = useToast()

const userId = computed(() => String(route.params.id))
const isOwn = computed(() => userId.value === session.profile?.id)

const other = ref<Profile | null>(null)
const unavailable = ref(false)
const loadError = ref(false)
const editing = ref(false)

/** Свой профиль — из сессии (обновляется после сохранения), чужой — отдельным запросом. */
const profile = computed<Profile | null>(() => (isOwn.value ? session.profile : other.value))

async function load(): Promise<void> {
  unavailable.value = false
  loadError.value = false
  editing.value = false
  if (isOwn.value) {
    // Актуальные данные (возраст, счётчики, правки администратора)
    await session.loadProfile().catch(() => undefined)
    return
  }
  other.value = null
  try {
    other.value = await getUserProfile(userId.value)
  } catch (error) {
    if (error instanceof ApiError && (error.status === 403 || error.status === 404)) {
      unavailable.value = true
    } else {
      loadError.value = true
    }
  }
}

watch(userId, () => void load(), { immediate: true })

const { url: coverUrl } = useImageUrl(
  () => {
    const current = profile.value
    const cover = current?.cover_id
    return current && cover ? () => loadUserImageUrl(current.id, cover, 'full') : null
  },
  () => (profile.value?.cover_id ? `cover:${profile.value.cover_id}` : null),
)

// Форма — только для своего профиля; база для «только изменённых полей» — профиль в сессии
const controller = useProfileForm(() => session.profile as Profile)
provideProfileForm(controller)

function startEdit(): void {
  if (!session.profile) return
  controller.reset(session.profile)
  editing.value = true
}

function cancelEdit(): void {
  if (session.profile) controller.reset(session.profile)
  editing.value = false
}

async function save(): Promise<void> {
  const before = session.profile
  const saved = await controller.submit()
  if (!saved) return
  editing.value = false
  if (saved !== before) toast.add({ severity: 'success', summary: 'Профиль сохранён', life: 3000 })
}

async function share(): Promise<void> {
  const url = new URL(router.resolve(`/users/${userId.value}`).href, window.location.origin).href
  const result = await shareLink(url, profile.value?.name ?? 'Профиль')
  if (result === 'copied') {
    toast.add({ severity: 'success', summary: 'Ссылка скопирована', life: 3000 })
  } else if (result === 'manual') {
    toast.add({ severity: 'info', summary: 'Ссылка на профиль', detail: url, life: 8000 })
  }
}
</script>

<template>
  <main class="app-page profile-page">
    <div class="profile-page__inner">
      <section
        v-if="unavailable"
        class="profile-page__status app-card"
        data-testid="profile-unavailable"
      >
        <i class="pi pi-lock profile-page__status-icon" aria-hidden="true" />
        <h1 class="app-title">Профиль недоступен</h1>
        <p class="app-subtitle">Профиль видят участники общих мероприятий</p>
        <Button type="button" label="К мероприятиям" outlined @click="router.push('/')" />
      </section>

      <section v-else-if="loadError" class="profile-page__status app-card">
        <p>Не удалось загрузить профиль</p>
        <Button type="button" label="Повторить" icon="pi pi-refresh" outlined @click="load" />
      </section>

      <template v-else-if="profile">
        <section
          class="profile-hero"
          :class="{ 'profile-hero--editing': editing }"
          data-testid="profile-view"
        >
          <!-- В режиме редактирования обложка — поле формы, полосу не показываем -->
          <div v-if="!editing" class="profile-hero__cover" data-testid="profile-cover">
            <img
              v-if="coverUrl && !editing"
              :src="coverUrl"
              alt=""
              data-testid="profile-cover-image"
            />
          </div>

          <div class="profile-hero__head">
            <div v-if="!editing" class="profile-hero__avatar" data-testid="profile-avatar">
              <PersonAvatar
                :name="profile.name"
                :user-id="profile.id"
                :avatar-id="profile.avatar_id"
                size="xlarge"
                shape="rounded"
              />
            </div>

            <div class="profile-hero__title">
              <h1 v-if="editing" class="profile-hero__name" data-testid="profile-edit-title">
                Редактирование профиля
              </h1>
              <template v-else>
                <h1 class="profile-hero__name app-break" data-testid="profile-name">
                  {{ profile.name }}
                </h1>
                <span
                  class="profile-hero__telegram app-break"
                  :class="{ 'profile-hero__empty': !profile.telegram }"
                  data-testid="profile-telegram"
                >
                  {{ profile.telegram ?? NOT_SET }}
                </span>
              </template>
            </div>

            <!-- «Редактировать» и «Сохранить»/«Отмена» — на одном и том же месте -->
            <div class="profile-hero__actions" data-testid="profile-actions">
              <template v-if="editing">
                <Button
                  type="button"
                  label="Отмена"
                  severity="secondary"
                  outlined
                  data-testid="profile-cancel"
                  @click="cancelEdit"
                />
                <Button
                  type="submit"
                  form="profile-edit-form"
                  label="Сохранить"
                  icon="pi pi-check"
                  :loading="controller.saving.value"
                  :disabled="!controller.requiredFilled.value || controller.saving.value"
                  data-testid="profile-submit"
                />
              </template>
              <template v-else>
                <Button
                  type="button"
                  label="Поделиться"
                  icon="pi pi-share-alt"
                  severity="secondary"
                  outlined
                  data-testid="profile-share"
                  @click="share"
                />
                <Button
                  v-if="isOwn"
                  type="button"
                  label="Редактировать"
                  icon="pi pi-user-edit"
                  data-testid="profile-edit"
                  @click="startEdit"
                />
              </template>
            </div>
          </div>

          <div v-if="editing" class="profile-hero__body">
            <ProfileEditForm :profile="profile" @submit="save" />
          </div>

          <div v-else class="profile-hero__body profile-hero__body--view">
            <div class="profile-hero__about">
              <p v-if="profile.about" class="profile-hero__about-text" data-testid="profile-about">
                {{ profile.about }}
              </p>
              <div
                v-if="profile.interests.length"
                class="profile-hero__interests"
                data-testid="profile-interests"
              >
                <CategoryTag
                  v-for="interest in profile.interests"
                  :key="interest.id"
                  :category="interest"
                  variant="soft"
                />
              </div>
            </div>

            <dl class="profile-hero__facts">
              <div class="profile-hero__fact">
                <dt><i class="pi pi-map-marker" aria-hidden="true" /><span>Город</span></dt>
                <dd :class="{ 'profile-hero__empty': !profile.city }" data-testid="profile-city">
                  {{ profile.city?.name ?? NOT_SET }}
                </dd>
              </div>
              <div class="profile-hero__fact">
                <!-- Значение уже начинается с «На сайте с …» — подпись только для экранных чтецов -->
                <dt>
                  <i class="pi pi-calendar" aria-hidden="true" />
                  <span class="profile-hero__sr">Дата регистрации</span>
                </dt>
                <dd data-testid="profile-since">{{ formatMemberSince(profile.created_at) }}</dd>
              </div>
              <div class="profile-hero__fact">
                <dt><i class="pi pi-gift" aria-hidden="true" /><span>Дата рождения</span></dt>
                <dd>
                  <span
                    :class="{ 'profile-hero__empty': !profile.birth_date }"
                    data-testid="profile-birth-date"
                  >
                    {{ profile.birth_date ? formatRuDate(profile.birth_date) : NOT_SET }}
                  </span>
                  <span
                    v-if="profile.age !== null"
                    class="profile-hero__age"
                    data-testid="profile-age"
                  >
                    {{ formatAge(profile.age) }}
                  </span>
                </dd>
              </div>
              <div class="profile-hero__fact">
                <dt><i class="pi pi-phone" aria-hidden="true" /><span>Телефон</span></dt>
                <dd class="app-break" data-testid="profile-phone">
                  {{ formatPhone(profile.phone) }}
                </dd>
              </div>
              <div class="profile-hero__fact">
                <dt><i class="pi pi-envelope" aria-hidden="true" /><span>Email</span></dt>
                <dd
                  class="app-break"
                  :class="{ 'profile-hero__empty': !profile.email }"
                  data-testid="profile-email"
                >
                  {{ profile.email ?? NOT_SET }}
                </dd>
              </div>
            </dl>
          </div>
        </section>

        <section v-if="!editing" class="profile-stats" aria-label="Активность">
          <div class="profile-stats__tile">
            <span class="profile-stats__icon profile-stats__icon--organized">
              <i class="pi pi-sparkles" aria-hidden="true" />
            </span>
            <div>
              <div class="profile-stats__value" data-testid="stats-organized">
                {{ profile.stats.organized_count }}
              </div>
              <div class="profile-stats__label">Организовано событий</div>
            </div>
          </div>
          <div class="profile-stats__tile">
            <span class="profile-stats__icon profile-stats__icon--attended">
              <i class="pi pi-ticket" aria-hidden="true" />
            </span>
            <div>
              <div class="profile-stats__value" data-testid="stats-attended">
                {{ profile.stats.attended_count }}
              </div>
              <div class="profile-stats__label">Посещено мероприятий</div>
            </div>
          </div>
        </section>
      </template>

      <div v-else class="profile-page__status" data-testid="profile-loading">
        <ProgressSpinner style="width: 40px; height: 40px" stroke-width="4" aria-label="Загрузка" />
      </div>
    </div>
  </main>
</template>

<style scoped>
.profile-page__inner {
  width: 100%;
  max-width: 1200px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.profile-page__status {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 48px 16px;
  text-align: center;
}

.profile-page__status-icon {
  color: var(--app-text-muted);
  font-size: 2rem;
}

.profile-hero {
  overflow: hidden;
  background: var(--p-surface-0);
  border: 1px solid var(--app-border);
  border-radius: 20px;
}

/* Обложка или сплошная полоса основного цвета той же высоты — без градиента */
.profile-hero__cover {
  height: 140px;
  background: var(--p-primary-600);
}

@media (min-width: 640px) {
  .profile-hero__cover {
    height: 220px;
  }
}

.profile-hero__cover img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.profile-hero--editing .profile-hero__head {
  padding-top: 20px;
}

.profile-hero__head {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  gap: 12px 20px;
  padding: 0 20px;
}

.profile-hero__avatar {
  margin-top: -64px;
  padding: 4px;
  border-radius: 24px;
  background: var(--p-surface-0);
  box-shadow: 0 4px 16px rgb(15 23 42 / 0.12);
}

.profile-hero__title {
  flex: 1 1 200px;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding-top: 12px;
}

.profile-hero__name {
  margin: 0;
  font-size: 1.75rem;
  font-weight: 800;
  line-height: 1.2;
}

.profile-hero__telegram {
  color: var(--app-text-muted);
}

.profile-hero__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding-top: 12px;
}

@media (max-width: 639px) {
  .profile-hero__actions {
    width: 100%;
  }

  .profile-hero__actions :deep(.p-button) {
    flex: 1 1 0;
    min-width: 0;
  }
}

.profile-hero__body {
  padding: 20px;
}

.profile-hero__body--view {
  display: grid;
  gap: 20px;
}

@media (min-width: 1024px) {
  .profile-hero__body--view {
    grid-template-columns: minmax(0, 1fr) 320px;
    gap: 32px;
  }

  .profile-hero__facts {
    padding-left: 24px;
    border-left: 1px solid var(--app-border);
  }
}

.profile-hero__about {
  display: flex;
  flex-direction: column;
  gap: 14px;
  min-width: 0;
}

.profile-hero__about-text {
  margin: 0;
  white-space: pre-line;
  overflow-wrap: anywhere;
  line-height: 1.55;
}

.profile-hero__interests {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.profile-hero__facts {
  margin: 0;
  display: grid;
  gap: 12px;
  align-content: start;
}

.profile-hero__fact {
  display: grid;
  gap: 2px;
}

.profile-hero__fact dt {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--app-text-muted);
  font-size: 0.8125rem;
}

.profile-hero__fact dt .pi {
  color: var(--p-primary-600);
}

.profile-hero__fact dd {
  margin: 0;
  display: flex;
  flex-wrap: wrap;
  gap: 4px 8px;
  font-weight: 500;
}

.profile-hero__sr {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip-path: inset(50%);
  white-space: nowrap;
}

.profile-hero__age {
  color: var(--app-text-muted);
  font-weight: 400;
}

.profile-hero__empty {
  color: var(--app-text-muted);
  font-style: italic;
  font-weight: 400;
}

.profile-stats {
  display: grid;
  gap: 16px;
}

@media (min-width: 640px) {
  .profile-stats {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

.profile-stats__tile {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px;
  background: var(--p-surface-0);
  border: 1px solid var(--app-border);
  border-radius: 16px;
}

.profile-stats__icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 48px;
  height: 48px;
  border-radius: 12px;
  font-size: 1.25rem;
}

.profile-stats__icon--organized {
  background: var(--p-primary-50);
  color: var(--p-primary-600);
}

.profile-stats__icon--attended {
  background: var(--app-accent-soft);
  color: var(--app-accent-text);
}

.profile-stats__value {
  font-size: 1.5rem;
  font-weight: 800;
  line-height: 1.2;
}

.profile-stats__label {
  color: var(--app-text-muted);
  font-size: 0.875rem;
}
</style>
