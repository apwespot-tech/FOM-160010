import type { VueWrapper } from '@vue/test-utils'
import DatePicker from 'primevue/datepicker'
import Select from 'primevue/select'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { Profile, ProfilePatch } from '@/api/profile'
import { maxBirthDate, startOfToday, toIsoDate } from '@/utils/dates'

import {
  blobResponse,
  categories,
  cities,
  completeProfile,
  draftProfile,
  errorResponse,
  jsonResponse,
  mockApi,
  type MockRequest,
} from './helpers/api'
import { setViewportWidth } from './helpers/media'
import { renderApp, settle, withStoredSession } from './helpers/render'

function setBirthDate(wrapper: VueWrapper, date: Date | null) {
  wrapper.getComponent(DatePicker).vm.$emit('update:modelValue', date)
  return settle()
}

/** Отправляет форму профиля в режиме редактирования. */
async function submitForm(wrapper: VueWrapper) {
  await wrapper.get('[data-testid="profile-card"]').trigger('submit')
  await settle()
}

const submitDisabled = (wrapper: VueWrapper) =>
  wrapper.get('[data-testid="profile-submit"]').attributes('disabled') !== undefined

describe('Заполнение профиля черновиком', () => {
  it('«Сохранить» неактивна, пока не заполнены имя и дата рождения', async () => {
    const { wrapper } = await openEditor(draftProfile)

    expect(submitDisabled(wrapper)).toBe(true)
    await wrapper.get('[data-testid="field-name"]').setValue('   ')
    expect(submitDisabled(wrapper)).toBe(true)
    await wrapper.get('[data-testid="field-name"]').setValue('Анна')
    expect(submitDisabled(wrapper)).toBe(true)
    await setBirthDate(wrapper, new Date(2000, 0, 15))
    expect(submitDisabled(wrapper)).toBe(false)
  })

  it('сохраняет профиль и остаётся на своей странице в режиме просмотра', async () => {
    const { api, wrapper, router, session } = await openEditor(draftProfile)

    await wrapper.get('[data-testid="field-name"]').setValue('  Анна  ')
    await setBirthDate(wrapper, new Date(2000, 0, 15))
    await submitForm(wrapper)

    expect(api.calls('PATCH /profile')[0]?.body).toEqual({ name: 'Анна', birth_date: '2000-01-15' })
    expect(router.currentRoute.value.path).toBe(`/users/${draftProfile.id}`)
    expect(text(wrapper, 'profile-name')).toBe('Анна')
    expect(session.isProfileCompleted).toBe(true)
  })
})

