import { describe, expect, it } from 'vitest'

import { completeProfile, draftProfile, mockApi } from './helpers/api'
import { renderApp, withStoredSession } from './helpers/render'

async function currentPath(path: string) {
  const { router } = await renderApp(path)
  return router.currentRoute.value.path
}

describe('Доступ к страницам', () => {
  describe('гость', () => {
    it.each(['/profile', '/onboarding', '/', '/unknown/page'])('%s -> /login', async (path) => {
      mockApi()
      expect(await currentPath(path)).toBe('/login')
    })

    it('/login доступен', async () => {
      mockApi()
      expect(await currentPath('/login')).toBe('/login')
    })
  })

  describe('незаполненный профиль', () => {
    it.each(['/profile', '/login', '/', '/unknown'])('%s -> /onboarding', async (path) => {
      withStoredSession(mockApi(), draftProfile)
      expect(await currentPath(path)).toBe('/onboarding')
    })

    it('/onboarding доступен', async () => {
      withStoredSession(mockApi(), draftProfile)
      expect(await currentPath('/onboarding')).toBe('/onboarding')
    })
  })

  describe('заполненный профиль', () => {
    it.each(['/login', '/onboarding', '/', '/unknown'])('%s -> /profile', async (path) => {
      withStoredSession(mockApi(), completeProfile)
      expect(await currentPath(path)).toBe('/profile')
    })
  })
})
