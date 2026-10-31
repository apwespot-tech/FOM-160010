import { afterEach, describe, expect, it, vi } from 'vitest'

import {
  completeProfile,
  draftProfile,
  errorResponse,
  jsonResponse,
  mockApi,
  tokens,
  type MockHandler,
} from './helpers/api'
import { renderApp, settle, waitForPath } from './helpers/render'

const PHONE = '+79991234567'

function loginApi(overrides: Record<string, MockHandler> = {}) {
  let codeNo = 0
  return mockApi({
    'POST /auth/code': () => {
      codeNo += 1
      return jsonResponse(200, { expires_in: 300 })
    },
    'GET /auth/test/code': () => jsonResponse(200, { code: `11111${codeNo}` }),
    'POST /auth/verify': () => jsonResponse(200, tokens(1)),
    'GET /profile': () => jsonResponse(200, draftProfile),
    ...overrides,
  })
}

async function openCodeStep(phone = PHONE) {
  const app = await renderApp('/login')
  await app.wrapper.get('[data-testid="phone-input"]').setValue(phone)
  await app.wrapper.get('form').trigger('submit')
  await settle()
  return app
}

afterEach(() => {
  vi.useRealTimers()
})

describe('Ввод телефона', () => {
  it('поле телефона вызывает телефонную клавиатуру', async () => {
    mockApi()
    const { wrapper } = await renderApp('/login')
    const input = wrapper.get('[data-testid="phone-input"]')

    expect(input.attributes('type')).toBe('tel')
    expect(input.attributes('inputmode')).toBe('tel')
    expect(input.attributes('autocomplete')).toBe('tel')
  })

  it('кнопка неактивна, пока номер не введён', async () => {
    mockApi()
    const { wrapper } = await renderApp('/login')
    expect(wrapper.get('[data-testid="phone-submit"]').attributes('disabled')).toBeDefined()
  })

  it('успешный запрос кода открывает шаг кода с номером', async () => {
    const api = loginApi()
    const { wrapper } = await openCodeStep('8 999 123-45-67')

    expect(api.calls('POST /auth/code')[0]?.body).toEqual({ phone: '8 999 123-45-67' })
    expect(wrapper.get('[data-testid="code-phone"]').text()).toBe('8 999 123-45-67')
    expect(wrapper.find('[data-testid="code-input"]').exists()).toBe(true)
  })

  it('422 показывается как ошибка поля без перехода', async () => {
    loginApi({
      'POST /auth/code': () => jsonResponse(422, { detail: [{ loc: ['body', 'phone'] }] }),
    })
    const { wrapper } = await openCodeStep('12ab')

    expect(wrapper.get('[data-testid="phone-error"]').text()).toBe('Некорректный номер телефона')
    expect(wrapper.find('[data-testid="code-input"]').exists()).toBe(false)
  })

  it('429 открывает шаг кода с таймером из retry_after', async () => {
    loginApi({ 'POST /auth/code': () => errorResponse(429, 'code_cooldown', { retry_after: 42 }) })
    const { wrapper } = await openCodeStep()

    const resend = wrapper.get('[data-testid="code-resend"]')
    expect(resend.text()).toContain('42 с')
    expect(resend.attributes('disabled')).toBeDefined()
  })
})

describe('Подсказка с тестовым кодом', () => {
  it('показывает код, если тестовая ручка его вернула', async () => {
    const api = loginApi({ 'GET /auth/test/code': () => jsonResponse(200, { code: '711694' }) })
    const { wrapper } = await openCodeStep()

    expect(api.calls('GET /auth/test/code')[0]?.url).toBe(
      `/api/auth/test/code?phone=${encodeURIComponent(PHONE)}`,
    )
    const hint = wrapper.get('[data-testid="dev-code"]')
    expect(hint.text()).toContain('Тестовый режим')
    expect(wrapper.get('[data-testid="dev-code-value"]').text()).toBe('711694')
  })

  it('при 404 подсказки и ошибок нет', async () => {
    loginApi({ 'GET /auth/test/code': () => errorResponse(404, 'not_found') })
    const { wrapper } = await openCodeStep()

    expect(wrapper.find('[data-testid="dev-code"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="code-error"]').exists()).toBe(false)
    expect(wrapper.find('.p-message-error').exists()).toBe(false)
  })

  it('после повторной отправки показывает новый код', async () => {
    vi.useFakeTimers({ toFake: ['setInterval', 'clearInterval', 'Date'] })
    loginApi()
    const { wrapper } = await openCodeStep()
    expect(wrapper.get('[data-testid="dev-code-value"]').text()).toBe('111111')

    vi.advanceTimersByTime(60_000)
    await settle()
    await wrapper.get('[data-testid="code-resend"]').trigger('click')
    await settle()

    expect(wrapper.get('[data-testid="dev-code-value"]').text()).toBe('111112')
  })
})