describe('Проверка полей формы профиля', () => {
  async function filledEditor() {
    const app = await openEditor(draftProfile)
    await app.wrapper.get('[data-testid="field-name"]').setValue('Анна')
    return app
  }

  it('ровно 14 лет принимается', async () => {
    const { api, wrapper } = await filledEditor()
    await setBirthDate(wrapper, maxBirthDate())
    await submitForm(wrapper)

    expect(api.calls('PATCH /profile')).toHaveLength(1)
  })

  it('дата рождения сегодня не отправляется', async () => {
    const { api, wrapper } = await filledEditor()
    await setBirthDate(wrapper, startOfToday())
    await submitForm(wrapper)

    expect(wrapper.get('[data-testid="error-birth-date"]').text()).toBe(
      'Сервисом можно пользоваться с 14 лет',
    )
    expect(api.calls('PATCH /profile')).toHaveLength(0)
  })

  it('на день младше 14 лет не отправляется', async () => {
    const { api, wrapper } = await filledEditor()
    const younger = maxBirthDate()
    younger.setDate(younger.getDate() + 1)

    await setBirthDate(wrapper, younger)
    await submitForm(wrapper)

    expect(wrapper.get('[data-testid="error-birth-date"]').text()).toBe(
      'Сервисом можно пользоваться с 14 лет',
    )
    expect(api.calls('PATCH /profile')).toHaveLength(0)
  })

  it('дата рождения в будущем не отправляется', async () => {
    const { api, wrapper } = await filledEditor()
    const tomorrow = startOfToday()
    tomorrow.setDate(tomorrow.getDate() + 1)

    await setBirthDate(wrapper, tomorrow)
    await submitForm(wrapper)

    expect(wrapper.find('[data-testid="error-birth-date"]').exists()).toBe(true)
    expect(api.calls('PATCH /profile')).toHaveLength(0)
  })

  it('дата младше 14 лет, введённая вручную, не стирается, а даёт ошибку', async () => {
    const { api, wrapper } = await filledEditor()
    const younger = maxBirthDate()
    younger.setDate(younger.getDate() + 1)
    const typed = [younger.getDate(), younger.getMonth() + 1]
      .map((part) => String(part).padStart(2, '0'))
      .concat(String(younger.getFullYear()))
      .join('.')
    const input = wrapper.get('#profile-birth-date')

    await input.setValue(typed)
    await input.trigger('blur')
    await settle()

    expect((input.element as HTMLInputElement).value).toBe(typed)
    expect(wrapper.get('[data-testid="error-birth-date"]').text()).toBe(
      'Сервисом можно пользоваться с 14 лет',
    )
    await submitForm(wrapper)
    expect(api.calls('PATCH /profile')).toHaveLength(0)
  })

  it('пустая дата рождения: ошибка после ухода из поля', async () => {
    const { wrapper } = await filledEditor()
    await wrapper.get('#profile-birth-date').trigger('blur')
    await settle()

    expect(wrapper.get('[data-testid="error-birth-date"]').text()).toBe('Укажите дату рождения')
  })

  it('дата раньше 01.01.1900 не отправляется', async () => {
    const { api, wrapper } = await filledEditor()
    await setBirthDate(wrapper, new Date(1899, 11, 31))
    await submitForm(wrapper)

    expect(wrapper.find('[data-testid="error-birth-date"]').exists()).toBe(true)
    expect(api.calls('PATCH /profile')).toHaveLength(0)
  })

  it('DatePicker ограничен датами 01.01.1900 — сегодня минус 14 лет', async () => {
    const { wrapper } = await filledEditor()
    const props = wrapper.getComponent(DatePicker).props()

    expect(props.minDate).toEqual(new Date(1900, 0, 1))
    expect(props.maxDate).toEqual(maxBirthDate())
  })

  it('сохранённая дата младше 14 лет не мешает изменить «О себе»', async () => {
    const { api, wrapper } = await openEditor({ ...OWN, birth_date: '2020-01-01', age: 6 })
    await wrapper.get('[data-testid="field-about"]').setValue('Люблю настолки')
    await submitForm(wrapper)

    expect(api.calls('PATCH /profile')[0]?.body).toEqual({ about: 'Люблю настолки' })
  })

  it('некорректный Telegram — ошибка поля, без отправки', async () => {
    const { api, wrapper } = await filledEditor()
    await setBirthDate(wrapper, new Date(2000, 0, 15))
    await wrapper.get('[data-testid="field-telegram"]').setValue('@abc')
    await submitForm(wrapper)

    expect(wrapper.get('[data-testid="error-telegram"]').text()).toContain('@username')
    expect(api.calls('PATCH /profile')).toHaveLength(0)
  })

  it('занятый email показывается у поля', async () => {
    const { api, wrapper } = await filledEditor()
    api.on('PATCH /profile', () => errorResponse(409, 'email_taken'))
    await setBirthDate(wrapper, new Date(2000, 0, 15))
    await wrapper.get('[data-testid="field-email"]').setValue('ann@example.com')
    await submitForm(wrapper)

    expect(wrapper.get('[data-testid="error-email"]').text()).toBe('Этот email уже используется')
  })

  it('ошибка валидации сервера раскладывается по полю', async () => {
    const { api, wrapper } = await filledEditor()
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
    const { api, wrapper } = await openEditor(draftProfile)

    expect(wrapper.findComponent(DatePicker).exists()).toBe(false)
    const input = wrapper.get('[data-testid="field-birth-date-native"]')
    expect(input.attributes('type')).toBe('date')
    expect(input.attributes('min')).toBe('1900-01-01')
    expect(input.attributes('max')).toBe(toIsoDate(maxBirthDate()))

    await wrapper.get('[data-testid="field-name"]').setValue('Анна')
    await input.setValue('2000-01-15')
    await submitForm(wrapper)
    expect(api.calls('PATCH /profile')[0]?.body).toEqual({ name: 'Анна', birth_date: '2000-01-15' })
  })

  it('при смене ширины 1024 -> 639 введённые данные сохраняются', async () => {
    const { wrapper } = await openEditor(draftProfile)
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

// --- страница профиля /users/:id ---

const OWN = completeProfile
const OTHER: Profile = {
  ...completeProfile,
  id: 'u2',
  phone: '+79990002222',
  name: 'Борис Петров',
  telegram: '@boris_k',
  email: 'boris@example.com',
}

function text(wrapper: VueWrapper, testId: string): string {
  return wrapper.get(`[data-testid="${testId}"]`).text().replace(/\s+/g, ' ').trim()
}

/** Свой профиль: PATCH применяет патч, загрузка и удаление картинок меняют id. */
function ownProfileApi(profile: Profile = OWN) {
  const api = mockApi({ 'GET /categories': () => jsonResponse(200, categories) })
  withStoredSession(api, profile)
  api.on('GET /cities', () => jsonResponse(200, cities))
  let current: Profile = { ...profile }
  let uploads = 0
  api.on('PATCH /profile', (request: MockRequest) => {
    const { city_id, interest_ids, ...rest } = request.body as ProfilePatch
    current = { ...current, ...rest }
    if (city_id !== undefined) current.city = cities.find((c) => c.id === city_id) ?? null
    if (interest_ids !== undefined) {
      current.interests = categories
        .filter((c) => interest_ids.includes(c.id))
        .map(({ id, name, icon }) => ({ id, name, icon }))
    }
    current.profile_completed = current.name !== null && current.birth_date !== null
    return jsonResponse(200, current)
  })
  api.on('PUT /profile/avatar', () => {
    current = { ...current, avatar_id: `av-${++uploads}` }
    return jsonResponse(200, current)
  })
  api.on('PUT /profile/cover', () => {
    current = { ...current, cover_id: `cv-${++uploads}` }
    return jsonResponse(200, current)
  })
  api.on('DELETE /profile/avatar', () => {
    current = { ...current, avatar_id: null }
    return jsonResponse(200, current)
  })
  return api
}

async function openOwn(profile: Profile = OWN) {
  const api = ownProfileApi(profile)
  const app = await renderApp(`/users/${profile.id}`)
  await settle()
  return { api, ...app }
}

async function openEditor(profile: Profile = OWN) {
  const app = await openOwn(profile)
  await app.wrapper.get('[data-testid="profile-edit"]').trigger('click')
  await settle()
  return app
}

async function selectFile(wrapper: VueWrapper, kind: 'avatar' | 'cover', file: File) {
  const input = wrapper.get(`[data-testid="image-input-${kind}"]`).element as HTMLInputElement
  Object.defineProperty(input, 'files', { value: [file], configurable: true })
  input.dispatchEvent(new Event('change', { bubbles: true }))
  await settle()
}

function photo(name = 'me.jpg', size = 1024, type = 'image/jpeg'): File {
  return new File([new Uint8Array(size)], name, { type })
}

const value = (wrapper: VueWrapper, id: string) =>
  (wrapper.get(`[data-testid="${id}"]`).element as HTMLInputElement).value

describe('Просмотр профиля', () => {
  it('свой профиль: данные, заглушка email, инициалы, полоса без обложки, счётчики', async () => {
    const { wrapper } = await openOwn({
      ...OWN,
      email: null,
      about: 'Обожаю настолки\nи прогулки',
      interests: [
        { id: 1, name: 'Настольные игры', icon: 'pi-th-large' },
        { id: 2, name: 'Прогулки', icon: 'pi-map' },
      ],
      stats: { organized_count: 12, attended_count: 34 },
    })

    expect(text(wrapper, 'profile-name')).toBe('Анна Иванова')
    expect(text(wrapper, 'profile-telegram')).toBe('@anna_k')
    expect(wrapper.get('[data-testid="profile-about"]').text()).toContain('Обожаю настолки')
    expect(wrapper.get('[data-testid="profile-about"]').element.textContent).toContain('\n')
    expect(
      wrapper.findAll('[data-testid="profile-interests"] [data-testid="category-tag"]'),
    ).toHaveLength(2)
    expect(text(wrapper, 'profile-city')).toBe('Москва')
    expect(text(wrapper, 'profile-since')).toBe('На сайте с ноября 2023 года')
    expect(text(wrapper, 'profile-age')).toBe('26 лет')
    expect(text(wrapper, 'profile-birth-date')).toBe('15.01.2000')
    expect(text(wrapper, 'profile-phone')).toBe('+7 999 123-45-67')
    expect(text(wrapper, 'placeholder-email')).toBe('Добавьте email')
    expect(text(wrapper, 'stats-organized')).toBe('12')
    expect(text(wrapper, 'stats-attended')).toBe('34')
    expect(
      wrapper.get('[data-testid="profile-avatar"] [data-testid="avatar-initials"]').text(),
    ).toBe('АИ')
    expect(wrapper.find('[data-testid="profile-cover-image"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="profile-edit"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="profile-share"]').exists()).toBe(true)
  })

  it('аватар и обложка загружаются с токеном по id', async () => {
    const api = ownProfileApi({ ...OWN, avatar_id: 'av-1', cover_id: 'cv-1' })
    api.on(`GET /users/${OWN.id}/images/av-1`, () => blobResponse())
    api.on(`GET /users/${OWN.id}/images/cv-1`, () => blobResponse())
    const { wrapper } = await renderApp(`/users/${OWN.id}`)
    await settle()

    expect(wrapper.get('[data-testid="profile-avatar"] img').attributes('src')).toMatch(/^blob:/)
    expect(wrapper.get('[data-testid="profile-cover-image"]').attributes('src')).toMatch(/^blob:/)
    expect(api.calls(`GET /users/${OWN.id}/images/cv-1`)[0]?.headers.Authorization).toMatch(
      /^Bearer /,
    )
  })

  it('чужой профиль: все поля, без «Редактировать», с «Поделиться»', async () => {
    const api = ownProfileApi()
    api.on('GET /profile/u2', () => jsonResponse(200, OTHER))
    const { wrapper } = await renderApp('/users/u2')
    await settle()

    expect(text(wrapper, 'profile-name')).toBe('Борис Петров')
    expect(text(wrapper, 'profile-phone')).toBe('+7 999 000-22-22')
    expect(text(wrapper, 'profile-email')).toBe('boris@example.com')
    expect(wrapper.find('[data-testid="profile-edit"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="profile-share"]').exists()).toBe(true)
  })

  it.each([403, 404, 422])('ответ %i — «Профиль недоступен»', async (status) => {
    const api = ownProfileApi()
    api.on('GET /profile/u2', () => errorResponse(status, status === 403 ? 'forbidden' : 'nf'))
    const { wrapper } = await renderApp('/users/u2')
    await settle()

    expect(wrapper.get('[data-testid="profile-unavailable"]').text()).toContain(
      'Профиль недоступен',
    )
    expect(wrapper.find('[data-testid="profile-name"]').exists()).toBe(false)
  })
})

describe('Поделиться профилем', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
    Reflect.deleteProperty(navigator, 'share')
    Reflect.deleteProperty(navigator, 'clipboard')
  })

  function toasts(): string {
    return document.body.querySelector('.p-toast')?.textContent ?? ''
  }

  it('системное меню получает ссылку на профиль, отмена — без ошибки', async () => {
    const share = vi.fn().mockRejectedValue(new DOMException('cancel', 'AbortError'))
    Object.defineProperty(navigator, 'share', { value: share, configurable: true })
    const { wrapper } = await openOwn()

    await wrapper.get('[data-testid="profile-share"]').trigger('click')
    await settle()

    expect(share).toHaveBeenCalledWith(
      expect.objectContaining({ url: `${window.location.origin}/users/${OWN.id}` }),
    )
    expect(toasts()).toBe('')
  })

  it('без системного меню — копирование и «Ссылка скопирована»', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined)
    Object.defineProperty(navigator, 'clipboard', { value: { writeText }, configurable: true })
    const { wrapper } = await openOwn()

    await wrapper.get('[data-testid="profile-share"]').trigger('click')
    await settle()

    expect(writeText).toHaveBeenCalledWith(`${window.location.origin}/users/${OWN.id}`)
    expect(toasts()).toContain('Ссылка скопирована')
  })

  it('без буфера обмена — уведомление со ссылкой', async () => {
    const writeText = vi.fn().mockRejectedValue(new Error('denied'))
    Object.defineProperty(navigator, 'clipboard', { value: { writeText }, configurable: true })
    const { wrapper } = await openOwn()

    await wrapper.get('[data-testid="profile-share"]').trigger('click')
    await settle()

    expect(toasts()).toContain(`/users/${OWN.id}`)
  })
})

