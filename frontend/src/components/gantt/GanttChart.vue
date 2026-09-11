<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import Button from 'primevue/button'
import SelectButton from 'primevue/selectbutton'
import { addDays, dayjs, formatDate, formatDateShort, initials, pluralDays } from '@/utils/format'
import { STATE_COLORS, STATE_LABELS } from '@/utils/status'
import type { GanttBar, GanttResponse } from '@/types/api'
import type { ZoomLevel } from '@/types/ui'

const props = withDefaults(defineProps<{ gantt: GanttResponse; readonly?: boolean }>(), {
  readonly: false,
})

const emit = defineEmits<{
  (e: 'open', taskId: number): void
  (e: 'shift', payload: { taskId: number; shiftDays: number }): void
  (e: 'resize', payload: { taskId: number; endDate: string }): void
  (e: 'link', payload: { predecessorId: number; successorId: number }): void
  (e: 'remove-link', payload: { linkId: number; sourceId: number; targetId: number }): void
}>()

const ROW_HEIGHT = 40
const BAR_HEIGHT = 24
const SIDEBAR = 320
const HEADER = 52

const ZOOM_OPTIONS: { value: ZoomLevel; label: string }[] = [
  { value: 'day', label: 'День' },
  { value: 'week', label: 'Неделя' },
  { value: 'month', label: 'Месяц' },
]
const DAY_WIDTHS: Record<ZoomLevel, number> = { day: 36, week: 14, month: 6 }

const zoom = ref<ZoomLevel>('day')
const dayWidth = computed(() => DAY_WIDTHS[zoom.value])

const scroller = ref<HTMLElement | null>(null)

const timeline = computed(() => props.gantt.timeline)
const tasks = computed(() => props.gantt.tasks)
const totalDays = computed(() => Math.max(1, timeline.value.total_days))
const timelineWidth = computed(() => totalDays.value * dayWidth.value)
const bodyHeight = computed(() => Math.max(tasks.value.length, 1) * ROW_HEIGHT)

function dayOffset(iso: string): number {
  return dayjs(iso).diff(dayjs(timeline.value.chart_start), 'day')
}

function xOf(iso: string): number {
  return dayOffset(iso) * dayWidth.value
}

interface DayCell {
  iso: string
  label: string
  weekend: boolean
  today: boolean
  first: boolean
  monday: boolean
  x: number
}

const days = computed<DayCell[]>(() => {
  const start = dayjs(timeline.value.chart_start)
  const today = timeline.value.today
  return Array.from({ length: totalDays.value }, (_, index) => {
    const day = start.add(index, 'day')
    const weekday = day.day()
    const iso = day.format('YYYY-MM-DD')
    return {
      iso,
      label: day.format('D'),
      weekend: weekday === 0 || weekday === 6,
      today: iso === today,
      first: day.date() === 1,
      monday: weekday === 1,
      x: index * dayWidth.value,
    }
  })
})

const months = computed(() => {
  const groups: { key: string; label: string; x: number; width: number }[] = []
  for (const day of days.value) {
    const key = day.iso.slice(0, 7)
    const last = groups.at(-1)
    if (last && last.key === key) last.width += dayWidth.value
    else groups.push({ key, label: dayjs(day.iso).format('MMMM YYYY'), x: day.x, width: dayWidth.value })
  }
  return groups
})

const weeks = computed(() => {
  const cells: { iso: string; label: string; x: number; width: number }[] = []
  for (const day of days.value) {
    const last = cells.at(-1)
    if (day.monday || !last) cells.push({ iso: day.iso, label: formatDateShort(day.iso), x: day.x, width: dayWidth.value })
    else last.width += dayWidth.value
  }
  return cells
})

const showDays = computed(() => dayWidth.value >= 20)
const showWeeks = computed(() => !showDays.value && dayWidth.value >= 8)

const todayX = computed(() => {
  const offset = dayOffset(timeline.value.today)
  if (offset < 0 || offset >= totalDays.value) return null
  return offset * dayWidth.value + dayWidth.value / 2
})

const projectRange = computed(() => ({
  left: xOf(timeline.value.project_start),
  width: Math.max(dayWidth.value, (dayOffset(timeline.value.project_end) - dayOffset(timeline.value.project_start) + 1) * dayWidth.value),
}))

interface BarBox {
  task: GanttBar
  index: number
  left: number
  width: number
  top: number
  color: string
  lightBar: boolean
}

