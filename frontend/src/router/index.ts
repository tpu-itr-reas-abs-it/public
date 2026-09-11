import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/AuthView.vue'),
      props: { mode: 'login' },
      meta: { public: true },
    },
    {
      path: '/register',
      name: 'register',
      component: () => import('@/views/AuthView.vue'),
      props: { mode: 'register' },
      meta: { public: true },
    },
    { path: '/', redirect: { name: 'projects' } },
    {
      path: '/projects',
      name: 'projects',
      component: () => import('@/views/ProjectsView.vue'),
    },
    {
      path: '/projects/new',
      name: 'project-create',
      component: () => import('@/views/CreateProjectView.vue'),
    },
    {
      path: '/projects/:id(\\d+)',
      name: 'workspace',
      component: () => import('@/views/WorkspaceView.vue'),
      props: (route) => ({ projectId: Number(route.params.id) }),
    },
    { path: '/:pathMatch(.*)*', redirect: { name: 'projects' } },
  ],
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  if (!auth.ready) await auth.loadMe()

  if (!to.meta.public && !auth.isAuthenticated) {
    return { name: 'login', query: to.fullPath !== '/' ? { redirect: to.fullPath } : {} }
  }
  if (to.meta.public && auth.isAuthenticated) {
    return { name: 'projects' }
  }
  return true
})

export default router
