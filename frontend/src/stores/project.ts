import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { analyticsApi, projectsApi, tasksApi } from '@/api'
import { useAuthStore } from '@/stores/auth'
import type {
  GanttResponse,
  Member,
  MemberRole,
  ProjectDetail,
  ProjectStats,
  Task,
} from '@/types/api'

export const useProjectStore = defineStore('project', () => {
  const projectId = ref<number | null>(null)
  const project = ref<ProjectDetail | null>(null)
  const members = ref<Member[]>([])
  const tasks = ref<Task[]>([])
  const gantt = ref<GanttResponse | null>(null)
  const stats = ref<ProjectStats | null>(null)

  const loading = ref(false)
  const tasksLoading = ref(false)

  const auth = useAuthStore()

  const myRole = computed<MemberRole | null>(() => {
    const me = auth.user?.id
    if (!me) return null
    return members.value.find((m) => m.user_id === me)?.role ?? null
  })
  const isOwner = computed(() => myRole.value === 'owner')
  const canEditTasks = computed(() => myRole.value === 'owner' || myRole.value === 'responsible')

  const responsibleMember = computed<Member | null>(
    () =>
      members.value.find((m) => m.role === 'responsible') ??
      members.value.find((m) => m.role === 'owner') ??
      null,
  )

  async function open(id: number): Promise<void> {
    projectId.value = id
    loading.value = true
    try {
      const [detail, taskPage, ganttData, statsData] = await Promise.all([
        projectsApi.get(id),
        tasksApi.list(id, { limit: 200 }),
        analyticsApi.gantt(id),
        analyticsApi.stats(id),
      ])
      project.value = detail
      members.value = detail.members
      tasks.value = taskPage.items
      gantt.value = ganttData
      stats.value = statsData
    } finally {
      loading.value = false
    }
  }

  async function reloadProject(): Promise<void> {
    if (!projectId.value) return
    const detail = await projectsApi.get(projectId.value)
    project.value = detail
    members.value = detail.members
  }

  async function reloadMembers(): Promise<void> {
    if (!projectId.value) return
    members.value = await projectsApi.members(projectId.value)
  }

  async function reloadTasks(): Promise<void> {
    if (!projectId.value) return
    tasksLoading.value = true
    try {
      const page = await tasksApi.list(projectId.value, { limit: 200 })
      tasks.value = page.items
    } finally {
      tasksLoading.value = false
    }
  }

  async function reloadGantt(): Promise<void> {
    if (projectId.value) gantt.value = await analyticsApi.gantt(projectId.value)
  }

  async function reloadStats(): Promise<void> {
    if (projectId.value) stats.value = await analyticsApi.stats(projectId.value)
  }

  async function reloadTaskData(): Promise<void> {
    await Promise.all([reloadTasks(), reloadGantt(), reloadStats()])
  }

  let refreshTimer: ReturnType<typeof setTimeout> | null = null

  function scheduleRefresh(scope: 'tasks' | 'project' | 'all' = 'all', delay = 350): void {
    if (refreshTimer) clearTimeout(refreshTimer)
    refreshTimer = setTimeout(() => {
      refreshTimer = null
      const jobs: Promise<void>[] = []
      if (scope === 'tasks' || scope === 'all') jobs.push(reloadTaskData())
      if (scope === 'project' || scope === 'all') jobs.push(reloadProject())
      void Promise.all(jobs).catch(() => undefined)
    }, delay)
  }

  function reset(): void {
    if (refreshTimer) clearTimeout(refreshTimer)
    refreshTimer = null
    projectId.value = null
    project.value = null
    members.value = []
    tasks.value = []
    gantt.value = null
    stats.value = null
  }

  return {
    projectId,
    project,
    members,
    tasks,
    gantt,
    stats,
    loading,
    tasksLoading,
    myRole,
    isOwner,
    canEditTasks,
    responsibleMember,
    open,
    reloadProject,
    reloadMembers,
    reloadTasks,
    reloadGantt,
    reloadStats,
    reloadTaskData,
    scheduleRefresh,
    reset,
  }
})
