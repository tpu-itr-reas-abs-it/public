<script setup lang="ts">
import { ref, watch } from 'vue'
import Dialog from 'primevue/dialog'
import Textarea from 'primevue/textarea'
import Button from 'primevue/button'
import ProgressSpinner from 'primevue/progressspinner'
import { tasksApi } from '@/api'
import { useNotify } from '@/composables/useNotify'
import { formatDateTime, shortName } from '@/utils/format'
import type { Comment, Task } from '@/types/api'

const props = defineProps<{ visible: boolean; task: Task | null }>()
const emit = defineEmits<{
  (e: 'update:visible', value: boolean): void
  (e: 'count', taskId: number, count: number): void
}>()

const notify = useNotify()

const comments = ref<Comment[]>([])
const loading = ref(false)
const submitting = ref(false)
const text = ref('')

async function load() {
  if (!props.task) return
  loading.value = true
  comments.value = []
  text.value = ''
  try {
    const page = await tasksApi.comments(props.task.id, { limit: 100 })
    comments.value = page.items
    emit('count', props.task.id, page.total)
  } catch (error) {
    notify.error(error, 'Не удалось загрузить комментарии')
  } finally {
    loading.value = false
  }
}

watch(
  () => props.visible,
  (open) => {
    if (open) void load()
  },
)

async function submit() {
  const value = text.value.trim()
  if (!value || !props.task) return
  submitting.value = true
  try {
    const created = await tasksApi.addComment(props.task.id, value)
    comments.value.push(created)
    emit('count', props.task.id, comments.value.length)
    text.value = ''
  } catch (error) {
    notify.error(error, 'Не удалось отправить комментарий')
  } finally {
    submitting.value = false
  }
}

function close() {
  emit('update:visible', false)
}
</script>

<template>
  <Dialog
    :visible="visible"
    modal
    class="app-dialog"
    header="Комментарии"
    :style="{ width: '540px' }"
    :breakpoints="{ '640px': '96vw' }"
    :draggable="false"
    dismissable-mask
    @update:visible="emit('update:visible', $event)"
  >
    <p v-if="task" class="task-ref">
      Задача: <strong>#{{ task.id }} {{ task.title }}</strong>
    </p>

    <div v-if="loading" class="comments-empty">
      <ProgressSpinner style="width: 28px; height: 28px" stroke-width="4" />
      Загрузка комментариев...
    </div>

    <div v-else-if="comments.length === 0" class="comments-empty">
      Комментариев пока нет.<br />Будьте первым!
    </div>

    <div v-else class="comments-list custom-scroll">
      <div v-for="comment in comments" :key="comment.id" class="comment-item">
        <div class="comment-head">
          <span class="comment-author">
            {{ shortName(comment.author?.full_name || comment.author?.email || 'Пользователь') }}
          </span>
          <span>{{ formatDateTime(comment.created_at) }}</span>
        </div>
        <div class="comment-text">{{ comment.text }}</div>
      </div>
    </div>

    <form class="comment-form" @submit.prevent="submit">
      <Textarea
        v-model="text"
        class="input-red"
        rows="3"
        auto-resize
        placeholder="Напишите комментарий... (Ctrl+Enter — отправить)"
        :disabled="submitting"
        @keydown.ctrl.enter.prevent="submit"
        @keydown.meta.enter.prevent="submit"
      />
      <div class="comment-actions">
        <Button type="button" label="Закрыть" rounded outlined severity="secondary" @click="close" />
        <Button type="submit" label="Отправить" rounded :loading="submitting" :disabled="!text.trim()" />
      </div>
    </form>
  </Dialog>
</template>

<style scoped>
.task-ref { font-size: 14px; color: #64748b; margin-bottom: 16px; }
.task-ref strong { color: #334155; font-weight: 600; }

.comments-list {
  max-height: 360px;
  overflow-y: auto;
  padding: 4px 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.comment-item {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 12px 14px;
  font-size: 14px;
  color: #0f172a;
}

.comment-head {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 6px;
  gap: 8px;
  font-size: 12px;
  color: #64748b;
}
.comment-author { font-weight: 700; color: #c64747; }
.comment-text { white-space: pre-wrap; word-break: break-word; line-height: 1.5; }

.comments-empty {
  padding: 24px 16px;
  text-align: center;
  color: #94a3b8;
  font-size: 14px;
  background: #f8fafc;
  border: 1px dashed #e2e8f0;
  border-radius: 10px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.comment-form {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 2px solid #fee2e2;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.comment-actions { display: flex; justify-content: flex-end; gap: 8px; }
</style>
