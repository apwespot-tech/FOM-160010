import { computed, reactive, ref } from 'vue'

import { ApiError } from '@/api/client'
import { updateProfile, type Profile, type ProfilePatch } from '@/api/profile'
import { useSessionStore } from '@/stores/session'
import { fromIsoDate, MIN_BIRTH_DATE, startOfToday, toIsoDate } from '@/utils/dates'

export type ProfileField = 'name' | 'birthDate' | 'email' | 'telegram'

const FIELDS: ProfileField[] = ['name', 'birthDate', 'email', 'telegram']
const TELEGRAM_RE = /^@[A-Za-z0-9_]{5,32}$/
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
const SERVER_FIELDS: Record<string, ProfileField> = {
  name: 'name',
  birth_date: 'birthDate',
  email: 'email',
  telegram: 'telegram',
}
const SAVE_FAILED = 'Не удалось сохранить профиль. Попробуйте ещё раз'

/**
 * Состояние и логика формы профиля: валидация как на сервере, отправка только
 * изменённых полей, раскладка серверных ошибок по полям.
 * Используется формой онбординга и карточкой профиля в режиме редактирования.
 */
export function useProfileForm(getInitial: () => Profile) {
  const session = useSessionStore()
  const maxDate = startOfToday()

  const form = reactive({
    name: '',
    birthDate: null as Date | null,
    email: '',
    telegram: '',
  })
  const touched = reactive<Record<ProfileField, boolean>>({
    name: false,
    birthDate: false,
    email: false,
    telegram: false,
  })
  const serverErrors = reactive<Partial<Record<ProfileField, string>>>({})
  const generalError = ref<string | null>(null)
  const saving = ref(false)
  const submitted = ref(false)

  /** Заполнить форму значениями профиля и сбросить ошибки. */
  function reset(profile: Profile = getInitial()): void {
    form.name = profile.name ?? ''
    form.birthDate = profile.birth_date ? fromIsoDate(profile.birth_date) : null
    form.email = profile.email ?? ''
    form.telegram = profile.telegram ?? ''
    for (const field of FIELDS) {
      touched[field] = false
      delete serverErrors[field]
    }
    generalError.value = null
    submitted.value = false
  }

  function validate(field: ProfileField): string | null {
    switch (field) {
      case 'name': {
        const name = form.name.trim()
        if (!name) return 'Укажите имя'
        if (name.length > 100) return 'Не больше 100 символов'
        return null
      }
      case 'birthDate':
        if (!form.birthDate) return 'Укажите дату рождения'
        if (form.birthDate > maxDate) return 'Дата рождения не может быть в будущем'
        if (form.birthDate < MIN_BIRTH_DATE) return 'Дата рождения не раньше 01.01.1900'
        return null
      case 'email':
        return form.email.trim() && !EMAIL_RE.test(form.email.trim()) ? 'Некорректный email' : null
      case 'telegram':
        return form.telegram.trim() && !TELEGRAM_RE.test(form.telegram.trim())
          ? 'Формат: @username, 5–32 символа: латиница, цифры, _'
          : null
    }
  }

  function errorFor(field: ProfileField): string | null {
    if (serverErrors[field]) return serverErrors[field] ?? null
    return touched[field] || submitted.value ? validate(field) : null
  }

  const requiredFilled = computed(() => form.name.trim().length > 0 && form.birthDate !== null)

  function touch(field: ProfileField): void {
    touched[field] = true
    delete serverErrors[field]
  }

  /** Только изменённые поля; пустое необязательное поле — null. */
  function buildPatch(): ProfilePatch {
    const initial = getInitial()
    const patch: ProfilePatch = {}
    const name = form.name.trim()
    if (name !== (initial.name ?? '')) patch.name = name

    const birthDate = form.birthDate ? toIsoDate(form.birthDate) : null
    if (birthDate && birthDate !== initial.birth_date) patch.birth_date = birthDate

    const email = form.email.trim() || null
    if (email !== initial.email) patch.email = email

    const telegram = form.telegram.trim() || null
    if (telegram !== initial.telegram) patch.telegram = telegram

    return patch
  }

  function applyServerError(error: ApiError): void {
    if (error.status === 409 && error.code === 'email_taken') {
      serverErrors.email = 'Этот email уже используется'
    } else if (error.code === 'invalid_birth_date') {
      serverErrors.birthDate = 'Некорректная дата рождения'
    } else if (error.status === 422 && error.fields.some((field) => field in SERVER_FIELDS)) {
      for (const field of error.fields) {
        const formField = SERVER_FIELDS[field]
        if (formField) serverErrors[formField] = 'Некорректное значение'
      }
    } else {
      generalError.value = SAVE_FAILED
    }
  }

  /**
   * Проверяет и сохраняет форму. Возвращает актуальный профиль (без запроса,
   * если ничего не изменилось) или null, если сохранить не удалось.
   */
  async function submit(): Promise<Profile | null> {
    submitted.value = true
    generalError.value = null
    if (!requiredFilled.value || FIELDS.some((field) => validate(field) !== null)) return null

    const patch = buildPatch()
    if (Object.keys(patch).length === 0) return getInitial()

    saving.value = true
    try {
      const profile = await updateProfile(patch)
      session.setProfile(profile)
      return profile
    } catch (error) {
      if (error instanceof ApiError) applyServerError(error)
      else generalError.value = SAVE_FAILED
      return null
    } finally {
      saving.value = false
    }
  }

  reset()

  return {
    form,
    serverErrors,
    generalError,
    saving,
    requiredFilled,
    errorFor,
    touch,
    reset,
    submit,
  }
}
