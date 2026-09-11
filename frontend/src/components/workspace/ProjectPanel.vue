<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import Button from 'primevue/button'
import Select from 'primevue/select'
import DatePicker from 'primevue/datepicker'
import type { ProjectUpdatePayload } from '@/api'
import { useNotify } from '@/composables/useNotify'
import { durationDays, pluralDays, shortName, toApiDate, toDate } from '@/utils/format'
import { PROJECT_STATUS_OPTIONS, RISK_BADGE, ROLE_LABELS } from '@/utils/status'
import type { Member, ProjectDetail, ProjectStats, ProjectStatus } from '@/types/api'

const props = defineProps<{
  project: ProjectDetail
  stats: ProjectStats | null
  members: Member[]
  responsibleId: number | null
  canEdit: boolean
}>()

const emit = defineEmits<{
  (e: 'update', payload: ProjectUpdatePayload): void
  (e: 'responsible', memberId: number | null): void
  (e: 'members'): void
}>()

const notify = useNotify()

const status = ref<ProjectStatus>(props.project.status)
const start = ref<Date | null>(toDate(props.project.start_date))
const end = ref<Date | null>(toDate(props.project.end_date))
const responsible = ref<number | null>(props.responsibleId)

watch(
  () => props.project,
  (p) => {
    status.value = p.status
    start.value = toDate(p.start_date)
    end.value = toDate(p.end_date)
  },
  { deep: true },
)
watch(() => props.responsibleId, (id) => (responsible.value = id))

const riskLevel = computed(() => props.stats?.risk.level ?? null)
const duration = computed(() => durationDays(props.project.start_date, props.project.end_date))

const memberOptions = computed(() =>
  props.members
    .filter((m) => m.user)
    .map((m) => ({
      value: m.id,
      label: `${shortName(m.user!.full_name || m.user!.email)} (${ROLE_LABELS[m.role]})`,
    })),
)

function onStatus(value: ProjectStatus) {
  emit('update', { status: value })
}

function onDates() {
  if (!start.value || !end.value) return
  const startIso = toApiDate(start.value)
  const endIso = toApiDate(end.value)
  if (startIso > endIso) {
    notify.warn('Дата начала не может быть позже даты окончания')
    start.value = toDate(props.project.start_date)
    end.value = toDate(props.project.end_date)
    return
  }
  if (startIso === props.project.start_date && endIso === props.project.end_date) return
  emit('update', { start_date: startIso, end_date: endIso })
}
</script>

<template>
  <section class="project-panel">
    <div class="panel-head">
      <div>
        <div class="title-row">
          <h2>{{ project.name }}</h2>
          <span v-if="riskLevel" class="risk-badge" :class="riskLevel">
            <span class="risk-dot" />
            {{ RISK_BADGE[riskLevel] }}
          </span>
        </div>
        <p class="panel-meta">
          <span class="meta-dot" />
          Продолжительность: <strong>{{ pluralDays(duration) }}</strong>
          <span v-if="stats" class="meta-progress">
            Прогресс: <strong>{{ stats.progress_percent ?? 0 }}%</strong>
          </span>
          <span v-if="stats && stats.critical_path_length" class="meta-progress">
            Критический путь: <strong>{{ pluralDays(stats.critical_path_days) }}</strong>
          </span>
        </p>
        <p v-if="project.description" class="panel-description">{{ project.description }}</p>
      </div>
    </div>

    <div class="project-toolbar">
      <div class="form-control">
        <label>Статус проекта</label>
        <Select
          v-model="status"
          :options="PROJECT_STATUS_OPTIONS"
          option-label="label"
          option-value="value"
          class="input-red input-sm"
          :disabled="!canEdit"
          @update:model-value="onStatus"
        />
      </div>

      <div class="form-control">
        <label>Дата начала</label>
        <DatePicker
          v-model="start"
          date-format="dd.mm.yy"
          class="input-red input-sm"
          :disabled="!canEdit"
          :max-date="end ?? undefined"
          @update:model-value="onDates"
        />
      </div>

      <div class="form-control">
        <label>Дата окончания</label>
        <DatePicker
          v-model="end"
          date-format="dd.mm.yy"
          class="input-red input-sm"
          :disabled="!canEdit"
          :min-date="start ?? undefined"
          @update:model-value="onDates"
        />
      </div>

      <div class="form-control">
        <label>Ответственный</label>
        <div class="input-with-btn">
          <Select
            v-model="responsible"
            :options="memberOptions"
            option-label="label"
            option-value="value"
            placeholder="— Не назначен —"
            class="input-red input-sm"
            show-clear
            :disabled="!canEdit"
            @update:model-value="emit('responsible', $event)"
          />
          <Button
            class="btn-gradient"
            size="small"
            :label="canEdit ? '+ Участник' : 'Участники'"
            :title="canEdit ? 'Добавить участников' : 'Список участников'"
            @click="emit('members')"
          />
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.project-panel {
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -2px rgba(0, 0, 0, 0.1);
  padding: 24px;
  margin-bottom: 24px;
  border: 1px solid #fee2e2;
}

.panel-head { display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; flex-wrap: wrap; }

.title-row { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
.title-row h2 { font-size: 24px; font-weight: 700; color: #0f172a; letter-spacing: -0.01em; }

.panel-meta {
  color: #475569;
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 8px;
  flex-wrap: wrap;
}
.panel-meta strong { color: #dc2626; }
.meta-dot { width: 8px; height: 8px; background: #ef4444; border-radius: 50%; flex-shrink: 0; }
.meta-progress { margin-left: 16px; color: #64748b; }
.panel-description { margin-top: 8px; color: #64748b; font-size: 14px; max-width: 800px; }

.risk-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 12px;
  border-radius: 100px;
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}
.risk-badge.ok { background: #dcfce7; color: #166534; }
.risk-badge.warning { background: #fef3c7; color: #92400e; }
.risk-badge.critical { background: #fee2e2; color: #991b1b; }
.risk-dot { width: 8px; height: 8px; border-radius: 50%; background: currentColor; }

.project-toolbar {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
  margin-top: 16px;
  align-items: end;
}

.form-control { min-width: 0; display: flex; flex-direction: column; gap: 4px; }
.form-control label {
  font-size: 11px;
  font-weight: 700;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.input-with-btn { display: flex; gap: 8px; align-items: stretch; min-width: 0; width: 100%; }
.input-with-btn > :first-child { flex: 1 1 0; min-width: 0; }
.input-with-btn .p-button { flex: 0 0 auto; white-space: nowrap; }
</style>
