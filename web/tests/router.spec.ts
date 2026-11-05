import { describe, expect, it } from 'vitest'

import { completeProfile, draftProfile, mockApi } from './helpers/api'
import { renderApp, withStoredSession } from './helpers/render'

async function currentPath(path: string) {
  const { router } = await renderApp(path)
  return router.currentRoute.value.path
}

describe('Доступ к страницам', () => {
  describe('гость', () => {
    it.each(['/profile', '/users/u2', '/onboarding', '/', '/events/e1', '/unknown/page'])(
      '%s -> /login',
      async (path) => {
        mockApi()
        expect(await currentPath(path)).toBe('/login')
      },
    )

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
    it.each(['/login', '/onboarding', '/unknown'])('%s -> /', async (path) => {
      withStoredSession(mockApi(), completeProfile)
      expect(await currentPath(path)).toBe('/')
    })

    it.each(['/', '/events/e1', '/users/u2'])('%s доступен', async (path) => {
      withStoredSession(mockApi(), completeProfile)
      expect(await currentPath(path)).toBe(path)
    })

    it('/profile -> /users/<свой id>', async () => {
      withStoredSession(mockApi(), completeProfile)
      expect(await currentPath('/profile')).toBe(`/users/${completeProfile.id}`)
    })
  })
})
