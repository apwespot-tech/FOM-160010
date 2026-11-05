import { computed, inject, provide, reactive, ref, type InjectionKey } from 'vue'

import { ApiError } from '@/api/client'
import { MAX_PHOTO_BYTES, PHOTO_TYPES } from '@/api/events'
import {
  ABOUT_MAX_LENGTH,
  deleteProfileImage,
  updateProfile,
  uploadProfileImage,
  type Profile,
  type ProfileImageKind,
  type ProfilePatch,
} from '@/api/profile'
import { useSessionStore } from '@/stores/session'
import { fromIsoDate, MIN_BIRTH_DATE, startOfToday, toIsoDate } from '@/utils/dates'
import { PHOTO_BAD_TYPE, PHOTO_TOO_LARGE, photoErrorMessage } from '@/utils/photos'

export type ProfileField = 'name' | 'birthDate' | 'email' | 'telegram' | 'about' | 'cityId'

const FIELDS: ProfileField[] = ['name', 'birthDate', 'email', 'telegram', 'about', 'cityId']
const TELEGRAM_RE = /^@[A-Za-z0-9_]{5,32}$/
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
const SERVER_FIELDS: Record<string, ProfileField> = {
  name: 'name',
  birth_date: 'birthDate',
  email: 'email',
  telegram: 'telegram',
  about: 'about',
  city_id: 'cityId',
}
const SAVE_FAILED = 'Не удалось сохранить профиль. Попробуйте ещё раз'
const IMAGE_KINDS: ProfileImageKind[] = ['avatar', 'cover']

/** Черновик аватара или обложки: без изменений, новый файл или удаление. */
export type ImageDraft =
  { state: 'keep' } | { state: 'new'; file: File; previewUrl: string } | { state: 'remove' }

/**
 * Состояние и логика формы профиля: валидация как на сервере, отправка только
 * изменённых полей, затем — если изменились — аватара и обложки, раскладка
 * серверных ошибок по полям. Используется онбордингом и страницей профиля.
 */