describe('Редактирование профиля на месте', () => {
  it('страница перестраивается в форму с текущими значениями', async () => {
    const { wrapper, router } = await openOwn()
    const actions = wrapper.get('[data-testid="profile-actions"]').element

    await wrapper.get('[data-testid="profile-edit"]').trigger('click')
    await settle()

    expect(wrapper.find('[data-testid="profile-card"]').exists()).toBe(true)
    expect(value(wrapper, 'field-name')).toBe('Анна Иванова')
    expect(value(wrapper, 'field-telegram')).toBe('@anna_k')
    expect(wrapper.getComponent(DatePicker).props('modelValue')).toEqual(new Date(2000, 0, 15))
    expect(text(wrapper, 'profile-phone')).toBe('+7 999 123-45-67')
    expect(wrapper.find('[data-testid="profile-edit"]').exists()).toBe(false)
    expect(actions.contains(wrapper.get('[data-testid="profile-submit"]').element)).toBe(true)
    expect(actions.contains(wrapper.get('[data-testid="profile-cancel"]').element)).toBe(true)
    expect(router.currentRoute.value.path).toBe(`/users/${OWN.id}`)
  })

  it('пустое необязательное поле', async () => {
    const { wrapper } = await openEditor({ ...OWN, email: null })

    expect(value(wrapper, 'field-email')).toBe('')
  })

  it('выбор интересов подсвечивает категории', async () => {
    const { wrapper } = await openEditor()

    await wrapper.get('[data-testid="interest-2"]').trigger('click')
    await wrapper.get('[data-testid="interest-4"]').trigger('click')

    expect(wrapper.get('[data-testid="interest-2"]').attributes('aria-pressed')).toBe('true')
    expect(wrapper.get('[data-testid="interest-4"]').attributes('aria-pressed')).toBe('true')
    expect(wrapper.get('[data-testid="interest-1"]').attributes('aria-pressed')).toBe('false')
  })

  it('некорректный Telegram — ошибка у поля, без отправки', async () => {
    const { api, wrapper } = await openEditor()

    await wrapper.get('[data-testid="field-telegram"]').setValue('@abc')
    await submitForm(wrapper)

    expect(wrapper.find('[data-testid="error-telegram"]').exists()).toBe(true)
    expect(api.calls('PATCH /profile')).toHaveLength(0)
  })

  it('«О себе» длиннее 500 — ошибка и счётчик, без отправки', async () => {
    const { api, wrapper } = await openEditor()

    await wrapper.get('[data-testid="field-about"]').setValue('а'.repeat(501))
    await submitForm(wrapper)

    expect(text(wrapper, 'error-about')).toBe('Не больше 500 символов')
    expect(text(wrapper, 'about-counter')).toBe('501 / 500')
    expect(api.calls('PATCH /profile')).toHaveLength(0)
  })

  it('большой файл аватара не принимается', async () => {
    const { wrapper } = await openEditor()

    await selectFile(wrapper, 'avatar', photo('big.jpg', 3 * 1024 * 1024))

    expect(text(wrapper, 'error-image-avatar')).toBe('Файл больше 2 МБ')
    expect(wrapper.find('[data-testid="image-preview-avatar"]').exists()).toBe(false)
  })

  it('на мобильной ширине дата — нативное поле', async () => {
    setViewportWidth(360)
    const { wrapper } = await openEditor()

    expect(value(wrapper, 'field-birth-date-native')).toBe('2000-01-15')
  })
})

