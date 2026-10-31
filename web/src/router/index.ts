import {
  createRouter,
  createWebHistory,
  type RouteLocationNormalized,
  type RouterHistory,
} from 'vue-router'

import { useSessionStore } from '@/stores/session'

declare module 'vue-router' {
  interface RouteMeta {
    /** Только для гостей */
    guest?: boolean
    /** Только для пользователей с незаполненным профилем */
    incomplete?: boolean
    /** Только для пользователей с заполненным профилем */
    complete?: boolean
  }
}

export const routes = [
  {
    path: '/login',
    name: 'login',
    component: () => import('@/views/LoginView.vue'),
    meta: { guest: true },
  },
  {
    path: '/onboarding',
    name: 'onboarding',
    component: () => import('@/views/OnboardingView.vue'),
    meta: { incomplete: true },
  },
  {
    path: '/profile',
    name: 'profile',
    component: () => import('@/views/ProfileView.vue'),
    meta: { complete: true },
  },
  {
    path: '/',
    name: 'events',
    component: () => import('@/views/EventsView.vue'),
    meta: { complete: true },
    // Мероприятие открывается окном поверх списка: список остаётся смонтированным
    children: [
      {
        path: 'events/:id',
        name: 'event',
        component: () => import('@/views/EventModal.vue'),
        meta: { complete: true },
      },
    ],
  },
  { path: '/:pathMatch(.*)*', redirect: '/' },
]

type SessionState = { isAuthenticated: boolean; isProfileCompleted: boolean }

/** Куда перенаправить; null — доступ разрешён. */
export function resolveRedirect(to: RouteLocationNormalized, session: SessionState): string | null {
  if (!session.isAuthenticated) return to.meta.guest ? null : '/login'
  if (!session.isProfileCompleted) return to.meta.incomplete ? null : '/onboarding'
  return to.meta.complete ? null : '/'
}

export function createAppRouter(history: RouterHistory = createWebHistory()) {
  const router = createRouter({ history, routes })

  router.beforeEach(async (to) => {
    const session = useSessionStore()
    await session.init()
    return resolveRedirect(to, session) ?? true
  })

  return router
}
