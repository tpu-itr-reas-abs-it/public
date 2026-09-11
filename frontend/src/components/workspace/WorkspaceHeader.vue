<script setup lang="ts">
import { ref } from 'vue'
import Button from 'primevue/button'
import Menu from 'primevue/menu'
import AppLogo from '@/components/AppLogo.vue'
import UserChip from '@/components/UserChip.vue'
import { formatDate } from '@/utils/format'
import type { ProjectDetail, UserPublic } from '@/types/api'

defineProps<{ project: ProjectDetail | null; user: UserPublic | null }>()
const emit = defineEmits<{
  (e: 'projects'): void
  (e: 'create'): void
  (e: 'export', format: 'json' | 'csv'): void
}>()

const exportMenu = ref<InstanceType<typeof Menu> | null>(null)
const exportItems = [
  { label: 'JSON — полный дамп проекта', icon: 'pi pi-code', command: () => emit('export', 'json') },
  { label: 'CSV — таблица задач для Excel', icon: 'pi pi-table', command: () => emit('export', 'csv') },
]
</script>

<template>
  <nav class="workspace-nav">
    <div class="nav-inner">
      <div class="nav-left">
        <div class="header-logo"><AppLogo :height="32" /></div>
        <div class="nav-title">
          <h1>{{ project?.name || 'Загрузка...' }}</h1>
          <p v-if="project">
            <i class="pi pi-calendar" /> {{ formatDate(project.start_date) }} — {{ formatDate(project.end_date) }}
          </p>
        </div>
      </div>

      <div class="nav-right">
        <UserChip v-if="user" :user="user" size="sm" />
        <Button
          v-if="project"
          class="btn-glass"
          icon="pi pi-download"
          label="Экспорт"
          aria-haspopup="true"
          aria-controls="export-menu"
          @click="exportMenu?.toggle($event)"
        />
        <Menu id="export-menu" ref="exportMenu" :model="exportItems" popup />
        <Button class="btn-glass" label="← Мои проекты" @click="emit('projects')" />
        <Button class="btn-glass" label="+ Новый" @click="emit('create')" />
      </div>
    </div>
  </nav>
</template>

<style scoped>
.workspace-nav {
  background: linear-gradient(90deg, #dc2626, #ef4444);
  box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -4px rgba(0, 0, 0, 0.1);
  border-bottom: 1px solid #f87171;
  position: sticky;
  top: 0;
  z-index: 10;
}

.nav-inner {
  max-width: 1280px;
  margin: 0 auto;
  padding: 6px 16px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.nav-left { display: flex; align-items: center; gap: 12px; min-width: 0; }

.header-logo {
  display: flex;
  flex-shrink: 0;
}

.nav-title { min-width: 0; }
.nav-title h1 {
  font-size: 18px;
  font-weight: 700;
  color: #fff;
  letter-spacing: -0.01em;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.nav-title p {
  color: #fee2e2;
  font-size: 13px;
  margin-top: 2px;
  display: flex;
  align-items: center;
  gap: 6px;
}
.nav-title p .pi { font-size: 12px; }

.nav-right { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
</style>