describe('Сохранение изменений профиля', () => {
  it('отправляет только изменённое имя и показывает его', async () => {
    const { api, wrapper } = await openEditor()

    await wrapper.get('[data-testid="field-name"]').setValue('Мария')
    await submitForm(wrapper)

    expect(api.calls('PATCH /profile')[0]?.body).toEqual({ name: 'Мария' })
    expect(text(wrapper, 'profile-name')).toBe('Мария')
  })

  it('очищенный Telegram уходит как null', async () => {
    const { api, wrapper } = await openEditor()

    await wrapper.get('[data-testid="field-telegram"]').setValue('')
    await submitForm(wrapper)

    expect(api.calls('PATCH /profile')[0]?.body).toEqual({ telegram: null })
    expect(text(wrapper, 'placeholder-telegram')).toBe('Добавьте Telegram')
  })

  it('город, «О себе» и интересы', async () => {
    const { api, wrapper } = await openEditor()

    wrapper
      .findAllComponents(Select)
      .find((select) => select.attributes('data-testid') === 'field-city')
      ?.vm.$emit('update:modelValue', 5)
    await wrapper.get('[data-testid="field-about"]').setValue('  Люблю\nнастолки  ')
    await wrapper.get('[data-testid="interest-2"]').trigger('click')
    await wrapper.get('[data-testid="interest-1"]').trigger('click')
    await submitForm(wrapper)

    expect(api.calls('PATCH /profile')[0]?.body).toEqual({
      city_id: 5,
      about: 'Люблю\nнастолки',
      interest_ids: [1, 2],
    })
    expect(text(wrapper, 'profile-city')).toBe('Казань')
  })

  it('отмена отбрасывает поля и выбранный аватар без запросов', async () => {
    const { api, wrapper } = await openEditor()

    await wrapper.get('[data-testid="field-name"]').setValue('Другое имя')
    await selectFile(wrapper, 'avatar', photo())
    await wrapper.get('[data-testid="profile-cancel"]').trigger('click')
    await settle()

    expect(api.calls('PATCH /profile')).toHaveLength(0)
    expect(api.calls('PUT /profile/avatar')).toHaveLength(0)
    expect(text(wrapper, 'profile-name')).toBe('Анна Иванова')
    expect(
      wrapper.find('[data-testid="profile-avatar"] [data-testid="avatar-initials"]').exists(),
    ).toBe(true)
  })

  it('без изменений запрос не отправляется', async () => {
    const { api, wrapper } = await openEditor()

    await submitForm(wrapper)

    expect(api.calls('PATCH /profile')).toHaveLength(0)
    expect(wrapper.find('[data-testid="profile-edit"]').exists()).toBe(true)
  })

  it('только новый аватар — без PATCH, PUT с файлом', async () => {
    const { api, wrapper } = await openEditor()
    api.on(`GET /users/${OWN.id}/images/av-1`, () => blobResponse())

    await selectFile(wrapper, 'avatar', photo('me.png', 2048, 'image/png'))
    expect(wrapper.get('[data-testid="image-preview-avatar"]').attributes('src')).toMatch(/^blob:/)
    await submitForm(wrapper)

    expect(api.calls('PATCH /profile')).toHaveLength(0)
    const form = api.calls('PUT /profile/avatar')[0]?.body as FormData
    expect((form.get('file') as File).name).toBe('me.png')
    expect(wrapper.find('[data-testid="profile-edit"]').exists()).toBe(true)
    expect(wrapper.get('[data-testid="profile-avatar"] img').attributes('src')).toMatch(/^blob:/)
  })

  it('обложка не загрузилась после PATCH — форма открыта, повтор шлёт только обложку', async () => {
    const { api, wrapper } = await openEditor()
    let failCover = true
    api.on('PUT /profile/cover', () =>
      failCover
        ? errorResponse(422, 'photo_invalid', { file: 0 })
        : jsonResponse(200, { ...OWN, name: 'Мария', cover_id: 'cv-9' }),
    )

    await wrapper.get('[data-testid="field-name"]').setValue('Мария')
    await selectFile(wrapper, 'cover', photo('cover.jpg'))
    await submitForm(wrapper)

    expect(api.calls('PATCH /profile')).toHaveLength(1)
    expect(text(wrapper, 'error-image-cover')).toBe('Поддерживаются JPEG, PNG и WebP')
    expect(wrapper.find('[data-testid="profile-card"]').exists()).toBe(true)

    failCover = false
    await submitForm(wrapper)

    expect(api.calls('PATCH /profile')).toHaveLength(1)
    expect(api.calls('PUT /profile/cover')).toHaveLength(2)
    expect(wrapper.find('[data-testid="profile-edit"]').exists()).toBe(true)
  })
})