const bars = computed<BarBox[]>(() =>
  tasks.value.map((task, index) => ({
    task,
    index,
    left: xOf(task.start_date),
    width: Math.max(dayWidth.value * task.duration_days, 6),
    top: index * ROW_HEIGHT + (ROW_HEIGHT - BAR_HEIGHT) / 2,
    color: STATE_COLORS[task.state],
    lightBar: task.state === 'upcoming',
  })),
)

const barById = computed(() => {
  const map = new Map<number, BarBox>()
  for (const bar of bars.value) map.set(bar.task.id, bar)
  return map
})

interface LinkPath {
  id: number
  source: number
  target: number
  d: string
  critical: boolean
  violated: boolean
  note: string | null
}

function buildPath(from: BarBox, to: BarBox): string {
  const x1 = from.left + from.width
  const y1 = from.top + BAR_HEIGHT / 2
  const x2 = to.left
  const y2 = to.top + BAR_HEIGHT / 2
  const stub = 10
  const arrowGap = 7

  if (x2 - x1 >= stub + arrowGap) {
    return `M ${x1} ${y1} H ${x1 + stub} V ${y2} H ${x2 - arrowGap}`
  }

  const downY = (from.index < to.index ? from.top + ROW_HEIGHT : from.top - ROW_HEIGHT / 2) + BAR_HEIGHT / 2
  const backX = x2 - stub - arrowGap
  return `M ${x1} ${y1} H ${x1 + stub} V ${downY} H ${backX} V ${y2} H ${x2 - arrowGap}`
}

const links = computed<LinkPath[]>(() => {
  const result: LinkPath[] = []
  for (const link of props.gantt.links) {
    const from = barById.value.get(link.source)
    const to = barById.value.get(link.target)
    if (!from || !to) continue
    result.push({
      id: link.id,
      source: link.source,
      target: link.target,
      d: buildPath(from, to),
      critical: link.is_critical,
      violated: link.violated,
      note: link.note,
    })
  }
  return result
})

const DRAG_THRESHOLD_PX = 5

const drag = ref<{ taskId: number; deltaDays: number; active: boolean } | null>(null)

function onBarPointerDown(event: PointerEvent, bar: BarBox) {
  if (props.readonly || event.button !== 0) return
  const startX = event.clientX
  drag.value = { taskId: bar.task.id, deltaDays: 0, active: false }

  const move = (moveEvent: PointerEvent) => {
    if (!drag.value) return
    const dx = moveEvent.clientX - startX
    if (!drag.value.active && Math.abs(dx) < DRAG_THRESHOLD_PX) return
    drag.value.active = true
    drag.value.deltaDays = Math.round(dx / dayWidth.value)
  }

  const up = () => {
    window.removeEventListener('pointermove', move)
    window.removeEventListener('pointerup', up)
    const current = drag.value
    drag.value = null
    if (current?.active && current.deltaDays !== 0) {
      emit('shift', { taskId: current.taskId, shiftDays: current.deltaDays })
    }
  }

  window.addEventListener('pointermove', move)
  window.addEventListener('pointerup', up)
}

function dragOffset(bar: BarBox): number {
  const current = drag.value
  if (!current?.active || current.taskId !== bar.task.id) return 0
  return current.deltaDays * dayWidth.value
}

const resize = ref<{ taskId: number; deltaDays: number } | null>(null)

function onResizePointerDown(event: PointerEvent, bar: BarBox) {
  if (props.readonly || event.button !== 0) return
  event.stopPropagation()
  const startX = event.clientX
  const minDelta = 1 - bar.task.duration_days
  resize.value = { taskId: bar.task.id, deltaDays: 0 }

  const move = (moveEvent: PointerEvent) => {
    if (!resize.value) return
    resize.value.deltaDays = Math.max(minDelta, Math.round((moveEvent.clientX - startX) / dayWidth.value))
  }

  const up = () => {
    window.removeEventListener('pointermove', move)
    window.removeEventListener('pointerup', up)
    const current = resize.value
    resize.value = null
    if (current && current.deltaDays !== 0) {
      emit('resize', { taskId: current.taskId, endDate: addDays(bar.task.end_date, current.deltaDays) })
    }
  }

  window.addEventListener('pointermove', move)
  window.addEventListener('pointerup', up)
}

function resizeExtra(bar: BarBox): number {
  const current = resize.value
  if (!current || current.taskId !== bar.task.id) return 0
  return current.deltaDays * dayWidth.value
}

const linking = ref<{ fromId: number; x: number; y: number } | null>(null)
const linkTargetId = ref<number | null>(null)
const canvas = ref<HTMLElement | null>(null)

