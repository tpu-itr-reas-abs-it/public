<script setup lang="ts">
import { computed } from 'vue'
import { formatDate, pluralDays, pluralTasks } from '@/utils/format'
import { RISK_TITLE } from '@/utils/status'
import type { ProjectStats } from '@/types/api'

const props = defineProps<{ stats: ProjectStats }>()

const level = computed(() => props.stats.risk.level)
const icon = computed(() =>
  level.value === 'critical' ? 'pi-exclamation-circle' : level.value === 'warning' ? 'pi-exclamation-triangle' : 'pi-check-circle',
)
</script>

<template>
  <div class="risk-block" :class="level">
    <h4 class="risk-block-title">
      <i class="pi" :class="icon" />
      {{ RISK_TITLE[level] }}
    </h4>
    <ul>
      <li v-if="stats.risk.breaks_deadline">
        <strong>Проект выходит за дедлайн.</strong>
        Прогноз окончания: <strong>{{ formatDate(stats.risk.projected_end_date) }}</strong>,
        плановый дедлайн: {{ formatDate(stats.risk.deadline) }}.
        <span v-if="stats.risk.overrun_days > 0">Превышение на <strong>{{ pluralDays(stats.risk.overrun_days) }}</strong>.</span>
      </li>
      <li v-if="stats.overdue_count > 0">Просрочено: <strong>{{ pluralTasks(stats.overdue_count) }}</strong>.</li>
      <li v-for="reason in stats.risk.reasons" :key="reason">{{ reason }}</li>
      <li v-if="stats.days_left >= 0">До дедлайна осталось <strong>{{ pluralDays(stats.days_left) }}</strong>.</li>
      <li v-else>Дедлайн просрочен на <strong>{{ pluralDays(Math.abs(stats.days_left)) }}</strong>.</li>
      <li v-if="stats.critical_path_length">
        Критический путь: {{ pluralTasks(stats.critical_path_length) }}, {{ pluralDays(stats.critical_path_days) }}.
      </li>
    </ul>
  </div>
</template>

<style scoped>
.risk-block { border: 2px solid; border-radius: 12px; padding: 16px 20px; margin-top: 24px; }
.risk-block.ok { border-color: #86efac; background: linear-gradient(90deg, #f0fdf4, #dcfce7); }
.risk-block.warning { border-color: #fcd34d; background: linear-gradient(90deg, #fffbeb, #fef3c7); }
.risk-block.critical { border-color: #fca5a5; background: linear-gradient(90deg, #fef2f2, #fee2e2); }

.risk-block-title { font-weight: 700; font-size: 16px; margin-bottom: 8px; display: flex; align-items: center; gap: 8px; }
.risk-block-title .pi { font-size: 20px; }
.risk-block.ok .risk-block-title { color: #166534; }
.risk-block.warning .risk-block-title { color: #92400e; }
.risk-block.critical .risk-block-title { color: #991b1b; }

.risk-block ul { font-size: 14px; padding-left: 22px; margin: 0; }
.risk-block.ok ul { color: #166534; }
.risk-block.warning ul { color: #92400e; }
.risk-block.critical ul { color: #991b1b; }
.risk-block li { margin-bottom: 4px; }
</style>
