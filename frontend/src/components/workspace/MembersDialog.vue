<script setup lang="ts">
import { ref, watch } from 'vue'
import Dialog from 'primevue/dialog'
import AutoComplete, { type AutoCompleteCompleteEvent } from 'primevue/autocomplete'
import Select from 'primevue/select'
import Button from 'primevue/button'
import { useConfirm } from 'primevue/useconfirm'
import { projectsApi, usersApi } from '@/api'
import { useNotify } from '@/composables/useNotify'
import { shortName } from '@/utils/format'
import { MEMBER_ROLE_OPTIONS, ROLE_LABELS } from '@/utils/status'
import type { Member, MemberRole, UserPublic } from '@/types/api'

const props = defineProps<{
  visible: boolean
  projectId: number
  members: Member[]
  canManage: boolean
}>()

const emit = defineEmits<{
  (e: 'update:visible', value: boolean): void
  (e: 'changed'): void
}>()

const notify = useNotify()
const confirm = useConfirm()

const query = ref<string | UserPublic>('')
const suggestions = ref<UserPublic[]>([])
const role = ref<MemberRole>('responsible')
const submitting = ref(false)

watch(
  () => props.visible,
  (open) => {
    if (open) {
      query.value = ''
      role.value = 'responsible'
      suggestions.value = []
    }
  },
)

async function search(event: AutoCompleteCompleteEvent) {
  const q = event.query.trim()
  if (q.length < 2) {
    suggestions.value = []
    return
  }
  try {
    const known = new Set(props.members.map((m) => m.user_id))
    suggestions.value = (await usersApi.search(q)).filter((u) => !known.has(u.id))
  } catch {
    suggestions.value = []
  }
}

function memberName(member: Member): string {
  return member.user?.full_name || member.user?.email || 'Неизвестно'
}

async function add() {
  const value = query.value
  const payload =
    typeof value === 'string'
      ? { email: value.trim(), role: role.value }
      : { user_id: value.id, role: role.value }
  if ('email' in payload && !payload.email) return

  submitting.value = true
  try {
    const member = await projectsApi.addMember(props.projectId, payload)
    notify.success(`Участник ${memberName(member)} добавлен`)
    query.value = ''
    emit('changed')
  } catch (error) {
    notify.error(error, 'Не удалось добавить участника')
  } finally {
    submitting.value = false
  }
}

function remove(member: Member) {
  confirm.require({
    header: 'Исключить участника',
    message: `Исключить ${memberName(member)} из проекта?`,
    icon: 'pi pi-user-minus',
    acceptLabel: 'Исключить',
    rejectLabel: 'Отмена',
    acceptProps: { severity: 'danger' },
    rejectProps: { severity: 'secondary', outlined: true },
    accept: async () => {
      try {
        await projectsApi.removeMember(props.projectId, member.id)
        notify.success(`${memberName(member)} исключён из проекта`)
        emit('changed')
      } catch (error) {
        notify.error(error, 'Не удалось исключить участника')
      }
    },
  })
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
    header="Участники проекта"
    :style="{ width: '540px' }"
    :breakpoints="{ '640px': '96vw' }"
    :draggable="false"
    dismissable-mask
    @update:visible="emit('update:visible', $event)"
  >
    <p class="section-label">В проекте сейчас · {{ members.length }}</p>

    <div v-if="members.length === 0" class="members-empty">Пока нет участников</div>
    <div v-else class="members-list custom-scroll">
      <div v-for="member in members" :key="member.id" class="member-item">
        <div class="member-info">
          <div class="member-name" :title="memberName(member)">{{ shortName(memberName(member)) }}</div>
          <div class="member-meta">{{ ROLE_LABELS[member.role] }} · {{ member.user?.email }}</div>
        </div>
        <span v-if="member.role === 'owner'" class="owner-mark">владелец</span>
        <Button
          v-else-if="canManage"
          icon="pi pi-user-minus"
          text
          rounded
          severity="danger"
          size="small"
          title="Исключить из проекта"
          @click="remove(member)"
        />
      </div>
    </div>

    <form v-if="canManage" class="add-form" @submit.prevent="add">
      <p class="section-label">Добавить участника</p>
      <AutoComplete
        v-model="query"
        :suggestions="suggestions"
        option-label="email"
        placeholder="Email или имя пользователя"
        class="input-red"
        fluid
        @complete="search"
      >
        <template #option="{ option }">
          <div class="suggestion">
            <span class="suggestion-name">{{ option.full_name }}</span>
            <span class="suggestion-email">{{ option.email }}</span>
          </div>
        </template>
      </AutoComplete>

      <div class="role-row">
        <label class="section-label" for="member-role">Роль:</label>
        <Select
          v-model="role"
          input-id="member-role"
          :options="MEMBER_ROLE_OPTIONS"
          option-label="label"
          option-value="value"
          class="input-red input-sm role-select"
        />
      </div>

      <div class="actions">
        <Button type="button" label="Закрыть" rounded outlined severity="secondary" @click="close" />
        <Button
          type="submit"
          label="Добавить"
          rounded
          :loading="submitting"
          :disabled="!query || (typeof query === 'string' && !query.trim())"
        />
      </div>
    </form>
    <div v-else class="actions">
      <Button type="button" label="Закрыть" rounded outlined severity="secondary" @click="close" />
    </div>
  </Dialog>
</template>

<style scoped>
.section-label {
  font-size: 12px;
  font-weight: 700;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  margin-bottom: 8px;
}

.members-list { max-height: 240px; overflow-y: auto; display: flex; flex-direction: column; gap: 10px; }

.member-item {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 10px 14px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
}
.member-info { min-width: 0; flex: 1; }
.member-name { font-weight: 700; color: #0f172a; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.member-meta { font-size: 12px; color: #64748b; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.owner-mark { font-size: 11px; color: #94a3b8; font-style: italic; flex-shrink: 0; }

.members-empty {
  padding: 24px 16px;
  text-align: center;
  color: #94a3b8;
  font-size: 14px;
  background: #f8fafc;
  border: 1px dashed #e2e8f0;
  border-radius: 10px;
}

.add-form {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 2px solid #fee2e2;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.suggestion { display: flex; flex-direction: column; }
.suggestion-name { font-weight: 600; }
.suggestion-email { font-size: 12px; color: #64748b; }

.role-row { display: flex; align-items: center; gap: 10px; }
.role-row .section-label { margin: 0; }
.role-select { width: 200px; }

.actions { display: flex; justify-content: flex-end; gap: 8px; margin-top: 8px; }
</style>
