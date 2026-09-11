<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import ProgressSpinner from 'primevue/progressspinner'
import { useConfirm } from 'primevue/useconfirm'
import AuthLayout from '@/components/auth/AuthLayout.vue'
import UserChip from '@/components/UserChip.vue'
import ProjectCard from '@/components/ProjectCard.vue'
import { projectsApi } from '@/api'
import { useAuthStore } from '@/stores/auth'
import { useProjectStore } from '@/stores/project'
import { useNotify } from '@/composables/useNotify'
import type { ProjectSummary } from '@/types/api'
import type { FeatureItem } from '@/types/ui'

const router = useRouter()
const auth = useAuthStore()
const projectStore = useProjectStore()
const notify = useNotify()
const confirm = useConfirm()

const FEATURES: FeatureItem[] = [
  { color: 'blue', text: 'Все проекты в одном месте' },
  { color: 'green', text: 'Прогресс и просрочки видны сразу' },
  { color: 'yellow', text: 'Один клик — и вы в диаграмме' },
]

const projects = ref<ProjectSummary[]>([])
const loading = ref(false)
const search = ref('')

const filtered = computed(() => {
  const query = search.value.trim().toLowerCase()
  if (!query) return projects.value
  return projects.value.filter(
    (p) => p.name.toLowerCase().includes(query) || (p.description ?? '').toLowerCase().includes(query),
  )
})

async function load() {
  loading.value = true
  try {
    projects.value = (await projectsApi.list({ limit: 200 })).items
  } catch (error) {
    projects.value = []
    notify.error(error, 'Не удалось загрузить список проектов')
  } finally {
    loading.value = false
  }
}

function open(project: ProjectSummary) {
  router.push({ name: 'workspace', params: { id: project.id } })
}

function remove(project: ProjectSummary) {
  confirm.require({
    header: 'Удаление проекта',
    message: `Удалить проект «${project.name}»? Это действие нельзя отменить.`,
    icon: 'pi pi-exclamation-triangle',
    acceptLabel: 'Удалить',
    rejectLabel: 'Отмена',
    acceptProps: { severity: 'danger' },
    rejectProps: { severity: 'secondary', outlined: true },
    accept: async () => {
      try {
        await projectsApi.remove(project.id)
        projects.value = projects.value.filter((p) => p.id !== project.id)
        notify.success(`Проект «${project.name}» удалён`)
      } catch (error) {
        notify.error(error, 'Не удалось удалить проект')
      }
    },
  })
}

function logout() {
  auth.logout()
  projectStore.reset()
  router.replace({ name: 'login' })
}

onMounted(load)
</script>

<template>
  <AuthLayout
    title="Ваши проекты"
    description="Выберите проект для продолжения работы или создайте новый"
    :features="FEATURES"
    card-subtitle="Проекты"
    scrollable
  >
    <UserChip v-if="auth.user" :user="auth.user" class="chip" />

    <div class="projects-toolbar">
      <h2>Всего: {{ projects.length }}</h2>
      <div class="projects-toolbar-actions">
        <Button label="+ Новый проект" rounded @click="router.push({ name: 'project-create' })" />
        <Button label="Выйти" rounded outlined severity="secondary" @click="logout" />
      </div>
    </div>

    <InputText
      v-if="projects.length > 3"
      v-model="search"
      class="projects-search"
      placeholder="Поиск по названию или описанию"
    />

    <div v-if="loading" class="projects-empty">
      <ProgressSpinner style="width: 36px; height: 36px" stroke-width="4" />
      <div>Загрузка проектов...</div>
    </div>

    <div v-else-if="projects.length === 0" class="projects-empty">
      Пока нет ни одного проекта.<br />
      Нажмите «+ Новый проект», чтобы создать первый.
    </div>

    <div v-else-if="filtered.length === 0" class="projects-empty">
      По запросу «{{ search }}» ничего не найдено.
    </div>

    <div v-else class="project-list">
      <ProjectCard
        v-for="project in filtered"
        :key="project.id"
        :project="project"
        :can-delete="project.owner_id === auth.user?.id"
        @open="open(project)"
        @remove="remove(project)"
      />
    </div>
  </AuthLayout>
</template>

<style scoped>
.chip { margin-bottom: 24px; }

.projects-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  padding-bottom: 16px;
  border-bottom: 1px solid #D9D9D9;
  flex-wrap: wrap;
}
.projects-toolbar h2 { font-size: 20px; font-weight: 600; color: var(--text); }
.projects-toolbar-actions { display: flex; gap: 8px; }

.projects-search { margin-top: 20px; }

.project-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 16px;
  margin-top: 24px;
}

.projects-empty {
  padding: 60px 20px;
  text-align: center;
  color: var(--text-light);
  font-size: 15px;
  border: 2px dashed #E0E0E0;
  border-radius: 12px;
  margin-top: 24px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}
</style>