describe('Повторная отправка кода', () => {
  it('кнопка неактивна до истечения 60 секунд и активна ровно после', async () => {
    vi.useFakeTimers({ toFake: ['setInterval', 'clearInterval', 'Date'] })
    const api = loginApi()
    const { wrapper } = await openCodeStep()
    const resend = () => wrapper.get('[data-testid="code-resend"]')

    vi.advanceTimersByTime(59_000)
    await settle()
    expect(resend().attributes('disabled')).toBeDefined()
    expect(resend().text()).toContain('(1 с)')

    vi.advanceTimersByTime(1_000)
    await settle()
    expect(resend().attributes('disabled')).toBeUndefined()

    await resend().trigger('click')
    await settle()
    expect(api.calls('POST /auth/code')).toHaveLength(2)
    expect(resend().attributes('disabled')).toBeDefined()
    expect(resend().text()).toContain('(60 с)')
  })
})

describe('Ввод кода', () => {
  it('поле кода — цифровая клавиатура и автозаполнение из SMS', async () => {
    loginApi()
    const { wrapper } = await openCodeStep()
    const input = wrapper.get('[data-testid="code-input"]')

    expect(input.attributes('inputmode')).toBe('numeric')
    expect(input.attributes('autocomplete')).toBe('one-time-code')
    expect(input.attributes('maxlength')).toBe('6')
  })

  async function enterCode(
    wrapper: Awaited<ReturnType<typeof openCodeStep>>['wrapper'],
    code: string,
  ) {
    await wrapper.get('[data-testid="code-input"]').setValue(code)
    await wrapper.get('form').trigger('submit')
    await settle()
  }

  it('первый вход открывает онбординг и сохраняет сессию', async () => {
    const api = loginApi()
    const { wrapper, router, session } = await openCodeStep()

    await enterCode(wrapper, '123456')

    expect(api.calls('POST /auth/verify')[0]?.body).toEqual({ phone: PHONE, code: '123456' })
    await waitForPath(router, '/onboarding')
    expect(session.accessToken).toBe('access-1')
    expect(localStorage.getItem('ik.refreshToken')).toBe('refresh-1')
  })

  it('повторный вход открывает главную', async () => {
    loginApi({ 'GET /profile': () => jsonResponse(200, completeProfile) })
    const { wrapper, router } = await openCodeStep()

    await enterCode(wrapper, '123456')

    await waitForPath(router, '/')
  })

  it('неверный код: ошибка и очищенное поле', async () => {
    loginApi({ 'POST /auth/verify': () => errorResponse(400, 'invalid_code') })
    const { wrapper, router } = await openCodeStep()

    await enterCode(wrapper, '000000')

    expect(wrapper.get('[data-testid="code-error"]').text()).toBe('Неверный или просроченный код')
    expect((wrapper.get('[data-testid="code-input"]').element as HTMLInputElement).value).toBe('')
    expect(router.currentRoute.value.path).toBe('/login')
  })

  it('в поле кода остаются только цифры, кнопка активна при 6 цифрах', async () => {
    loginApi()
    const { wrapper } = await openCodeStep()
    const input = wrapper.get('[data-testid="code-input"]')

    await input.setValue('12a3')
    expect((input.element as HTMLInputElement).value).toBe('123')
    expect(wrapper.get('[data-testid="code-submit"]').attributes('disabled')).toBeDefined()
    await input.setValue('123456')
    expect(wrapper.get('[data-testid="code-submit"]').attributes('disabled')).toBeUndefined()
  })

  it('«Изменить номер» возвращает к телефону с сохранённым номером', async () => {
    loginApi()
    const { wrapper } = await openCodeStep()

    await wrapper.get('[data-testid="code-change-phone"]').trigger('click')
    await settle()

    const input = wrapper.get('[data-testid="phone-input"]').element as HTMLInputElement
    expect(input.value).toBe(PHONE)
  })
})