export function useProfileForm(getInitial: () => Profile) {
  const session = useSessionStore()
  const maxDate = startOfToday()

  const form = reactive({
    name: '',
    birthDate: null as Date | null,
    email: '',
    telegram: '',
    about: '',
    cityId: null as number | null,
    interestIds: [] as number[],
  })
  const images = reactive<Record<ProfileImageKind, ImageDraft>>({
    avatar: { state: 'keep' },
    cover: { state: 'keep' },
  })
  const imageErrors = reactive<Partial<Record<ProfileImageKind, string>>>({})
  const touched = reactive<Partial<Record<ProfileField, boolean>>>({})
  const serverErrors = reactive<Partial<Record<ProfileField, string>>>({})
  const generalError = ref<string | null>(null)
  const saving = ref(false)
  const submitted = ref(false)

  function releasePreview(kind: ProfileImageKind): void {
    const draft = images[kind]
    if (draft.state === 'new') URL.revokeObjectURL(draft.previewUrl)
  }

  /** Заполнить форму значениями профиля и сбросить ошибки и выбранные файлы. */
  function reset(profile: Profile = getInitial()): void {
    form.name = profile.name ?? ''
    form.birthDate = profile.birth_date ? fromIsoDate(profile.birth_date) : null
    form.email = profile.email ?? ''
    form.telegram = profile.telegram ?? ''
    form.about = profile.about ?? ''
    form.cityId = profile.city?.id ?? null
    form.interestIds = (profile.interests ?? []).map((interest) => interest.id)
    for (const kind of IMAGE_KINDS) {
      releasePreview(kind)
      images[kind] = { state: 'keep' }
      delete imageErrors[kind]
    }
    for (const field of FIELDS) {
      delete touched[field]
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
      case 'about':
        return form.about.trim().length > ABOUT_MAX_LENGTH
          ? `Не больше ${ABOUT_MAX_LENGTH} символов`
          : null
      case 'cityId':
        return null
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

  function toggleInterest(categoryId: number): void {
    form.interestIds = form.interestIds.includes(categoryId)
      ? form.interestIds.filter((id) => id !== categoryId)
      : [...form.interestIds, categoryId]
  }

  /** Выбрать файл аватара или обложки; неподходящий не принимается, ошибка — у поля. */
  function selectImage(kind: ProfileImageKind, file: File): void {
    delete imageErrors[kind]
    if (!PHOTO_TYPES.includes(file.type)) {
      imageErrors[kind] = PHOTO_BAD_TYPE
      return
    }
    if (file.size > MAX_PHOTO_BYTES) {
      imageErrors[kind] = PHOTO_TOO_LARGE
      return
    }
    releasePreview(kind)
    images[kind] = { state: 'new', file, previewUrl: URL.createObjectURL(file) }
  }

  function removeImage(kind: ProfileImageKind): void {
    delete imageErrors[kind]
    releasePreview(kind)
    const saved = kind === 'avatar' ? getInitial().avatar_id : getInitial().cover_id
    images[kind] = saved ? { state: 'remove' } : { state: 'keep' }
  }

  /** Только изменённые поля; пустое необязательное поле — null, интересы — набор целиком. */
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

    const about = form.about.trim() || null
    if (about !== (initial.about ?? null)) patch.about = about

    if (form.cityId !== (initial.city?.id ?? null)) patch.city_id = form.cityId

    const before = (initial.interests ?? []).map((interest) => interest.id).sort((a, b) => a - b)
    const after = [...form.interestIds].sort((a, b) => a - b)
    if (before.join(',') !== after.join(',')) patch.interest_ids = after

    return patch
  }

  function applyServerError(error: ApiError): void {
    if (error.status === 409 && error.code === 'email_taken') {
      serverErrors.email = 'Этот email уже используется'
    } else if (error.code === 'invalid_birth_date') {
      serverErrors.birthDate = 'Некорректная дата рождения'
    } else if (error.code === 'city_not_found') {
      serverErrors.cityId = 'Город не найден'
    } else if (error.status === 422 && error.fields.some((field) => field in SERVER_FIELDS)) {
      for (const field of error.fields) {
        const formField = SERVER_FIELDS[field]
        if (formField) serverErrors[formField] = 'Некорректное значение'
      }
    } else {
      generalError.value = SAVE_FAILED
    }
  }

  /** Отправляет изменённые картинки; при ошибке — сообщение у поля этой картинки. */
  async function saveImages(): Promise<Profile | null> {
    let latest: Profile | null = null
    for (const kind of IMAGE_KINDS) {
      const draft = images[kind]
      if (draft.state === 'keep') continue
      try {
        latest =
          draft.state === 'new'
            ? await uploadProfileImage(kind, draft.file)
            : await deleteProfileImage(kind)
        session.setProfile(latest)
        releasePreview(kind)
        images[kind] = { state: 'keep' }
      } catch (error) {
        imageErrors[kind] = photoErrorMessage(error)
        return null
      }
    }
    return latest
  }

  /**
   * Проверяет и сохраняет форму: сначала поля, потом картинки. Возвращает актуальный
   * профиль (без запросов, если ничего не изменилось) или null, если сохранить не удалось.
   * Если поля сохранились, а картинка нет, повторный вызов отправит только картинки.
   */
  async function submit(): Promise<Profile | null> {
    submitted.value = true
    generalError.value = null
    if (!requiredFilled.value || FIELDS.some((field) => validate(field) !== null)) return null

    const patch = buildPatch()
    const imagesChanged = IMAGE_KINDS.some((kind) => images[kind].state !== 'keep')
    if (Object.keys(patch).length === 0 && !imagesChanged) return getInitial()

    saving.value = true
    try {
      let profile = getInitial()
      if (Object.keys(patch).length > 0) {
        try {
          profile = await updateProfile(patch)
          session.setProfile(profile)
        } catch (error) {
          if (error instanceof ApiError) applyServerError(error)
          else generalError.value = SAVE_FAILED
          return null
        }
      }
      if (!imagesChanged) return profile
      return await saveImages()
    } finally {
      saving.value = false
    }
  }

  reset()

  return {
    form,
    images,
    imageErrors,
    serverErrors,
    generalError,
    saving,
    requiredFilled,
    errorFor,
    touch,
    toggleInterest,
    selectImage,
    removeImage,
    reset,
    submit,
  }
}

export type ProfileFormController = ReturnType<typeof useProfileForm>

const KEY: InjectionKey<ProfileFormController> = Symbol('profile-form')

/** Делит форму профиля между страницей (кнопки в шапке) и полями формы. */
export function provideProfileForm(controller: ProfileFormController): void {
  provide(KEY, controller)
}

export function injectProfileForm(): ProfileFormController {
  const controller = inject(KEY)
  if (!controller) throw new Error('ProfileEditForm используется вне страницы профиля')
  return controller
}
