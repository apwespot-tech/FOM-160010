import type { VueWrapper } from '@vue/test-utils'
import DatePicker from 'primevue/datepicker'
import { describe, expect, it } from 'vitest'

import type { Profile, ProfilePatch } from '@/api/profile'
import { startOfToday, toIsoDate } from '@/utils/dates'

import {
  completeProfile,
  draftProfile,
  errorResponse,
  jsonResponse,
  mockApi,
  type MockRequest,
} from './helpers/api'
import { setViewportWidth } from './helpers/media'
import { renderApp, settle, waitForPath, withStoredSession } from './helpers/render'

/** Сессия с профилем; PATCH /profile применяет патч к профилю. */
function profileApi(profile: Profile) {
  const api = mockApi()
  withStoredSession(api, profile)
  let current = { ...profile }
  api.on('PATCH /profile', (request: MockRequest) => {
    const patch = request.body as ProfilePatch
    current = { ...current, ...patch }
    current.profile_completed = current.name !== null && current.birth_date !== null
    return jsonResponse(200, current)
  })
  return api
}

function setBirthDate(wrapper: VueWrapper, date: Date | null) {
  wrapper.getComponent(DatePicker).vm.$emit('update:modelValue', date)
  return settle()
}

/** Отправляет форму онбординга или карточку профиля в режиме редактирования. */
async function submitForm(wrapper: VueWrapper) {
  const form = wrapper.find('[data-testid="profile-form"]').exists()
    ? wrapper.get('[data-testid="profile-form"]')
    : wrapper.get('[data-testid="profile-card"]')
  await form.trigger('submit')
  await settle()
}

const submitDisabled = (wrapper: VueWrapper) =>
  wrapper.get('[data-testid="profile-submit"]').attributes('disabled') !== undefined

describe('Онбординг', () => {
  it('кнопка неактивна, пока не заполнены имя и дата рождения', async () => {
    profileApi(draftProfile)
    const { wrapper } = await renderApp('/onboarding')

    expect(submitDisabled(wrapper)).toBe(true)
    await wrapper.get('[data-testid="field-name"]').setValue('   ')
    expect(submitDisabled(wrapper)).toBe(true)
    await wrapper.get('[data-testid="field-name"]').setValue('Анна')
    expect(submitDisabled(wrapper)).toBe(true)
    await setBirthDate(wrapper, new Date(2000, 0, 15))
    expect(submitDisabled(wrapper)).toBe(false)
  })

  it('сохраняет профиль и открывает страницу профиля', async () => {
    const api = profileApi(draftProfile)
    const { wrapper, router } = await renderApp('/onboarding')

    await wrapper.get('[data-testid="field-name"]').setValue('  Анна  ')
    await setBirthDate(wrapper, new Date(2000, 0, 15))
    await submitForm(wrapper)

    expect(api.calls('PATCH /profile')[0]?.body).toEqual({ name: 'Анна', birth_date: '2000-01-15' })
    await waitForPath(router, '/profile')
  })
})

