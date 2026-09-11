<script setup lang="ts">
import Select from 'primevue/select'
import Button from 'primevue/button'
import { formatDateShort, shortName } from '@/utils/format'
import { STATE_LABELS, STATUS_OPTIONS } from '@/utils/status'
import type { Task, TaskStatus } from '@/types/api'

defineProps<{ task: Task; canEdit: boolean; commentsCount?: number; critical?: boolean }>()
const emit = defineEmits<{
  (e: 'edit'): void
  (e: 'remove'): void
  (e: 'comments'): void
  (e: 'status', status: TaskStatus): void
}>()
</script>

<template>
  <div class="task-card" :class="{ critical }">
    <h4 class="task-title">
      <span class="task-id">{{ task.id }}</span>
      <span class="truncate" :title="task.title">{{ task.title }}</span>
      <i v-if="critical" class="pi pi-bolt critical-mark" title="Критический путь" />
    </h4>

    <div class="task-meta">
      <span class="state-badge" :class="task.state">{{ STATE_LABELS[task.state] }}</span>
      <span class="task-line" :title="task.assignee?.full_name || ''">
        <i class="pi pi-user" />
        <span class="truncate">{{ shortName(task.assignee?.full_name || task.assignee?.email) || 'Не назначен' }}</span>
      </span>
    </div>

    <div class="task-line dates">
      <i class="pi pi-calendar" />
      <span class="truncate">
        {{ formatDateShort(task.start_date) }} — {{ formatDateShort(task.end_date) }}
        <span class="muted">· {{ task.duration_days }} дн.</span>
        <span v-if="task.progress_percent" class="muted">· {{ task.progress_percent }}%</span>
      </span>
    </div>

    <div class="task-actions">
      <Select
        :model-value="task.status"
        :options="STATUS_OPTIONS"
        option-label="label"
        option-value="value"
        class="status-select input-sm"
        :disabled="!canEdit"
        @update:model-value="emit('status', $event)"
      />

      <button
        type="button"
        class="task-comments-btn"
        :class="{ 'has-comments': (commentsCount ?? 0) > 0 }"
        :title="commentsCount === undefined ? 'Комментарии' : `Комментарии (${commentsCount})`"
        @click="emit('comments')"
      >
        <i class="pi pi-comment" />
        <span v-if="commentsCount !== undefined">{{ commentsCount }}</span>
      </button>

      <Button
        v-if="canEdit"
        icon="pi pi-pencil"
        text
        rounded
        size="small"
        class="icon-btn edit"
        title="Редактировать"
        @click="emit('edit')"
      />
      <Button
        v-if="canEdit"
        icon="pi pi-trash"
        text
        rounded
        size="small"
        severity="danger"
        class="icon-btn"
        title="Удалить"
        @click="emit('remove')"
      />
    </div>
  </div>
</template>

<style scoped>
.task-card {
  background: #f8fafc;
  border-radius: 8px;
  padding: 14px;
  border: 1px solid #e2e8f0;
  transition: all .2s;
}
.task-card:hover { background: #fff; border-color: #cbd5e1; box-shadow: 0 1px 3px rgba(0, 0, 0, .06); }
.task-card.critical { border-left: 3px solid #991b1b; }

.task-meta { display: flex; align-items: center; gap: 8px; margin-top: 8px; min-width: 0; }
.task-meta .task-line { flex: 1; }

.task-title {
  font-weight: 600;
  color: #1e293b;
  font-size: 14px;
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}
.task-id {
  flex-shrink: 0;
  min-width: 20px;
  height: 20px;
  padding: 0 4px;
  background: #e2e8f0;
  color: #475569;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 10px;
  font-weight: 700;
}
.critical-mark { color: #991b1b; font-size: 11px; flex-shrink: 0; }

.task-line { display: flex; align-items: center; gap: 6px; font-size: 12px; color: #64748b; min-width: 0; }
.task-line.dates { margin-top: 6px; }
.task-line .pi { font-size: 12px; color: #94a3b8; flex-shrink: 0; }
.task-line .muted { color: #94a3b8; }

.state-badge {
  flex-shrink: 0;
  padding: 2px 8px;
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  border-radius: 6px;
  box-shadow: 0 1px 2px rgba(0, 0, 0, .08);
  background: #e2e8f0;
  color: #1e293b;
}
.state-badge.upcoming { background: #fecaca; color: #991b1b; }
.state-badge.in_progress { background: #ef4444; color: #fff; }
.state-badge.done { background: #22c55e; color: #fff; }
.state-badge.blocked { background: #f59e0b; color: #fff; }
.state-badge.cancelled { background: #94a3b8; color: #fff; }
.state-badge.overdue { background: #b91c1c; color: #fff; }

.task-actions {
  display: flex;
  align-items: center;
  gap: 4px;
  padding-top: 10px;
  margin-top: 10px;
  border-top: 1px solid #e2e8f0;
}
.status-select { flex: 1; min-width: 0; margin-right: 2px; }
.status-select :deep(.p-select-label) { font-size: 12px; padding: 5px 8px; }
.status-select :deep(.p-select-dropdown) { width: 1.6rem; }

.task-comments-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 0 8px;
  font-size: 11px;
  font-weight: 600;
  color: #475569;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  cursor: pointer;
  transition: all .15s;
  flex-shrink: 0;
  height: 28px;
}
.task-comments-btn .pi { font-size: 12px; }
.task-comments-btn:hover { border-color: #cbd5e1; color: #0f172a; background: #f8fafc; }
.task-comments-btn.has-comments { color: #c64747; border-color: #fca5a5; background: #fef2f2; }

.icon-btn { width: 28px; height: 28px; flex-shrink: 0; color: #94a3b8; }
.icon-btn.edit:hover { color: #2563eb; background: #eff6ff; }
</style>
