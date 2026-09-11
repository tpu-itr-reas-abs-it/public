
export type TaskStatus = 'planned' | 'in_progress' | 'done' | 'blocked' | 'cancelled'
export type DerivedTaskState =
  | 'upcoming'
  | 'in_progress'
  | 'done'
  | 'overdue'
  | 'blocked'
  | 'cancelled'
export type ProjectStatus = 'active' | 'completed' | 'archived'
export type MemberRole = 'owner' | 'responsible' | 'viewer'
export type DependencyType = 'finish_to_start'
export type RiskLevel = 'ok' | 'warning' | 'critical'

export interface Page<T> {
  items: T[]
  total: number
  limit: number
  offset: number
}

export interface ApiError {
  error: { code: string; message: string; details: Record<string, unknown> }
}

export interface UserPublic {
  id: number
  email: string
  full_name: string
}

export interface UserRead extends UserPublic {
  is_active: boolean
  created_at: string
}

export interface TokenPair {
  access_token: string
  refresh_token: string
  token_type: string
}

export interface Project {
  id: number
  name: string
  description: string | null
  start_date: string
  end_date: string
  owner_id: number
  status: ProjectStatus
  created_at: string
  updated_at: string
}

export interface ProjectSummary extends Project {
  task_count: number
  done_count: number
  overdue_count: number
  progress_percent: number
  my_role: MemberRole | null
}

export interface Member {
  id: number
  project_id: number
  user_id: number
  role: MemberRole
  created_at: string
  user: UserPublic | null
}

export interface ProjectDetail extends Project {
  members: Member[]
}

export interface Task {
  id: number
  project_id: number
  title: string
  description: string | null
  start_date: string
  end_date: string
  duration_days: number
  status: TaskStatus
  state: DerivedTaskState
  is_overdue: boolean
  days_overdue: number
  assignee_id: number | null
  assignee: UserPublic | null
  progress_percent: number
  created_at: string
  updated_at: string
}

export interface TaskWithLinks extends Task {
  predecessor_ids: number[]
  successor_ids: number[]
}

export interface TaskCreate {
  title: string
  description?: string | null
  start_date: string
  end_date: string
  status?: TaskStatus
  assignee_id?: number | null
  progress_percent?: number
  predecessor_ids?: number[]
}

export interface TaskUpdate {
  title?: string
  description?: string | null
  start_date?: string
  end_date?: string
  status?: TaskStatus
  assignee_id?: number | null
  progress_percent?: number
  cascade?: boolean
}

export interface AffectedTask {
  task_id: number
  title: string
  old_start_date: string
  old_end_date: string
  new_start_date: string
  new_end_date: string
  shift_days: number
  is_critical: boolean
}

export interface ImpactAnalysis {
  task_id: number
  affected_tasks: AffectedTask[]
  affected_count: number
  project_end_date: string
  projected_end_date: string
  project_overrun_days: number
  breaks_deadline: boolean
  applied: boolean
}

export interface TaskUpdateResponse extends Task {
  impact: ImpactAnalysis | null
}

export interface Dependency {
  id: number
  project_id: number
  predecessor_id: number
  successor_id: number
  type: DependencyType
  lag_days: number
  created_at: string
}

export interface DependencyLink {
  id: number
  source: number
  target: number
  type: DependencyType
  lag_days: number
  is_critical: boolean
  violated: boolean
  violation_days: number
  note: string | null
}

export interface GanttBar {
  id: number
  title: string
  start_date: string
  end_date: string
  duration_days: number
  status: TaskStatus
  state: DerivedTaskState
  progress_percent: number
  assignee: UserPublic | null
  is_critical: boolean
  slack_days: number
  earliest_start: string
  earliest_finish: string
  latest_start: string
  latest_finish: string
  predecessor_ids: number[]
  successor_ids: number[]
  depth: number
}

export interface GanttTimeline {
  project_start: string
  project_end: string
  chart_start: string
  chart_end: string
  total_days: number
  today: string
}

export interface GanttResponse {
  project_id: number
  project_name: string
  timeline: GanttTimeline
  tasks: GanttBar[]
  links: DependencyLink[]
  critical_path: number[]
  generated_at: string
}

export interface RiskAssessment {
  level: RiskLevel
  breaks_deadline: boolean
  projected_end_date: string
  deadline: string
  overrun_days: number
  overdue_task_count: number
  reasons: string[]
}

export interface ProjectStats {
  project_id: number
  task_count: number
  progress_percent: number
  status_counts: Record<TaskStatus, number>
  state_counts: Record<DerivedTaskState, number>
  done_count: number
  in_progress_count: number
  overdue_count: number
  upcoming_count: number
  critical_path_length: number
  critical_path_days: number
  days_left: number
  risk: RiskAssessment
}

export interface Comment {
  id: number
  task_id: number
  user_id: number
  text: string
  created_at: string
  author: UserPublic | null
}

export interface WsEvent {
  type: string
  project_id: number
  actor_id: number | null
  payload: Record<string, unknown>
  ts: string
}
