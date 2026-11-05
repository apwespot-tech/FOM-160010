import {
  createRouter,
  createWebHistory,
  type RouteLocationNormalized,
  type RouterHistory,
} from 'vue-router'

import { useSessionStore } from '@/stores/session'

declare module 'vue-router' {
  interface RouteMeta {
    /** Только для гостей; остальные страницы — для любого авторизованного пользователя */
    guest?: boolean
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
    // Короткий адрес своего профиля: гард уже загрузил сессию
    path: '/profile',
    name: 'profile',
    component: () => import('@/views/UserProfileView.vue'),
    beforeEnter: () => {
      const session = useSessionStore()
      return session.profile ? `/users/${session.profile.id}` : '/'
    },
  },
  {
    path: '/users/:id',
    name: 'user',
    component: () => import('@/views/UserProfileView.vue'),
  },
  {
    path: '/',
    name: 'events',
    component: () => import('@/views/EventsView.vue'),
    // Мероприятие открывается окном поверх списка: список остаётся смонтированным
    children: [
      {
        path: 'events/:id',
        name: 'event',
        component: () => import('@/views/EventModal.vue'),
      },
    ],
  },
  { path: '/:pathMatch(.*)*', redirect: '/' },
]

type SessionState = { isAuthenticated: boolean }

/** Куда перенаправить; null — доступ разрешён. */
export function resolveRedirect(to: RouteLocationNormalized, session: SessionState): string | null {
  if (!session.isAuthenticated) return to.meta.guest ? null : '/login'
  // Незаполненный профиль не ограничивает страницы: профиль просят заполнить при действиях
  return to.meta.guest ? '/' : null
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
