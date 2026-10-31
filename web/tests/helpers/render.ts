import { flushPromises, mount, type ComponentMountingOptions } from '@vue/test-utils'
import { createPinia, setActivePinia, type Pinia } from 'pinia'
import ru from 'primelocale/ru.json'
import PrimeVue from 'primevue/config'
import ToastService from 'primevue/toastservice'
import { vi } from 'vitest'
import type { Component, Plugin } from 'vue'
import { createMemoryHistory, type Router } from 'vue-router'

import type { Profile } from '@/api/profile'
import App from '@/App.vue'
import { createAppRouter } from '@/router'
import { REFRESH_TOKEN_KEY, useSessionStore } from '@/stores/session'
import { themeOptions } from '@/theme'

import { jsonResponse, tokens, type mockApi } from './api'

type PluginEntry = Plugin | [Plugin, ...unknown[]]

export function primeVuePlugins(pinia: Pinia): PluginEntry[] {
  return [pinia, [PrimeVue, { theme: themeOptions, locale: ru.ru }], ToastService]
}

/** Монтирует компонент с Pinia и PrimeVue (без роутера). */
export function mountWithPrimeVue<C extends Component>(
  component: C,
  options: ComponentMountingOptions<C> = {},
  pinia: Pinia = createPinia(),
) {
  setActivePinia(pinia)
  return mount(component, {
    ...options,
    global: { ...options.global, plugins: [...primeVuePlugins(pinia)] },
  } as ComponentMountingOptions<C>)
}

/** Монтирует всё приложение на заданном адресе с роутером в памяти. */
export async function renderApp(path: string) {
  const pinia = createPinia()
  setActivePinia(pinia)
  const router = createAppRouter(createMemoryHistory())
  void router.push(path)
  await router.isReady()
  const wrapper = mount(App, {
    attachTo: document.body,
    global: { plugins: [router, ...primeVuePlugins(pinia)] },
  })
  await settle()
  return { wrapper, router, session: useSessionStore(pinia) }
}

/** Сохранённая сессия: refresh-токен в localStorage и ответы на её восстановление. */
export function withStoredSession(api: ReturnType<typeof mockApi>, profile: Profile): void {
  localStorage.setItem(REFRESH_TOKEN_KEY, 'refresh-0')
  let n = 0
  api.on('POST /auth/refresh', () => jsonResponse(200, tokens(++n)))
  api.on('GET /profile', () => jsonResponse(200, profile))
}

export async function settle(): Promise<void> {
  for (let i = 0; i < 5; i++) await flushPromises()
}

/** Ждёт перехода: страницы грузятся лениво (динамический import). */
export async function waitForPath(router: Router, path: string): Promise<void> {
  await vi.waitFor(() => {
    if (router.currentRoute.value.path !== path) {
      throw new Error(`route is ${router.currentRoute.value.path}, expected ${path}`)
    }
  })
  await settle()
}
