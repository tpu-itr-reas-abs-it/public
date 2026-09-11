<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import ProgressSpinner from 'primevue/progressspinner'
import { useConfirm } from 'primevue/useconfirm'
import { dependenciesApi, projectsApi, tasksApi, type ProjectUpdatePayload } from '@/api'
import { useAuthStore } from '@/stores/auth'
import { useProjectStore } from '@/stores/project'
import { useNotify } from '@/composables/useNotify'
import { useProjectSocket } from '@/composables/useProjectSocket'
import { downloadBlob, formatDate, pluralDays, pluralTasks, todayIso } from '@/utils/format'
import { STATE_COLORS, STATE_LABELS } from '@/utils/status'
import WorkspaceHeader from '@/components/workspace/WorkspaceHeader.vue'
import ProjectPanel from '@/components/workspace/ProjectPanel.vue'
import TaskList from '@/components/workspace/TaskList.vue'
import GanttChart from '@/components/gantt/GanttChart.vue'
import RiskBlock from '@/components/workspace/RiskBlock.vue'
import SiteFooter from '@/components/workspace/SiteFooter.vue'
import TaskDialog from '@/components/workspace/TaskDialog.vue'
import CommentsDialog from '@/components/workspace/CommentsDialog.vue'
import MembersDialog from '@/components/workspace/MembersDialog.vue'
import type { ImpactAnalysis, Task, TaskStatus, WsEvent } from '@/types/api'

const props = defineProps<{ projectId: number }>()

const router = useRouter()
const auth = useAuthStore()
const store = useProjectStore()
const { project, members, tasks, gantt, stats, loading, tasksLoading, isOwner, canEditTasks } =
  storeToRefs(store)
const notify = useNotify()
const confirm = useConfirm()

watch(
  () => props.projectId,
  async (id) => {
    try {
      await store.open(id)
    } catch (error) {
      notify.error(error, 'Не удалось открыть проект')
      await router.replace({ name: 'projects' })
    }
  },
  { immediate: true },
)

onBeforeUnmount(() => store.reset())

const hasBars = computed(() => (gantt.value?.tasks.length ?? 0) > 0)
const criticalIds = computed(() => gantt.value?.critical_path ?? [])

useProjectSocket(
  computed(() => store.projectId),
  (event: WsEvent) => {
    if (event.actor_id !== null && event.actor_id === auth.user?.id) return
    switch (event.type) {
      case 'project.updated':
      case 'member.added':
      case 'member.removed':
        store.scheduleRefresh('project')
        break
      case 'comment.created': {
        const taskId = event.payload.task_id
        if (typeof taskId === 'number' && taskId in commentCounts.value) {
          commentCounts.value[taskId] = (commentCounts.value[taskId] ?? 0) + 1
        }
        break
      }
      case 'notification.created':
        break
      default:
        store.scheduleRefresh('tasks')
    }
  },
)

async function updateProject(payload: ProjectUpdatePayload) {
  try {
    await projectsApi.update(props.projectId, payload)
    notify.success(payload.status ? 'Статус проекта обновлён' : 'Сроки проекта обновлены')
    await Promise.all([store.reloadProject(), store.reloadStats(), store.reloadGantt()])
  } catch (error) {
    notify.error(error, 'Не удалось сохранить изменения проекта')
    await store.reloadProject()
  }
}

async function setResponsible(memberId: number | null) {
  const previous = members.value.find((m) => m.role === 'responsible')
  const target = memberId ? members.value.find((m) => m.id === memberId) : null
  try {
    if (previous && previous.id !== memberId) {
      await projectsApi.updateMember(props.projectId, previous.id, 'viewer')
    }
    if (target && target.role !== 'owner' && target.role !== 'responsible') {
      await projectsApi.updateMember(props.projectId, target.id, 'responsible')
    }
    await store.reloadMembers()
    notify.success('Ответственный обновлён')
  } catch (error) {
    notify.error(error, 'Не удалось изменить ответственного')
    await store.reloadMembers()
  }
}

async function exportProject(format: 'json' | 'csv') {
  try {
    const blob = await projectsApi.exportBlob(props.projectId, format)
    downloadBlob(blob, `project-${props.projectId}-${todayIso()}.${format}`)
    notify.success(`Экспорт в ${format.toUpperCase()} готов`)
  } catch (error) {
    notify.error(error, 'Не удалось экспортировать проект')
  }
}

const commentCounts = ref<Record<number, number>>({})

const taskDialog = ref(false)
const editingTask = ref<Task | null>(null)