describe('Проверка полей формы профиля', () => {
  async function filledOnboarding() {
    const api = profileApi(draftProfile)
    const app = await renderApp('/onboarding')
    await app.wrapper.get('[data-testid="field-name"]').setValue('Анна')
    return { api, ...app }
  }

  it('дата рождения сегодня принимается', async () => {
    const { api, wrapper } = await filledOnboarding()
    await setBirthDate(wrapper, startOfToday())
    await submitForm(wrapper)

    expect(api.calls('PATCH /profile')).toHaveLength(1)
  })

  it('дата рождения в будущем не отправляется', async () => {
    const { api, wrapper } = await filledOnboarding()
    const tomorrow = startOfToday()
    tomorrow.setDate(tomorrow.getDate() + 1)

    await setBirthDate(wrapper, tomorrow)
    await submitForm(wrapper)

    expect(wrapper.get('[data-testid="error-birth-date"]').text()).toContain('в будущем')
    expect(api.calls('PATCH /profile')).toHaveLength(0)
  })

  it('дата раньше 01.01.1900 не отправляется', async () => {
    const { api, wrapper } = await filledOnboarding()
    await setBirthDate(wrapper, new Date(1899, 11, 31))
    await submitForm(wrapper)

    expect(wrapper.find('[data-testid="error-birth-date"]').exists()).toBe(true)
    expect(api.calls('PATCH /profile')).toHaveLength(0)
  })

  it('DatePicker ограничен датами 01.01.1900 — сегодня', async () => {
    const { wrapper } = await filledOnboarding()
    const props = wrapper.getComponent(DatePicker).props()

    expect(props.minDate).toEqual(new Date(1900, 0, 1))
    expect(props.maxDate).toEqual(startOfToday())
  })

  it('некорректный Telegram — ошибка поля, без отправки', async () => {
    const { api, wrapper } = await filledOnboarding()
    await setBirthDate(wrapper, new Date(2000, 0, 15))
    await wrapper.get('[data-testid="field-telegram"]').setValue('@abc')
    await submitForm(wrapper)

    expect(wrapper.get('[data-testid="error-telegram"]').text()).toContain('@username')
    expect(api.calls('PATCH /profile')).toHaveLength(0)
  })

  it('занятый email показывается у поля', async () => {
    const { api, wrapper } = await filledOnboarding()
    api.on('PATCH /profile', () => errorResponse(409, 'email_taken'))
    await setBirthDate(wrapper, new Date(2000, 0, 15))
    await wrapper.get('[data-testid="field-email"]').setValue('ann@example.com')
    await submitForm(wrapper)

    expect(wrapper.get('[data-testid="error-email"]').text()).toBe('Этот email уже используется')
  })

  it('ошибка валидации сервера раскладывается по полю', async () => {
    const { api, wrapper } = await filledOnboarding()
    api.on('PATCH /profile', () =>
      jsonResponse(422, { detail: [{ loc: ['body', 'telegram'], msg: 'bad' }] }),
    )
    await setBirthDate(wrapper, new Date(2000, 0, 15))
    await wrapper.get('[data-testid="field-telegram"]').setValue('@valid_name')
    await submitForm(wrapper)

    expect(wrapper.get('[data-testid="error-telegram"]').text()).toBe('Некорректное значение')
  })

  it('на мобильной ширине дата выбирается нативным полем с ограничениями', async () => {
    setViewportWidth(360)
    const api = profileApi(draftProfile)
    const { wrapper } = await renderApp('/onboarding')

    expect(wrapper.findComponent(DatePicker).exists()).toBe(false)
    const input = wrapper.get('[data-testid="field-birth-date-native"]')
    expect(input.attributes('type')).toBe('date')
    expect(input.attributes('min')).toBe('1900-01-01')
    expect(input.attributes('max')).toBe(toIsoDate(startOfToday()))

    await wrapper.get('[data-testid="field-name"]').setValue('Анна')
    await input.setValue('2000-01-15')
    await submitForm(wrapper)
    expect(api.calls('PATCH /profile')[0]?.body).toEqual({ name: 'Анна', birth_date: '2000-01-15' })
  })

  it('при смене ширины 1024 -> 639 введённые данные сохраняются', async () => {
    profileApi(draftProfile)
    const { wrapper } = await renderApp('/onboarding')
    await wrapper.get('[data-testid="field-name"]').setValue('Анна')
    await setBirthDate(wrapper, new Date(2000, 0, 15))

    setViewportWidth(639)
    await settle()

    expect((wrapper.get('[data-testid="field-name"]').element as HTMLInputElement).value).toBe(
      'Анна',
    )
    const native = wrapper.get('[data-testid="field-birth-date-native"]')
    expect((native.element as HTMLInputElement).value).toBe('2000-01-15')
  })
})

describe('Просмотр профиля', () => {
  it('показывает данные, «не указано» и инициалы', async () => {
    profileApi({ ...completeProfile, email: null })
    const { wrapper } = await renderApp('/profile')

    expect(wrapper.get('[data-testid="profile-name"]').text()).toBe('Анна Иванова')
    expect(wrapper.get('[data-testid="profile-age"]').text()).toBe('26 лет')
    expect(wrapper.get('[data-testid="profile-birth-date"]').text()).toBe('15.01.2000')
    expect(wrapper.get('[data-testid="profile-phone"]').text()).toBe('+7 999 123-45-67')
    expect(wrapper.get('[data-testid="profile-telegram"]').text()).toBe('@anna_k')
    expect(wrapper.get('[data-testid="profile-email"]').text()).toBe('не указано')
    expect(wrapper.get('[data-testid="profile-avatar-initials"]').text()).toBe('АИ')
  })

  it('показывает аватар по photo_url', async () => {
    profileApi({ ...completeProfile, photo_url: 'https://example.com/a.png' })
    const { wrapper } = await renderApp('/profile')

    const img = wrapper.get('[data-testid="profile-avatar-image"] img')
    expect(img.attributes('src')).toBe('https://example.com/a.png')
    expect(wrapper.find('[data-testid="profile-avatar-initials"]').exists()).toBe(false)
  })
})

