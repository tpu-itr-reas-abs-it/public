import type { DerivedTaskState, MemberRole, ProjectStatus, RiskLevel, TaskStatus } from '@/types/api'

export const STATUS_LABELS: Record<TaskStatus, string> = {
  planned: 'Запланирована',
  in_progress: 'В работе',
  done: 'Завершена',
  blocked: 'Заблокирована',
  cancelled: 'Отменена',
}

export const STATUS_OPTIONS = (Object.keys(STATUS_LABELS) as TaskStatus[]).map((value) => ({
  value,
  label: STATUS_LABELS[value],
}))

export const STATE_LABELS: Record<DerivedTaskState, string> = {
  upcoming: 'Предстоит',
  in_progress: 'В работе',
  done: 'Завершена',
  overdue: 'Просрочена',
  blocked: 'Заблокирована',
  cancelled: 'Отменена',
}

export const STATE_COLORS: Record<DerivedTaskState, string> = {
  upcoming: '#fca5a5',
  in_progress: '#dc2626',
  done: '#10b981',
  overdue: '#991b1b',
  blocked: '#f59e0b',
  cancelled: '#94a3b8',
}

export const STATE_FILTER_OPTIONS: { value: DerivedTaskState | 'all'; label: string }[] = [
  { value: 'all', label: 'Все' },
  { value: 'upcoming', label: 'Предстоят' },
  { value: 'in_progress', label: 'В работе' },
  { value: 'overdue', label: 'Просрочены' },
  { value: 'done', label: 'Завершены' },
  { value: 'blocked', label: 'Заблокированы' },
  { value: 'cancelled', label: 'Отменены' },
]

export const ROLE_LABELS: Record<MemberRole, string> = {
  owner: 'Владелец',
  responsible: 'Ответственный',
  viewer: 'Наблюдатель',
}

export const MEMBER_ROLE_OPTIONS: { value: MemberRole; label: string }[] = [
  { value: 'responsible', label: 'Ответственный' },
  { value: 'viewer', label: 'Наблюдатель' },
]

export const PROJECT_STATUS_LABELS: Record<ProjectStatus, string> = {
  active: 'Активен',
  completed: 'Завершён',
  archived: 'В архиве',
}

export const PROJECT_STATUS_OPTIONS = (Object.keys(PROJECT_STATUS_LABELS) as ProjectStatus[]).map(
  (value) => ({ value, label: PROJECT_STATUS_LABELS[value] }),
)

export const RISK_BADGE: Record<RiskLevel, string> = {
  ok: 'Сроки под контролем',
  warning: 'Есть риск срыва',
  critical: 'Критический риск',
}

export const RISK_TITLE: Record<RiskLevel, string> = {
  ok: 'Сроки проекта в порядке',
  warning: 'Обнаружен риск нарушения сроков',
  critical: 'Критическое отставание от графика',
}