describe('Заглушки незаполненных полей своего профиля', () => {
  const PLACEHOLDERS = {
    'placeholder-name': 'Укажите имя',
    'placeholder-telegram': 'Добавьте Telegram',
    'placeholder-about': 'Расскажите о себе',
    'placeholder-interests': 'Добавьте интересы',
    'placeholder-city': 'Укажите город',
    'placeholder-birth-date': 'Укажите дату рождения',
    'placeholder-email': 'Добавьте email',
  }

  it('новый профиль: заглушки на месте всех полей и иконка вместо аватара', async () => {
    const { wrapper } = await openOwn(draftProfile)

    for (const [testId, label] of Object.entries(PLACEHOLDERS)) {
      expect(text(wrapper, testId)).toBe(label)
    }
    expect(wrapper.find('[data-testid="profile-name"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="profile-about"]').exists()).toBe(false)
    expect(
      wrapper.find('[data-testid="profile-avatar"] [data-testid="avatar-icon"]').exists(),
    ).toBe(true)
  })

  it('нажатие на заглушку открывает редактирование без смены адреса', async () => {
    const { wrapper, router } = await openOwn(draftProfile)

    await wrapper.get('[data-testid="placeholder-about"]').trigger('click')
    await settle()

    expect(wrapper.find('[data-testid="profile-edit-title"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="field-about"]').exists()).toBe(true)
    expect(router.currentRoute.value.path).toBe(`/users/${draftProfile.id}`)
  })

  it('заглушка — кнопка: доступна с клавиатуры', async () => {
    const { wrapper } = await openOwn(draftProfile)
    const placeholder = wrapper.get('[data-testid="placeholder-city"]')

    expect(placeholder.element.tagName).toBe('BUTTON')
    expect(placeholder.attributes('type')).toBe('button')
  })

  it('частично заполненный профиль: значения и заглушки вперемешку', async () => {
    const { wrapper } = await openOwn({ ...OWN, telegram: null, email: null })

    expect(text(wrapper, 'profile-name')).toBe('Анна Иванова')
    expect(text(wrapper, 'profile-birth-date')).toBe('15.01.2000')
    expect(text(wrapper, 'profile-city')).toBe('Москва')
    expect(text(wrapper, 'placeholder-telegram')).toBe('Добавьте Telegram')
    expect(text(wrapper, 'placeholder-about')).toBe('Расскажите о себе')
    expect(text(wrapper, 'placeholder-interests')).toBe('Добавьте интересы')
    expect(text(wrapper, 'placeholder-email')).toBe('Добавьте email')
    expect(wrapper.find('[data-testid="placeholder-name"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="placeholder-city"]').exists()).toBe(false)
  })

  it('на чужом профиле заглушек нет, пустое — «не указано»', async () => {
    const api = ownProfileApi()
    api.on('GET /profile/u2', () => jsonResponse(200, { ...OTHER, email: null, about: null }))
    const { wrapper } = await renderApp('/users/u2')
    await settle()

    expect(wrapper.find('[data-testid^="placeholder-"]').exists()).toBe(false)
    expect(text(wrapper, 'profile-email')).toBe('не указано')
  })
})