function openCreate() {
  editingTask.value = null
  taskDialog.value = true
}

function openEdit(task: Task) {
  editingTask.value = task
  taskDialog.value = true
}

function openEditById(taskId: number) {
  const task = tasks.value.find((t) => t.id === taskId)
  if (task && canEditTasks.value) openEdit(task)
}

async function changeStatus(task: Task, status: TaskStatus) {
  const previous = task.status
  task.status = status
  try {
    await tasksApi.update(task.id, { status })
    await store.reloadTaskData()
  } catch (error) {
    task.status = previous
    notify.error(error, 'Ошибка обновления статуса')
    await store.reloadTasks()
  }
}

function removeTask(task: Task) {
  confirm.require({
    header: 'Удаление задачи',
    message: `Удалить задачу «${task.title}»? Зависимые задачи останутся на своих датах.`,
    icon: 'pi pi-exclamation-triangle',
    acceptLabel: 'Удалить',
    rejectLabel: 'Отмена',
    acceptProps: { severity: 'danger' },
    rejectProps: { severity: 'secondary', outlined: true },
    accept: async () => {
      try {
        await tasksApi.remove(task.id)
        notify.success(`Задача «${task.title}» удалена`)
        await store.reloadTaskData()
      } catch (error) {
        notify.error(error, 'Ошибка удаления задачи')
      }
    },
  })
}

const commentsDialog = ref(false)
const commentsTask = ref<Task | null>(null)

function openComments(task: Task) {
  commentsTask.value = task
  commentsDialog.value = true
}

const membersDialog = ref(false)

function describeImpact(impact: ImpactAnalysis) {
  if (impact.affected_count > 0) {
    notify.info(`Каскадно сдвинуто: ${pluralTasks(impact.affected_count)}`)
  }
  if (impact.breaks_deadline) {
    notify.warn(
      `Проект выходит за дедлайн на ${pluralDays(impact.project_overrun_days)}. ` +
        `Прогноз окончания: ${formatDate(impact.projected_end_date)}`,
    )
  }
}

async function onShift({ taskId, shiftDays }: { taskId: number; shiftDays: number }) {
  try {
    const impact = await tasksApi.shift(taskId, { shift_days: shiftDays, cascade: true })
    describeImpact(impact)
    await store.reloadTaskData()
  } catch (error) {
    notify.error(error, 'Не удалось сдвинуть задачу')
    await store.reloadGantt()
  }
}

async function onResize({ taskId, endDate }: { taskId: number; endDate: string }) {
  try {
    const impact = await tasksApi.shift(taskId, { end_date: endDate, cascade: true })
    describeImpact(impact)
    await store.reloadTaskData()
  } catch (error) {
    notify.error(error, 'Не удалось изменить длительность')
    await store.reloadGantt()
  }
}

async function onLink({ predecessorId, successorId }: { predecessorId: number; successorId: number }) {
  try {
    const result = await dependenciesApi.create(successorId, { predecessor_id: predecessorId, reschedule: true })
    notify.success('Связь между задачами добавлена')
    if (result.impact) describeImpact(result.impact)
    await store.reloadTaskData()
  } catch (error) {
    notify.error(error, 'Не удалось создать связь')
  }
}

function onRemoveLink({ linkId, sourceId, targetId }: { linkId: number; sourceId: number; targetId: number }) {
  const from = tasks.value.find((t) => t.id === sourceId)?.title ?? `#${sourceId}`
  const to = tasks.value.find((t) => t.id === targetId)?.title ?? `#${targetId}`
  confirm.require({
    header: 'Удаление связи',
    message: `Удалить связь «${from}» → «${to}»? Даты задач не изменятся.`,
    icon: 'pi pi-link',
    acceptLabel: 'Удалить',
    rejectLabel: 'Отмена',
    acceptProps: { severity: 'danger' },
    rejectProps: { severity: 'secondary', outlined: true },
    accept: async () => {
      try {
        await dependenciesApi.remove(linkId)
        notify.success('Связь удалена')
        await store.reloadTaskData()
      } catch (error) {
        notify.error(error, 'Не удалось удалить связь')
      }
    },
  })
}
</script>