function onHandlePointerDown(event: PointerEvent, bar: BarBox) {
  if (props.readonly || event.button !== 0) return
  event.stopPropagation()
  linking.value = { fromId: bar.task.id, x: bar.left + bar.width, y: bar.top + BAR_HEIGHT / 2 }

  const move = (moveEvent: PointerEvent) => {
    if (!linking.value || !canvas.value) return
    const rect = canvas.value.getBoundingClientRect()
    linking.value.x = moveEvent.clientX - rect.left
    linking.value.y = moveEvent.clientY - rect.top
    const index = Math.floor(linking.value.y / ROW_HEIGHT)
    const target = tasks.value[index]
    linkTargetId.value = target && target.id !== bar.task.id ? target.id : null
  }

  const up = () => {
    window.removeEventListener('pointermove', move)
    window.removeEventListener('pointerup', up)
    const target = linkTargetId.value
    linking.value = null
    linkTargetId.value = null
    if (target) emit('link', { predecessorId: bar.task.id, successorId: target })
  }

  window.addEventListener('pointermove', move)
  window.addEventListener('pointerup', up)
}

const linkPreviewPath = computed(() => {
  if (!linking.value) return null
  const from = barById.value.get(linking.value.fromId)
  if (!from) return null
  const x1 = from.left + from.width
  const y1 = from.top + BAR_HEIGHT / 2
  return `M ${x1} ${y1} C ${x1 + 40} ${y1}, ${linking.value.x - 40} ${linking.value.y}, ${linking.value.x} ${linking.value.y}`
})

function scrollToToday() {
  const element = scroller.value
  if (!element || todayX.value === null) return
  element.scrollTo({
    left: Math.max(0, todayX.value - (element.clientWidth - SIDEBAR) / 2),
    behavior: 'smooth',
  })
}

const centered = ref(false)
watch(
  () => props.gantt.generated_at,
  async () => {
    if (centered.value) return
    centered.value = true
    await nextTick()
    scrollToToday()
  },
  { immediate: true },
)

watch(zoom, async () => {
  await nextTick()
  scrollToToday()
})

const hoveredId = ref<number | null>(null)
</script>

