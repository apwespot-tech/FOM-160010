import { computed, reactive, ref } from 'vue'

import { ApiError, NETWORK_ERROR } from '@/api/client'
import {
  createEvent,
  updateEvent,
  type EventCreate,
  type EventItem,
  type EventPatch,
  type MinAge,
} from '@/api/events'
import { toOffsetIso } from '@/utils/dates'

export type EventField =
  | 'title'
  | 'categoryId'
  | 'startsAt'
  | 'durationMinutes'
  | 'place'
  | 'maxParticipants'
  | 'minAge'
  | 'description'

const FIELDS: EventField[] = [
  'title',
  'categoryId',
  'startsAt',
  'durationMinutes',
  'place',
  'maxParticipants',
  'minAge',
  'description',
]
const SERVER_FIELDS: Record<string, EventField> = {
  title: 'title',
  category_id: 'categoryId',
  starts_at: 'startsAt',
  duration_minutes: 'durationMinutes',
  place: 'place',
  max_participants: 'maxParticipants',
  min_age: 'minAge',
  description: 'description',
}

export const DEFAULT_MAX_PARTICIPANTS = 10
export const MAX_PARTICIPANTS = 100
const MIN_PARTICIPANTS = 2
const MAX_DURATION = 1440
const FUTURE_REQUIRED = 'Время начала должно быть в будущем'
const SAVE_FAILED = 'Не удалось сохранить мероприятие. Попробуйте ещё раз'

/** Сообщения по коду ошибки действий с мероприятием (для страницы и формы). */
export function eventErrorMessage(error: unknown, minAge?: number): string {
  if (!(error instanceof ApiError)) return 'Что-то пошло не так. Попробуйте ещё раз'
  switch (error.code) {
    case 'event_full':
      return 'Свободных мест нет'
    case 'age_restricted':
      return minAge ? `Мероприятие доступно с ${minAge} лет` : 'Мероприятие недоступно по возрасту'
    case 'event_started':
      return 'Мероприятие уже началось'
    case 'already_joined':
      return 'Вы уже записаны'
    case 'not_joined':
      return 'Вы не записаны на это мероприятие'
    case 'forbidden':
      return 'Недостаточно прав'
    case NETWORK_ERROR:
      return 'Нет связи с сервером'
  }
  if (error.status === 404) return 'Мероприятие не найдено'
  return 'Что-то пошло не так. Попробуйте ещё раз'
}

export interface EventFormOptions {
  /** Мероприятие для редактирования; null — создание. */
  getInitial: () => EventItem | null
  /** Текущее время (подменяется в тестах). */
  now?: () => Date
}

/**
 * Состояние и логика формы мероприятия: валидация как на сервере, создание или
 * отправка только изменённых полей, раскладка серверных ошибок по полям.
 * Используется окном создания и страницей мероприятия в режиме редактирования.
 */
