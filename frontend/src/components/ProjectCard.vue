<script setup lang="ts">
import { formatDate } from '@/utils/format'
import { PROJECT_STATUS_LABELS, ROLE_LABELS } from '@/utils/status'
import type { ProjectSummary } from '@/types/api'

defineProps<{ project: ProjectSummary; canDelete: boolean }>()
const emit = defineEmits<{ (e: 'open'): void; (e: 'remove'): void }>()
</script>

<template>
  <div class="project-card" role="button" tabindex="0" @click="emit('open')" @keyup.enter="emit('open')">
    <button
      v-if="canDelete"
      type="button"
      class="project-card-delete"
      title="Удалить проект"
      @click.stop="emit('remove')"
    >
      <i class="pi pi-trash" />
    </button>

    <div class="project-card-title">{{ project.name }}</div>

    <div class="project-card-dates">
      <i class="pi pi-calendar" /> {{ formatDate(project.start_date) }} — {{ formatDate(project.end_date) }}
    </div>

    <div class="project-card-progress">
      <div class="project-card-progress-bar" :style="{ width: `${project.progress_percent || 0}%` }" />
    </div>

    <div class="project-card-meta">
      <span>Задач: <strong>{{ project.task_count ?? 0 }}</strong></span>
      <span>Готово: <strong>{{ project.done_count ?? 0 }}</strong></span>
      <span v-if="project.overdue_count" class="project-card-badge overdue">
        Просрочено {{ project.overdue_count }}
      </span>
      <span v-else-if="project.progress_percent === 100" class="project-card-badge done">Готов</span>
    </div>

    <div class="project-card-bottom">
      <span class="project-status-badge" :class="`project-status-${project.status || 'active'}`">
        {{ PROJECT_STATUS_LABELS[project.status] ?? 'Активен' }}
      </span>
      <span v-if="project.my_role" class="project-card-owner" :title="`Ваша роль: ${ROLE_LABELS[project.my_role]}`">
        <i class="pi pi-user" />
        <span>{{ ROLE_LABELS[project.my_role] }}</span>
      </span>
    </div>
  </div>
</template>

<style scoped>
.project-card {
  position: relative;
  background: #fff;
  border: 1px solid #E0E0E0;
  border-radius: 12px;
  padding: 20px;
  cursor: pointer;
  transition: all .2s;
  box-shadow: 0 2px 4px rgba(0, 0, 0, .03);
  display: flex;
  flex-direction: column;
  gap: 12px;
  overflow: hidden;
  outline: none;
}

.project-card:hover,
.project-card:focus-visible {
  border-color: var(--primary);
  transform: translateY(-2px);
  box-shadow: 0 8px 20px rgba(198, 71, 71, 0.12);
}

.project-card-title {
  font-size: 17px;
  font-weight: 600;
  color: var(--text);
  line-height: 1.3;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  padding-right: 32px;
}

.project-card-dates {
  font-size: 13px;
  color: var(--text-light);
  display: flex;
  align-items: center;
  gap: 6px;
}
.project-card-dates .pi { font-size: 12px; color: var(--primary); }

.project-card-meta {
  display: flex;
  gap: 16px;
  font-size: 12px;
  color: var(--text-light);
  margin-top: auto;
  align-items: center;
  flex-wrap: wrap;
}
.project-card-meta strong { color: var(--primary); }

.project-card-progress {
  height: 6px;
  background: #F1F1F1;
  border-radius: 3px;
  overflow: hidden;
}
.project-card-progress-bar {
  height: 100%;
  background: linear-gradient(90deg, var(--primary-dark), var(--primary));
  border-radius: 3px;
  transition: width .3s;
}

.project-card-badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 10px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
.project-card-badge.overdue { background: #fee2e2; color: #991b1b; }
.project-card-badge.done { background: #d1fae5; color: #065f46; }

.project-card-delete {
  position: absolute;
  top: 12px;
  right: 12px;
  width: 30px;
  height: 30px;
  border-radius: 8px;
  border: none;
  background: transparent;
  color: #B0B0B0;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all .15s;
  z-index: 2;
}
.project-card-delete:hover { background: rgba(244, 67, 54, 0.1); color: var(--red); }

.project-card-bottom {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding-top: 10px;
  border-top: 1px solid #F1F1F1;
  font-size: 12px;
  color: var(--text-light);
  min-width: 0;
}

.project-status-badge {
  display: inline-block;
  padding: 3px 10px;
  border-radius: 100px;
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  flex-shrink: 0;
}
.project-status-active { background: #dcfce7; color: #166534; }
.project-status-completed { background: #dbeafe; color: #1e40af; }
.project-status-archived { background: #e2e8f0; color: #475569; }

.project-card-owner {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-weight: 500;
  color: #475569;
  min-width: 0;
  max-width: 60%;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}
.project-card-owner .pi { font-size: 11px; }
.project-card-owner > span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
</style>