<template>
  <div class="gantt">
    <div class="gantt-toolbar">
      <span class="toolbar-hint">
        <template v-if="!readonly">Тяните полосу — сдвиг, правый край — длительность, точку справа — связь.</template>
        <template v-else>Режим просмотра.</template>
      </span>
      <span class="spacer" />
      <SelectButton
        v-model="zoom"
        :options="ZOOM_OPTIONS"
        option-label="label"
        option-value="value"
        :allow-empty="false"
        size="small"
      />
      <Button text size="small" icon="pi pi-crosshairs" label="Сегодня" :disabled="todayX === null" @click="scrollToToday" />
    </div>

    <div ref="scroller" class="gantt-scroller">
      <div class="gantt-grid" :style="{ width: `${SIDEBAR + timelineWidth}px` }">
        <div class="gantt-header" :style="{ height: `${HEADER}px` }">
          <div class="header-sidebar" :style="{ width: `${SIDEBAR}px` }">
            <div class="col-title">Название</div>
            <div class="col-start">Начало</div>
            <div class="col-dur">Длит.</div>
          </div>
          <div class="header-timeline" :style="{ width: `${timelineWidth}px` }">
            <div class="months">
              <div
                v-for="month in months"
                :key="month.key"
                class="month"
                :style="{ left: `${month.x}px`, width: `${month.width}px` }"
              >
                <span class="month-label" :style="{ left: `${SIDEBAR + 6}px` }">{{ month.label }}</span>
              </div>
            </div>
            <div class="days">
              <template v-if="showDays">
                <div
                  v-for="day in days"
                  :key="day.iso"
                  class="day"
                  :class="{ weekend: day.weekend, today: day.today, 'month-start': day.first }"
                  :style="{ left: `${day.x}px`, width: `${dayWidth}px` }"
                >
                  {{ day.label }}
                </div>
              </template>
              <template v-else-if="showWeeks">
                <div
                  v-for="week in weeks"
                  :key="week.iso"
                  class="week"
                  :style="{ left: `${week.x}px`, width: `${week.width}px` }"
                >
                  {{ week.label }}
                </div>
              </template>
            </div>
          </div>
        </div>

        <div class="gantt-body" :style="{ height: `${bodyHeight}px` }">
          <div class="body-sidebar" :style="{ width: `${SIDEBAR}px` }">
            <div
              v-for="bar in bars"
              :key="bar.task.id"
              class="side-row"
              :class="{ hovered: bar.task.id === hoveredId, critical: bar.task.is_critical }"
              :style="{ height: `${ROW_HEIGHT}px` }"
              :title="`${bar.task.title} — двойной клик: открыть`"
              @mouseenter="hoveredId = bar.task.id"
              @mouseleave="hoveredId = null"
              @dblclick="emit('open', bar.task.id)"
            >
              <div class="col-title side-title">
                <i class="state-dot" :style="{ background: bar.color }" />
                <span class="truncate">{{ bar.task.title }}</span>
                <i v-if="bar.task.is_critical" class="pi pi-bolt critical-mark" title="Критический путь" />
              </div>
              <div class="col-start">{{ formatDateShort(bar.task.start_date) }}</div>
              <div class="col-dur">{{ bar.task.duration_days }}</div>
            </div>
          </div>

          <div ref="canvas" class="gantt-canvas" :style="{ width: `${timelineWidth}px` }">
            <div class="grid-layer">
              <div
                class="project-window"
                :style="{ left: `${projectRange.left}px`, width: `${projectRange.width}px` }"
              />
              <template v-if="dayWidth >= 8">
                <div
                  v-for="day in days"
                  :key="day.iso"
                  class="grid-col"
                  :class="{ weekend: day.weekend, 'month-start': day.first }"
                  :style="{ left: `${day.x}px`, width: `${dayWidth}px` }"
                />
              </template>
              <template v-else>
                <div
                  v-for="month in months"
                  :key="month.key"
                  class="grid-col month-start"
                  :style="{ left: `${month.x}px`, width: `${month.width}px` }"
                />
              </template>
            </div>

            <div class="row-lines">
              <div
                v-for="bar in bars"
                :key="`line-${bar.task.id}`"
                class="row-line"
                :class="{ hovered: bar.task.id === hoveredId }"
                :style="{ top: `${bar.index * ROW_HEIGHT}px`, height: `${ROW_HEIGHT}px` }"
              />
            </div>

            <div v-if="todayX !== null" class="today-line" :style="{ left: `${todayX}px` }">
              <span class="today-label">сегодня</span>
            </div>

            <svg class="links-layer" :width="timelineWidth" :height="bodyHeight">
              <defs>
                <marker id="gantt-arrow" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
                  <path d="M 0 0 L 8 4 L 0 8 z" fill="currentColor" />
                </marker>
              </defs>
              <g v-for="link in links" :key="link.id" class="link-group" :class="{ critical: link.critical, violated: link.violated }">
                <path :d="link.d" class="link" marker-end="url(#gantt-arrow)" />
                <path
                  v-if="!readonly"
                  :d="link.d"
                  class="link-hit"
                  @click="emit('remove-link', { linkId: link.id, sourceId: link.source, targetId: link.target })"
                >
                  <title>{{ link.note ?? 'Связь finish-to-start' }} — клик: удалить связь</title>
                </path>
                <title v-else-if="link.note">{{ link.note }}</title>
              </g>
              <path v-if="linkPreviewPath" :d="linkPreviewPath" class="link-preview" />
            </svg>

            <div
              v-for="bar in bars"
              :key="bar.task.id"
              class="bar"
              :class="{
                critical: bar.task.is_critical,
                light: bar.lightBar,
                dragging: drag?.active && drag.taskId === bar.task.id,
                resizing: resize?.taskId === bar.task.id,
                'link-target': linkTargetId === bar.task.id,
                readonly,
              }"
              :style="{
                left: `${bar.left + dragOffset(bar)}px`,
                top: `${bar.top}px`,
                width: `${bar.width + resizeExtra(bar)}px`,
                height: `${BAR_HEIGHT}px`,
                '--bar-color': bar.color,
              }"
              @mouseenter="hoveredId = bar.task.id"
              @mouseleave="hoveredId = null"
              @pointerdown="onBarPointerDown($event, bar)"
              @dblclick="emit('open', bar.task.id)"
            >
              <div class="bar-progress" :style="{ width: `${bar.task.progress_percent}%` }" />
              <span class="bar-label">{{ bar.task.title }}</span>
              <span v-if="!readonly" class="resize-handle" title="Потяните, чтобы изменить длительность" @pointerdown="onResizePointerDown($event, bar)" />
              <span v-if="!readonly" class="link-handle" title="Потяните к другой задаче, чтобы связать" @pointerdown="onHandlePointerDown($event, bar)" />

              <div class="bar-tooltip">
                <strong>{{ bar.task.title }}</strong>
                <div>{{ formatDate(bar.task.start_date) }} — {{ formatDate(bar.task.end_date) }} · {{ pluralDays(bar.task.duration_days) }}</div>
                <div class="muted">{{ STATE_LABELS[bar.task.state] }} · {{ bar.task.progress_percent }}%</div>
                <div v-if="bar.task.assignee" class="muted">
                  Ответственный: {{ bar.task.assignee.full_name }} ({{ initials(bar.task.assignee) }})
                </div>
                <div v-if="bar.task.is_critical" class="critical-note"><i class="pi pi-bolt" /> критический путь, резерва нет</div>
                <div v-else class="muted">Резерв: {{ pluralDays(bar.task.slack_days) }}</div>
                <div v-if="drag?.active && drag.taskId === bar.task.id && drag.deltaDays" class="drag-hint">
                  Сдвиг на {{ drag.deltaDays > 0 ? '+' : '' }}{{ drag.deltaDays }} дн.
                </div>
                <div v-if="resize?.taskId === bar.task.id && resize.deltaDays" class="drag-hint">
                  Окончание: {{ formatDate(addDays(bar.task.end_date, resize.deltaDays)) }}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.gantt { display: flex; flex-direction: column; overflow: hidden; }