describe('Редактирование профиля на месте', () => {
  async function openEditor(profile: Profile = completeProfile) {
    const api = profileApi(profile)
    const app = await renderApp('/profile')
    await app.wrapper.get('[data-testid="profile-edit"]').trigger('click')
    await settle()
    return { api, ...app }
  }

  const labels = (wrapper: VueWrapper) =>
    wrapper.findAll('.profile-card__row dt').map((dt) => dt.text())
  const value = (wrapper: VueWrapper, id: string) =>
    (wrapper.get(`[data-testid="${id}"]`).element as HTMLInputElement).value

  it('значения заменяются полями в той же раскладке', async () => {
    profileApi(completeProfile)
    const { wrapper } = await renderApp('/profile')
    const card = wrapper.get('[data-testid="profile-card"]').element
    const actions = wrapper.get('[data-testid="profile-actions"]').element
    const labelsBefore = labels(wrapper)

    await wrapper.get('[data-testid="profile-edit"]').trigger('click')
    await settle()

    // Тот же элемент карточки и тот же блок действий — окно не подменяется другой формой
    expect(wrapper.get('[data-testid="profile-card"]').element).toBe(card)
    expect(wrapper.get('[data-testid="profile-actions"]').element).toBe(actions)
    expect(labels(wrapper)).toEqual(labelsBefore)
    expect(wrapper.find('[data-testid="profile-form"]').exists()).toBe(false)

    // Значения стали полями с текущими значениями
    expect(wrapper.find('[data-testid="profile-name"]').exists()).toBe(false)
    expect(value(wrapper, 'field-name')).toBe('Анна Иванова')
    expect(value(wrapper, 'field-telegram')).toBe('@anna_k')
    expect(wrapper.getComponent(DatePicker).props('modelValue')).toEqual(new Date(2000, 0, 15))

    // Телефон, аватар и возраст остаются текстом на местах
    expect(wrapper.get('[data-testid="profile-phone"]').text()).toBe('+7 999 123-45-67')
    expect(wrapper.find('[data-testid="profile-avatar-initials"]').exists()).toBe(true)
    expect(wrapper.get('[data-testid="profile-age"]').text()).toBe('26 лет')

    // «Редактировать» сменилась на «Сохранить» и «Отмена» в том же блоке
    expect(wrapper.find('[data-testid="profile-edit"]').exists()).toBe(false)
    expect(actions.contains(wrapper.get('[data-testid="profile-submit"]').element)).toBe(true)
    expect(actions.contains(wrapper.get('[data-testid="profile-cancel"]').element)).toBe(true)
  })

  it('пустое необязательное поле вместо «не указано»', async () => {
    const { wrapper } = await openEditor({ ...completeProfile, email: null })

    expect(wrapper.find('[data-testid="profile-email"]').exists()).toBe(false)
    expect(value(wrapper, 'field-email')).toBe('')
  })

  it('ошибка показывается под полем на своём месте', async () => {
    const { api, wrapper } = await openEditor()

    await wrapper.get('[data-testid="field-telegram"]').setValue('@abc')
    await submitForm(wrapper)

    const row = wrapper.get('[data-testid="field-telegram"]').element.closest('dd')
    expect(row?.querySelector('[data-testid="error-telegram"]')).not.toBeNull()
    expect(api.calls('PATCH /profile')).toHaveLength(0)
  })

  it('на мобильной ширине дата в режиме редактирования — нативное поле', async () => {
    setViewportWidth(360)
    const { wrapper } = await openEditor()

    expect(value(wrapper, 'field-birth-date-native')).toBe('2000-01-15')
  })

  it('отправляет только изменённое имя и показывает его', async () => {
    const { api, wrapper } = await openEditor()

    await wrapper.get('[data-testid="field-name"]').setValue('Мария')
    await submitForm(wrapper)

    expect(api.calls('PATCH /profile')[0]?.body).toEqual({ name: 'Мария' })
    expect(wrapper.get('[data-testid="profile-name"]').text()).toBe('Мария')
  })

  it('очищенный Telegram уходит как null', async () => {
    const { api, wrapper } = await openEditor()

    await wrapper.get('[data-testid="field-telegram"]').setValue('')
    await submitForm(wrapper)

    expect(api.calls('PATCH /profile')[0]?.body).toEqual({ telegram: null })
    expect(wrapper.get('[data-testid="profile-telegram"]').text()).toBe('не указано')
  })

  it('отмена возвращает к просмотру без запросов', async () => {
    const { api, wrapper } = await openEditor()

    await wrapper.get('[data-testid="field-name"]').setValue('Другое имя')
    await wrapper.get('[data-testid="profile-cancel"]').trigger('click')
    await settle()

    expect(api.calls('PATCH /profile')).toHaveLength(0)
    expect(wrapper.get('[data-testid="profile-name"]').text()).toBe('Анна Иванова')
  })

  it('без изменений сохранение не отправляет запрос', async () => {
    const { api, wrapper } = await openEditor()

    await submitForm(wrapper)

    expect(api.calls('PATCH /profile')).toHaveLength(0)
    expect(wrapper.find('[data-testid="field-name"]').exists()).toBe(false)
    expect(wrapper.get('[data-testid="profile-name"]').text()).toBe('Анна Иванова')
    expect(wrapper.find('[data-testid="profile-edit"]').exists()).toBe(true)
  })
})