export function useEventForm({ getInitial, now = () => new Date() }: EventFormOptions) {
  const form = reactive({
    title: '',
    categoryId: null as number | null,
    startsAt: null as Date | null,
    durationMinutes: null as number | null,
    place: '',
    maxParticipants: DEFAULT_MAX_PARTICIPANTS as number | null,
    minAge: 0 as MinAge,
    description: '',
  })
  const touched = reactive<Partial<Record<EventField, boolean>>>({})
  const serverErrors = reactive<Partial<Record<EventField, string>>>({})
  const generalError = ref<string | null>(null)
  const saving = ref(false)
  const submitted = ref(false)

  /** Минимум участников: при редактировании — не меньше уже записавшихся. */
  const minParticipants = computed(() =>
    Math.max(MIN_PARTICIPANTS, getInitial()?.participants_count ?? 0),
  )

  function reset(): void {
    const initial = getInitial()
    form.title = initial?.title ?? ''
    form.categoryId = initial?.category.id ?? null
    form.startsAt = initial ? new Date(initial.starts_at) : null
    form.durationMinutes = initial?.duration_minutes ?? null
    form.place = initial?.place ?? ''
    form.maxParticipants = initial?.max_participants ?? DEFAULT_MAX_PARTICIPANTS
    form.minAge = initial?.min_age ?? 0
    form.description = initial?.description ?? ''
    for (const field of FIELDS) {
      delete touched[field]
      delete serverErrors[field]
    }
    generalError.value = null
    submitted.value = false
  }

  function textError(value: string, max: number, empty: string): string | null {
    const text = value.trim()
    if (!text) return empty
    if (text.length > max) return `Не больше ${max} символов`
    return null
  }

  function validate(field: EventField): string | null {
    switch (field) {
      case 'title':
        return textError(form.title, 100, 'Введите название')
      case 'place':
        return textError(form.place, 200, 'Укажите место')
      case 'description':
        return textError(form.description, 2000, 'Добавьте описание')
      case 'categoryId':
        return form.categoryId === null ? 'Выберите категорию' : null
      case 'startsAt':
        if (!form.startsAt) return 'Укажите дату и время'
        return form.startsAt <= now() ? FUTURE_REQUIRED : null
      case 'durationMinutes': {
        const value = form.durationMinutes
        if (value === null) return null
        return Number.isInteger(value) && value >= 1 && value <= MAX_DURATION
          ? null
          : `От 1 до ${MAX_DURATION} минут`
      }
      case 'maxParticipants': {
        const value = form.maxParticipants
        if (value === null) return 'Укажите число участников'
        const min = minParticipants.value
        if (value < min) {
          return min > MIN_PARTICIPANTS
            ? `Не меньше ${min} — столько уже записано`
            : `Не меньше ${MIN_PARTICIPANTS}`
        }
        return value > MAX_PARTICIPANTS ? `Не больше ${MAX_PARTICIPANTS}` : null
      }
      case 'minAge':
        return null
    }
  }

  function errorFor(field: EventField): string | null {
    if (serverErrors[field]) return serverErrors[field] ?? null
    return touched[field] || submitted.value ? validate(field) : null
  }

  function touch(field: EventField): void {
    touched[field] = true
    delete serverErrors[field]
  }

  const requiredFilled = computed(
    () =>
      form.title.trim().length > 0 &&
      form.categoryId !== null &&
      form.startsAt !== null &&
      form.place.trim().length > 0 &&
      form.maxParticipants !== null &&
      form.description.trim().length > 0,
  )

  function toPayload(): EventCreate {
    return {
      title: form.title.trim(),
      description: form.description.trim(),
      place: form.place.trim(),
      starts_at: toOffsetIso(form.startsAt as Date),
      duration_minutes: form.durationMinutes,
      category_id: form.categoryId as number,
      max_participants: form.maxParticipants as number,
      min_age: form.minAge,
    }
  }

  /** Только изменённые поля относительно мероприятия. */
  function buildPatch(initial: EventItem): EventPatch {
    const payload = toPayload()
    const patch: EventPatch = {}
    if (payload.title !== initial.title) patch.title = payload.title
    if (payload.description !== initial.description) patch.description = payload.description
    if (payload.place !== initial.place) patch.place = payload.place
    if ((form.startsAt as Date).getTime() !== new Date(initial.starts_at).getTime()) {
      patch.starts_at = payload.starts_at
    }
    if (payload.duration_minutes !== initial.duration_minutes) {
      patch.duration_minutes = payload.duration_minutes
    }
    if (payload.category_id !== initial.category.id) patch.category_id = payload.category_id
    if (payload.max_participants !== initial.max_participants) {
      patch.max_participants = payload.max_participants
    }
    if (payload.min_age !== initial.min_age) patch.min_age = payload.min_age
    return patch
  }

  /** Введено ли что-нибудь в окне создания (клик по фону тогда не закрывает окно). */
  const dirty = computed(
    () =>
      form.title.trim() !== '' ||
      form.place.trim() !== '' ||
      form.description.trim() !== '' ||
      form.categoryId !== null ||
      form.startsAt !== null ||
      form.durationMinutes !== null ||
      form.maxParticipants !== DEFAULT_MAX_PARTICIPANTS ||
      form.minAge !== 0,
  )

  function applyServerError(error: unknown): void {
    if (!(error instanceof ApiError)) {
      generalError.value = SAVE_FAILED
      return
    }
    if (error.code === 'starts_at_in_past') serverErrors.startsAt = FUTURE_REQUIRED
    else if (error.code === 'category_not_found') serverErrors.categoryId = 'Категория не найдена'
    else if (error.code === 'limit_below_participants') {
      serverErrors.maxParticipants = 'Лимит меньше числа записавшихся участников'
    } else if (error.status === 422 && error.fields.some((field) => field in SERVER_FIELDS)) {
      for (const field of error.fields) {
        const formField = SERVER_FIELDS[field]
        if (formField) serverErrors[formField] = 'Некорректное значение'
      }
    } else if (error.code === 'event_started' || error.code === 'forbidden') {
      generalError.value = eventErrorMessage(error)
    } else if (error.code === NETWORK_ERROR) {
      generalError.value = 'Нет связи с сервером'
    } else {
      generalError.value = SAVE_FAILED
    }
  }

  /**
   * Проверяет и сохраняет форму. Возвращает созданное или изменённое мероприятие
   * (исходное — без запроса, если ничего не изменилось) или null при ошибке.
   */
  async function submit(): Promise<EventItem | null> {
    submitted.value = true
    generalError.value = null
    if (!requiredFilled.value || FIELDS.some((field) => validate(field) !== null)) return null

    const initial = getInitial()
    const patch = initial ? buildPatch(initial) : null
    if (initial && patch && Object.keys(patch).length === 0) return initial

    saving.value = true
    try {
      return initial && patch
        ? await updateEvent(initial.id, patch)
        : await createEvent(toPayload())
    } catch (error) {
      applyServerError(error)
      return null
    } finally {
      saving.value = false
    }
  }

  reset()

  return {
    form,
    generalError,
    saving,
    requiredFilled,
    minParticipants,
    dirty,
    errorFor,
    touch,
    reset,
    submit,
  }
}
