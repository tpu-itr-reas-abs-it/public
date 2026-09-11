<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import Textarea from 'primevue/textarea'
import DatePicker from 'primevue/datepicker'
import AuthLayout from '@/components/auth/AuthLayout.vue'
import { projectsApi } from '@/api'
import { useNotify } from '@/composables/useNotify'
import { dayjs, toApiDate } from '@/utils/format'
import type { FeatureItem } from '@/types/ui'

const router = useRouter()
const notify = useNotify()

const FEATURES: FeatureItem[] = [
  { color: 'blue', text: 'Автоматический расчет длительности' },
  { color: 'green', text: 'Мгновенное построение Ганта' },
  { color: 'yellow', text: 'Контроль сроков и зависимостей' },
]

const form = reactive({
  name: '',
  description: '',
  start: dayjs().toDate() as Date | null,
  end: dayjs().add(30, 'day').toDate() as Date | null,
})
const saving = ref(false)

async function submit() {
  const name = form.name.trim()
  if (!name) return notify.warn('Укажите название проекта')
  if (!form.start || !form.end) return notify.warn('Укажите даты начала и окончания')
  if (form.start > form.end) return notify.warn('Дата начала не может быть позже даты окончания')

  saving.value = true
  try {
    const created = await projectsApi.create({
      name,
      description: form.description.trim() || null,
      start_date: toApiDate(form.start),
      end_date: toApiDate(form.end),
    })
    notify.success(`Проект «${created.name}» создан!`)
    await router.replace({ name: 'workspace', params: { id: created.id } })
  } catch (error) {
    notify.error(error, 'Ошибка создания проекта')
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <AuthLayout
    title="Создание нового проекта"
    description="Введите базовые параметры, чтобы перейти к планированию задач на диаграмме Ганта"
    :features="FEATURES"
    card-subtitle="Параметры проекта"
  >
    <form class="project-form" @submit.prevent="submit">
      <div class="form-group">
        <label for="proj-name">Название проекта *</label>
        <InputText id="proj-name" v-model="form.name" placeholder="Например: Разработка сайта" required />
      </div>

      <div class="form-group">
        <label for="proj-desc">Описание</label>
        <Textarea id="proj-desc" v-model="form.description" rows="2" auto-resize placeholder="Необязательно" />
      </div>

      <div class="dates">
        <div class="form-group">
          <label for="proj-start">Дата начала *</label>
          <DatePicker
            v-model="form.start"
            input-id="proj-start"
            date-format="dd.mm.yy"
            show-icon
            icon-display="input"
            :max-date="form.end ?? undefined"
          />
        </div>
        <div class="form-group">
          <label for="proj-end">Дата окончания *</label>
          <DatePicker
            v-model="form.end"
            input-id="proj-end"
            date-format="dd.mm.yy"
            show-icon
            icon-display="input"
            :min-date="form.start ?? undefined"
          />
        </div>
      </div>

      <div class="actions">
        <Button type="submit" class="btn-auth" :label="saving ? 'Создание...' : 'Создать проект'" :loading="saving" />
        <Button
          type="button"
          label="← К списку проектов"
          severity="secondary"
          outlined
          class="btn-back"
          @click="router.push({ name: 'projects' })"
        />
      </div>
    </form>
  </AuthLayout>
</template>

<style scoped>
.form-group { margin-bottom: 30px; }

.form-group label {
  display: block;
  font-size: 15px;
  color: #000000;
  margin-bottom: 10px;
  font-weight: 400;
}

.dates {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}

.actions {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.btn-back {
  width: 100%;
  padding: 12px;
  border-radius: 8px;
  border-color: #D9D9D9;
  color: var(--text-light);
}
</style>