<template>
  <div class="workspace">
    <WorkspaceHeader
      :project="project"
      :user="auth.user"
      @projects="router.push({ name: 'projects' })"
      @create="router.push({ name: 'project-create' })"
      @export="exportProject"
    />

    <div class="container">
      <div v-if="loading && !project" class="loading">
        <ProgressSpinner style="width: 44px; height: 44px" stroke-width="4" />
        <p>Загружаем проект...</p>
      </div>

      <template v-else-if="project">
        <ProjectPanel
          :project="project"
          :stats="stats"
          :members="members"
          :responsible-id="store.responsibleMember?.id ?? null"
          :can-edit="isOwner"
          @update="updateProject"
          @responsible="setResponsible"
          @members="membersDialog = true"
        />

        <div class="workspace-grid">
          <TaskList
            :tasks="tasks"
            :loading="tasksLoading"
            :can-edit="canEditTasks"
            :comment-counts="commentCounts"
            :critical-ids="criticalIds"
            @create="openCreate"
            @edit="openEdit"
            @remove="removeTask"
            @comments="openComments"
            @status="changeStatus"
          />

          <section class="gantt-card">
            <div v-if="!hasBars" class="gantt-empty">
              <p class="gantt-empty-title">{{ canEditTasks ? 'Добавьте задачи слева' : 'В проекте пока нет задач' }}</p>
              <p class="gantt-empty-sub">Диаграмма построится автоматически</p>
            </div>

            <GanttChart
              v-else-if="gantt"
              :gantt="gantt"
              :readonly="!canEditTasks"
              @open="openEditById"
              @shift="onShift"
              @resize="onResize"
              @link="onLink"
              @remove-link="onRemoveLink"
            />

            <div v-if="hasBars" class="legend">
              <div v-for="(color, state) in STATE_COLORS" :key="state" class="legend-item">
                <span class="legend-swatch" :style="{ background: color }" />
                <span>{{ STATE_LABELS[state] }}</span>
              </div>
              <div class="legend-item">
                <span class="legend-swatch critical" />
                <span>Критический путь</span>
              </div>
              <div class="legend-item">
                <span class="legend-line violated" />
                <span>Связь нарушена</span>
              </div>
            </div>
          </section>
        </div>

        <RiskBlock v-if="stats" :stats="stats" />
      </template>

      <SiteFooter />
    </div>

    <TaskDialog
      v-model:visible="taskDialog"
      :project-id="projectId"
      :task="editingTask"
      :members="members"
      :tasks="tasks"
      @saved="store.reloadTaskData()"
    />

    <CommentsDialog
      v-model:visible="commentsDialog"
      :task="commentsTask"
      @count="(taskId, count) => (commentCounts[taskId] = count)"
    />

    <MembersDialog
      v-model:visible="membersDialog"
      :project-id="projectId"
      :members="members"
      :can-manage="isOwner"
      @changed="store.reloadMembers()"
    />
  </div>
</template>

<style scoped>
.workspace {
  height: 100vh;
  overflow-y: auto;
  overflow-x: hidden;
  color: #1e293b;
  background:
    repeating-linear-gradient(45deg, transparent, transparent 35px, rgba(239, 68, 68, 0.03) 35px, rgba(239, 68, 68, 0.03) 70px),
    linear-gradient(135deg, #fef2f2 0%, #fee2e2 50%, #fecaca 100%);
  background-attachment: fixed;
}

.container {
  max-width: 1280px;
  margin: 0 auto;
  padding: 32px 24px 80px;
}

.loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 80px 0;
  color: #64748b;
}

.workspace-grid {
  display: grid;
  grid-template-columns: minmax(340px, 3.4fr) 8.6fr;
  gap: 24px;
  align-items: start;
}

.gantt-card {
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 1px 2px rgba(0, 0, 0, .05);
  border: 1px solid #e2e8f0;
  overflow: hidden;
  min-width: 0;
}

.gantt-empty { text-align: center; padding: 80px 20px; background: #f8fafc; }
.gantt-empty-title { color: #64748b; font-weight: 500; }
.gantt-empty-sub { color: #94a3b8; font-size: 14px; margin-top: 4px; }

.legend {
  padding: 12px 20px;
  border-top: 1px solid #e2e8f0;
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  font-size: 12px;
  background: #f8fafc;
  color: #475569;
}
.legend-item { display: flex; align-items: center; gap: 6px; }
.legend-swatch { width: 12px; height: 12px; border-radius: 3px; }
.legend-swatch.critical { background: transparent; outline: 2px solid #7f1d1d; outline-offset: -1px; }
.legend-line { width: 18px; height: 0; border-top: 2px dashed #f59e0b; }

@media (max-width: 1024px) {
  .workspace-grid { grid-template-columns: 1fr; }
}
@media (max-width: 640px) {
  .container { padding: 16px 12px 60px; }
}
</style>
