<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import Dialog from 'primevue/dialog'
import InputText from 'primevue/inputtext'
import Textarea from 'primevue/textarea'
import Select from 'primevue/select'
import MultiSelect from 'primevue/multiselect'
import DatePicker from 'primevue/datepicker'
import Slider from 'primevue/slider'
import Button from 'primevue/button'
import { dependenciesApi, tasksApi } from '@/api'
import { useNotify } from '@/composables/useNotify'
import { dayjs, shortName, toApiDate, toDate } from '@/utils/format'
import { ROLE_LABELS, STATUS_OPTIONS } from '@/utils/status'
import type { Member, Task, TaskStatus } from '@/types/api'

const props = defineProps<{
  visible: boolean
  projectId: number
  task: Task | null
  members: Member[]
  tasks: Task[]
}>()

const emit = defineEmits<{
  (e: 'update:visible', value: boolean): void
  (e: 'saved'): void
}>()

const notify = useNotify()

const isEditing = computed(() => props.task !== null)

const form = reactive({
  title: '',
  description: '',
  assignee_id: null as number | null,
  start: null as Date | null,
  end: null as Date | null,
  status: 'planned' as TaskStatus,
  progress: 0,
  predecessor_ids: [] as number[],
})

const saving = ref(false)
const linksLoading = ref(false)
let initialPredecessors: number[] = []
let successorIds: number[] = []

const assigneeOptions = computed(() =>
  props.members
    .filter((m) => m.user)
    .map((m) => ({
      value: m.user!.id,
      label: `${shortName(m.user!.full_name || m.user!.email)} (${ROLE_LABELS[m.role]})`,
    })),
)

const predecessorOptions = computed(() =>
  props.tasks
    .filter((t) => t.id !== props.task?.id && !successorIds.includes(t.id))
    .map((t) => ({ value: t.id, label: `#${t.id} · ${t.title}` })),
)

const durationLabel = computed(() => {
  if (!form.start || !form.end) return ''
  const days = dayjs(form.end).diff(dayjs(form.start), 'day') + 1
  return days > 0 ? `${days} дн.` : ''
})

async function reset() {
  const task = props.task
  initialPredecessors = []
  successorIds = []
  form.title = task?.title ?? ''
  form.description = task?.description ?? ''
  form.assignee_id = task?.assignee_id ?? null
  form.start = task ? toDate(task.start_date) : dayjs().toDate()
  form.end = task ? toDate(task.end_date) : dayjs().add(3, 'day').toDate()
  form.status = task?.status ?? 'planned'
  form.progress = task?.progress_percent ?? 0
  form.predecessor_ids = []

  if (!task) return
  linksLoading.value = true
  try {
    const links = await tasksApi.get(task.id)
    initialPredecessors = [...links.predecessor_ids]
    successorIds = [...links.successor_ids]
    form.predecessor_ids = [...links.predecessor_ids]
  } catch (error) {
    notify.error(error, 'Не удалось загрузить связи задачи')
  } finally {
    linksLoading.value = false
  }
}

watch(
  () => props.visible,
  (open) => {
    if (open) void reset()
  },
)

function close() {
  emit('update:visible', false)
}

async function syncDependencies(taskId: number) {
  const chosen = new Set(form.predecessor_ids)
  const initial = new Set(initialPredecessors)
  const added = [...chosen].filter((id) => !initial.has(id))
  const removed = [...initial].filter((id) => !chosen.has(id))
  if (!added.length && !removed.length) return

  if (removed.length) {
    const deps = await dependenciesApi.list(props.projectId)
    for (const dep of deps) {
      if (dep.successor_id === taskId && removed.includes(dep.predecessor_id)) {
        await dependenciesApi.remove(dep.id)
      }
    }
  }
  for (const predecessorId of added) {
    await dependenciesApi.create(taskId, { predecessor_id: predecessorId })
  }
}

