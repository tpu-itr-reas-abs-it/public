<script setup lang="ts">
import { computed, ref } from 'vue'
import Button from 'primevue/button'
import Select from 'primevue/select'
import InputText from 'primevue/inputtext'
import ProgressSpinner from 'primevue/progressspinner'
import TaskCard from './TaskCard.vue'
import { STATE_FILTER_OPTIONS } from '@/utils/status'
import type { DerivedTaskState, Task, TaskStatus } from '@/types/api'

const props = defineProps<{
  tasks: Task[]
  loading: boolean
  canEdit: boolean
  commentCounts: Record<number, number>
  criticalIds: number[]
}>()

const emit = defineEmits<{
  (e: 'create'): void
  (e: 'edit', task: Task): void
  (e: 'remove', task: Task): void
  (e: 'comments', task: Task): void
  (e: 'status', task: Task, status: TaskStatus): void
}>()

const stateFilter = ref<DerivedTaskState | 'all'>('all')
const search = ref('')

const filtered = computed(() => {
  const query = search.value.trim().toLowerCase()
  return props.tasks.filter((task) => {
    if (stateFilter.value !== 'all' && task.state !== stateFilter.value) return false
    if (query && !task.title.toLowerCase().includes(query) && !String(task.id).includes(query)) return false
    return true
  })
})

const criticalSet = computed(() => new Set(props.criticalIds))
</script>

<template>
  <section class="task-list">
    <div class="list-head">
      <h3><span class="head-mark" />Задачи <span class="count">{{ tasks.length }}</span></h3>
      <Select
        v-model="stateFilter"
        :options="STATE_FILTER_OPTIONS"
        option-label="label"
        option-value="value"
        class="filter-select"
        size="small"
      />
    </div>

    <InputText v-if="tasks.length > 5" v-model="search" class="search input-sm" placeholder="Поиск по названию или ID" />

    <div v-if="loading && tasks.length === 0" class="list-empty">
      <ProgressSpinner style="width: 28px; height: 28px" stroke-width="4" />
      <p>Загрузка...</p>
    </div>

    <div v-else-if="filtered.length === 0" class="list-empty dashed">
      {{ tasks.length === 0 ? 'Пока нет задач' : 'Нет задач с таким состоянием' }}
    </div>

    <div v-else class="cards custom-scroll">
      <TaskCard
        v-for="task in filtered"
        :key="task.id"
        :task="task"
        :can-edit="canEdit"
        :comments-count="commentCounts[task.id]"
        :critical="criticalSet.has(task.id)"
        @edit="emit('edit', task)"
        @remove="emit('remove', task)"
        @comments="emit('comments', task)"
        @status="emit('status', task, $event)"
      />
    </div>

    <Button
      v-if="canEdit"
      class="btn-gradient create-btn"
      icon="pi pi-plus"
      label="Создать задачу"
      @click="emit('create')"
    />
  </section>
</template>

<style scoped>
.task-list {
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 1px 2px rgba(0, 0, 0, .05);
  padding: 20px;
  border: 1px solid #e2e8f0;
  display: flex;
  flex-direction: column;
  min-height: 100%;
}

.list-head { display: flex; justify-content: space-between; align-items: center; gap: 8px; margin-bottom: 12px; }
.list-head h3 { font-size: 18px; font-weight: 700; color: #1e293b; display: flex; align-items: center; gap: 8px; }
.head-mark { width: 6px; height: 20px; background: #1e293b; border-radius: 100px; }
.count { font-size: 12px; font-weight: 600; color: #64748b; background: #f1f5f9; padding: 2px 8px; border-radius: 100px; }
.filter-select { min-width: 140px; }

.search { margin-bottom: 12px; }

.list-empty {
  text-align: center;
  padding: 32px 12px;
  color: #94a3b8;
  font-size: 14px;
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
}
.list-empty.dashed { background: #f8fafc; border-radius: 8px; border: 1px dashed #e2e8f0; }

.cards {
  display: flex;
  flex-direction: column;
  gap: 12px;
  max-height: 560px;
  overflow-y: auto;
  padding-right: 4px;
  flex: 1;
}

.create-btn { width: 100%; margin-top: 16px; }
</style>