.gantt-toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 14px;
  border-bottom: 1px solid #e2e8f0;
  background: #f8fafc;
  flex-wrap: wrap;
}
.toolbar-hint { font-size: 12px; color: #64748b; }
.spacer { flex: 1 1 auto; }

.gantt-scroller { overflow: auto; max-height: min(72vh, 760px); position: relative; }
.gantt-grid { position: relative; }

.gantt-header {
  display: flex;
  position: sticky;
  top: 0;
  z-index: 5;
  background: #f1f5f9;
  border-bottom: 1px solid #e2e8f0;
}

.header-sidebar,
.side-row {
  display: grid;
  grid-template-columns: minmax(0, 8fr) 3fr 2fr;
  gap: 8px;
  padding: 0 16px;
  align-items: center;
  flex: none;
}

.header-sidebar {
  position: sticky;
  left: 0;
  z-index: 6;
  background: #f1f5f9;
  border-right: 1px solid #e2e8f0;
  font-size: 11px;
  font-weight: 700;
  color: #475569;
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

.header-timeline { position: relative; flex: none; }
.months { position: relative; height: 26px; }

.month {
  position: absolute;
  top: 0;
  height: 26px;
  display: flex;
  align-items: center;
  border-left: 1px solid #e2e8f0;
  overflow: hidden;
}
.month-label {
  padding: 0 6px;
  font-size: 12px;
  font-weight: 700;
  text-transform: capitalize;
  color: #475569;
  white-space: nowrap;
  position: sticky;
  left: 0;
}

.days { position: relative; height: 26px; }

.day, .week {
  position: absolute;
  top: 0;
  height: 26px;
  display: grid;
  place-items: center;
  font-size: 11px;
  color: #64748b;
}
.week { border-left: 1px solid #e2e8f0; font-size: 10px; }
.day.weekend { background: rgba(100, 116, 139, 0.1); }
.day.month-start { border-left: 1px solid #cbd5e1; }
.day.today {
  background: #fee2e2;
  color: #b91c1c;
  font-weight: 700;
  border-radius: 4px;
}

.gantt-body { display: flex; position: relative; }

.body-sidebar {
  position: sticky;
  left: 0;
  z-index: 4;
  background: #f8fafc;
  border-right: 1px solid #e2e8f0;
  flex: none;
}

.side-row {
  font-size: 12px;
  color: #475569;
  border-bottom: 1px solid #e2e8f0;
  cursor: default;
  user-select: none;
  transition: background .15s;
}
.side-row.hovered { background: #fff; }
.side-row.critical .side-title { color: #7f1d1d; }
.side-title { display: flex; align-items: center; gap: 6px; font-weight: 500; color: #1e293b; min-width: 0; }
.state-dot { width: 8px; height: 8px; border-radius: 50%; flex: none; }
.critical-mark { color: #991b1b; font-size: 10px; flex: none; }

.gantt-canvas { position: relative; flex: none; background: #fff; }

.grid-layer, .row-lines { position: absolute; inset: 0; }
.grid-col { position: absolute; top: 0; bottom: 0; }
.grid-col.weekend { background: rgba(148, 163, 184, 0.12); }
.grid-col.month-start { border-left: 1px solid #cbd5e1; }
.project-window {
  position: absolute;
  top: 0;
  bottom: 0;
  background: rgba(254, 226, 226, 0.35);
  border-left: 1px dashed #fca5a5;
  border-right: 1px dashed #fca5a5;
}

.row-line { position: absolute; left: 0; right: 0; border-bottom: 1px solid #f1f5f9; }
.row-line.hovered { background: rgba(148, 163, 184, 0.08); }

.today-line {
  position: absolute;
  top: 0;
  bottom: 0;
  width: 2px;
  background: #ef4444;
  opacity: .8;
  z-index: 3;
  pointer-events: none;
}
.today-label {
  position: absolute;
  top: 2px;
  left: 4px;
  font-size: 9px;
  font-weight: 700;
  color: #b91c1c;
  text-transform: uppercase;
  letter-spacing: .05em;
  white-space: nowrap;
}

.links-layer { position: absolute; inset: 0; pointer-events: none; overflow: visible; z-index: 2; }
.link { fill: none; stroke: #64748b; stroke-width: 1.5; color: #64748b; opacity: .85; }
.link-group.critical .link { stroke: #991b1b; color: #991b1b; opacity: 1; stroke-width: 2; }
.link-group.violated .link { stroke: #f59e0b; color: #f59e0b; stroke-dasharray: 4 3; opacity: 1; }
.link-hit { fill: none; stroke: transparent; stroke-width: 12; pointer-events: stroke; cursor: pointer; }
.link-group:hover .link { stroke-width: 2.5; opacity: 1; }
.link-preview { fill: none; stroke: #c64747; stroke-width: 2; stroke-dasharray: 5 4; }

.bar {
  position: absolute;
  border-radius: 6px;
  background: var(--bar-color);
  display: flex;
  align-items: center;
  cursor: grab;
  z-index: 3;
  overflow: visible;
  touch-action: none;
  box-shadow: 0 1px 2px rgba(0, 0, 0, .15);
  transition: box-shadow .15s;
}
.bar.readonly { cursor: default; }
.bar.light { opacity: .85; }
.bar:hover { box-shadow: 0 4px 10px rgba(0, 0, 0, .18); z-index: 5; }
.bar.dragging { cursor: grabbing; opacity: .9; z-index: 6; }
.bar.resizing { z-index: 6; }
.bar.critical { outline: 2px solid #7f1d1d; outline-offset: 1px; }
.bar.link-target { box-shadow: 0 0 0 3px rgba(198, 71, 71, 0.55); }

.bar-progress {
  position: absolute;
  inset: 0 auto 0 0;
  background: rgba(0, 0, 0, 0.18);
  border-radius: 6px 0 0 6px;
  max-width: 100%;
  pointer-events: none;
}

.bar-label {
  position: relative;
  z-index: 1;
  padding: 0 8px;
  font-size: 12px;
  font-weight: 500;
  color: #fff;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  pointer-events: none;
}
.bar.light .bar-label { color: #7f1d1d; }

.resize-handle {
  position: absolute;
  right: 0;
  top: 0;
  bottom: 0;
  width: 8px;
  cursor: ew-resize;
  border-radius: 0 6px 6px 0;
  z-index: 4;
}
.bar:hover .resize-handle { background: rgba(255, 255, 255, 0.35); }

.link-handle {
  position: absolute;
  right: -8px;
  top: 50%;
  transform: translateY(-50%);
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: #fff;
  border: 2px solid #c64747;
  opacity: 0;
  cursor: crosshair;
  transition: opacity .12s ease;
  z-index: 5;
}
.bar:hover .link-handle { opacity: 1; }

.bar-tooltip {
  position: absolute;
  bottom: calc(100% + 8px);
  left: 0;
  min-width: 240px;
  padding: 10px 12px;
  border-radius: 8px;
  background: #fff;
  border: 1px solid #e2e8f0;
  box-shadow: 0 10px 26px rgba(15, 23, 42, 0.18);
  font-size: 12px;
  line-height: 1.45;
  color: #0f172a;
  display: none;
  z-index: 10;
  pointer-events: none;
  white-space: nowrap;
}
.bar:hover .bar-tooltip, .bar.dragging .bar-tooltip, .bar.resizing .bar-tooltip { display: block; }
.bar-tooltip .muted { color: #64748b; }
.critical-note { color: #991b1b; font-weight: 600; }
.drag-hint { margin-top: 4px; color: #c64747; font-weight: 700; }
</style>