async function save() {
  const title = form.title.trim()
  if (!title) return notify.warn('Укажите название задачи')
  if (!form.start || !form.end) return notify.warn('Укажите даты начала и окончания')
  const start_date = toApiDate(form.start)
  const end_date = toApiDate(form.end)
  if (start_date > end_date) return notify.warn('Дата окончания раньше даты начала')

  const payload = {
    title,
    description: form.description.trim() || null,
    start_date,
    end_date,
    status: form.status,
    assignee_id: form.assignee_id,
    progress_percent: form.status === 'done' ? 100 : form.progress,
  }

  saving.value = true
  try {
    if (props.task) {
      await tasksApi.update(props.task.id, payload)
      try {
        await syncDependencies(props.task.id)
      } catch (error) {
        notify.error(error, 'Не удалось обновить связи задачи')
      }
      notify.success('Изменения сохранены')
    } else {
      await tasksApi.create(props.projectId, { ...payload, predecessor_ids: form.predecessor_ids })
      notify.success(`Задача «${title}» создана`)
    }
    emit('saved')
    close()
  } catch (error) {
    notify.error(error, 'Ошибка сохранения задачи')
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <Dialog
    :visible="visible"
    modal
    class="app-dialog"
    :header="isEditing ? 'Редактирование задачи' : 'Новая задача'"
    :style="{ width: '560px' }"
    :breakpoints="{ '640px': '96vw' }"
    :draggable="false"
    dismissable-mask
    @update:visible="emit('update:visible', $event)"
  >
    <form class="task-form" @submit.prevent="save">
      <div class="field">
        <label for="task-title">Название задачи *</label>
        <InputText id="task-title" v-model="form.title" class="input-red" placeholder="Введите название" autofocus />
      </div>

      <div class="field">
        <label for="task-assignee">Ответственный</label>
        <Select
          v-model="form.assignee_id"
          input-id="task-assignee"
          :options="assigneeOptions"
          option-label="label"
          option-value="value"
          placeholder="Не назначен"
          show-clear
          class="input-red"
        />
      </div>

      <div class="field-row">
        <div class="field">
          <label for="task-start">Дата начала *</label>
          <DatePicker
            v-model="form.start"
            input-id="task-start"
            date-format="dd.mm.yy"
            class="input-red"
            :max-date="form.end ?? undefined"
            show-icon
            icon-display="input"
          />
        </div>
        <div class="field">
          <label for="task-end">Дата окончания * <span v-if="durationLabel" class="hint">({{ durationLabel }})</span></label>
          <DatePicker
            v-model="form.end"
            input-id="task-end"
            date-format="dd.mm.yy"
            class="input-red"
            :min-date="form.start ?? undefined"
            show-icon
            icon-display="input"
          />
        </div>
      </div>

      <div class="field-row">
        <div class="field">
          <label for="task-status">Статус</label>
          <Select
            v-model="form.status"
            input-id="task-status"
            :options="STATUS_OPTIONS"
            option-label="label"
            option-value="value"
            class="input-red"
          />
        </div>
        <div class="field">
          <label>Прогресс: <span class="hint">{{ form.status === 'done' ? 100 : form.progress }}%</span></label>
          <div class="slider-wrap">
            <Slider v-model="form.progress" :min="0" :max="100" :step="5" :disabled="form.status === 'done'" />
          </div>
        </div>
      </div>

      <div class="field">
        <label for="task-deps">
          Зависит от задач
          <span v-if="linksLoading" class="hint">(загрузка связей...)</span>
        </label>
        <MultiSelect
          v-model="form.predecessor_ids"
          input-id="task-deps"
          :options="predecessorOptions"
          option-label="label"
          option-value="value"
          display="chip"
          filter
          :placeholder="predecessorOptions.length ? 'Выберите предшественников' : 'Других задач пока нет'"
          :disabled="linksLoading || predecessorOptions.length === 0"
          class="input-red"
        />
        <small class="hint">Задача сможет начаться только после завершения выбранных.</small>
      </div>

      <div class="field">
        <label for="task-desc">Описание</label>
        <Textarea id="task-desc" v-model="form.description" class="input-red" rows="2" auto-resize placeholder="Необязательно" />
      </div>

      <div class="dialog-actions">
        <Button type="button" label="Отмена" text severity="secondary" @click="close" />
        <Button
          type="submit"
          class="btn-gradient"
          :label="isEditing ? 'Сохранить изменения' : 'Создать задачу'"
          :loading="saving"
        />
      </div>
    </form>
  </Dialog>
</template>

<style scoped>
.task-form { display: flex; flex-direction: column; gap: 16px; padding-top: 4px; }
.hint { font-weight: 400; color: #94a3b8; font-size: 12px; }
.slider-wrap { padding: 14px 6px 0; }
</style>
