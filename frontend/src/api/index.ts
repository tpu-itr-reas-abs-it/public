import { http } from './http'
import type {
  Comment,
  Dependency,
  DependencyType,
  DerivedTaskState,
  GanttResponse,
  ImpactAnalysis,
  Member,
  MemberRole,
  Page,
  Project,
  ProjectDetail,
  ProjectStats,
  ProjectSummary,
  Task,
  TaskCreate,
  TaskStatus,
  TaskUpdate,
  TaskUpdateResponse,
  TaskWithLinks,
  TokenPair,
  UserPublic,
  UserRead,
} from '@/types/api'

export const authApi = {
  register: (email: string, password: string, full_name: string) =>
    http.post<TokenPair>('/auth/register', { email, password, full_name }).then((r) => r.data),
  login: (email: string, password: string) =>
    http.post<TokenPair>('/auth/login', { email, password }).then((r) => r.data),
  me: () => http.get<UserRead>('/auth/me').then((r) => r.data),
}

export const usersApi = {
  search: (q: string, limit = 20) =>
    http.get<UserPublic[]>('/users', { params: { q, limit } }).then((r) => r.data),
}

export interface ProjectCreatePayload {
  name: string
  description?: string | null
  start_date: string
  end_date: string
}

export type ProjectUpdatePayload = Partial<
  Pick<Project, 'name' | 'description' | 'start_date' | 'end_date' | 'status'>
>

export const projectsApi = {
  list: (params: { limit?: number; offset?: number; search?: string } = {}) =>
    http.get<Page<ProjectSummary>>('/projects', { params }).then((r) => r.data),
  create: (payload: ProjectCreatePayload) =>
    http.post<Project>('/projects', payload).then((r) => r.data),
  get: (id: number) => http.get<ProjectDetail>(`/projects/${id}`).then((r) => r.data),
  update: (id: number, payload: ProjectUpdatePayload) =>
    http.patch<Project>(`/projects/${id}`, payload).then((r) => r.data),
  remove: (id: number) => http.delete<void>(`/projects/${id}`).then(() => undefined),

  members: (id: number) => http.get<Member[]>(`/projects/${id}/members`).then((r) => r.data),
  addMember: (id: number, payload: { user_id?: number; email?: string; role: MemberRole }) =>
    http.post<Member>(`/projects/${id}/members`, payload).then((r) => r.data),
  updateMember: (id: number, memberId: number, role: MemberRole) =>
    http.patch<Member>(`/projects/${id}/members/${memberId}`, { role }).then((r) => r.data),
  removeMember: (id: number, memberId: number) =>
    http.delete<void>(`/projects/${id}/members/${memberId}`).then(() => undefined),

  exportBlob: (id: number, format: 'json' | 'csv') =>
    http
      .get(`/projects/${id}/export`, { params: { format }, responseType: 'blob' })
      .then((r) => r.data as Blob),
}

export interface TaskListParams {
  limit?: number
  offset?: number
  status?: TaskStatus[]
  state?: DerivedTaskState[]
  assignee_id?: number
  search?: string
  start_from?: string
  end_to?: string
  order_by?: string
  order_dir?: 'asc' | 'desc'
}

export const tasksApi = {
  list: (projectId: number, params: TaskListParams = {}) =>
    http
      .get<Page<Task>>(`/projects/${projectId}/tasks`, {
        params,
        paramsSerializer: { indexes: null },
      })
      .then((r) => r.data),
  create: (projectId: number, payload: TaskCreate) =>
    http.post<Task>(`/projects/${projectId}/tasks`, payload).then((r) => r.data),
  get: (taskId: number) => http.get<TaskWithLinks>(`/tasks/${taskId}`).then((r) => r.data),
  update: (taskId: number, payload: TaskUpdate) =>
    http.patch<TaskUpdateResponse>(`/tasks/${taskId}`, payload).then((r) => r.data),
  remove: (taskId: number) => http.delete<void>(`/tasks/${taskId}`).then(() => undefined),

  previewImpact: (
    taskId: number,
    params: { start_date?: string; end_date?: string; shift_days?: number },
  ) => http.get<ImpactAnalysis>(`/tasks/${taskId}/impact`, { params }).then((r) => r.data),
  shift: (
    taskId: number,
    payload: { start_date?: string; end_date?: string; shift_days?: number; cascade?: boolean },
  ) => http.post<ImpactAnalysis>(`/tasks/${taskId}/shift`, payload).then((r) => r.data),

  comments: (taskId: number, params: { limit?: number; offset?: number } = {}) =>
    http.get<Page<Comment>>(`/tasks/${taskId}/comments`, { params }).then((r) => r.data),
  addComment: (taskId: number, text: string) =>
    http.post<Comment>(`/tasks/${taskId}/comments`, { text }).then((r) => r.data),
}

export const dependenciesApi = {
  list: (projectId: number) =>
    http.get<Dependency[]>(`/projects/${projectId}/dependencies`).then((r) => r.data),
  create: (
    successorId: number,
    payload: {
      predecessor_id: number
      type?: DependencyType
      lag_days?: number
      reschedule?: boolean
    },
  ) =>
    http
      .post<Dependency & { impact: ImpactAnalysis | null }>(
        `/tasks/${successorId}/dependencies`,
        payload,
      )
      .then((r) => r.data),
  remove: (dependencyId: number) =>
    http.delete<void>(`/dependencies/${dependencyId}`).then(() => undefined),
}

export const analyticsApi = {
  gantt: (projectId: number) =>
    http.get<GanttResponse>(`/projects/${projectId}/gantt`).then((r) => r.data),
  stats: (projectId: number) =>
    http.get<ProjectStats>(`/projects/${projectId}/stats`).then((r) => r.data),
}
