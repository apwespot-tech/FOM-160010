import { createRouter, createWebHistory } from 'vue-router'

import { useAuthStore } from '@/stores/auth'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'events',
      component: () => import('@/views/EventsView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/events/:id',
      name: 'event',
      component: () => import('@/views/EventView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/join/:code',
      name: 'join',
      component: () => import('@/views/JoinView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/LoginView.vue'),
    },
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  if (auth.isAuthenticated && !auth.user) await auth.fetchMe()

  if (to.meta.requiresAuth && !auth.isAuthenticated) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }
  if (to.name === 'login' && auth.isAuthenticated) return { name: 'events' }
  return true
})

export default router


