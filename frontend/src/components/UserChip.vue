<script setup lang="ts">
import { initials } from '@/utils/format'
import type { UserPublic } from '@/types/api'

withDefaults(defineProps<{ user: UserPublic; size?: 'lg' | 'sm' }>(), { size: 'lg' })
</script>

<template>
  <div class="user-chip" :class="size">
    <div class="user-chip-avatar">{{ initials(user) }}</div>
    <div class="user-chip-text">
      <div class="user-chip-name" :title="user.full_name || ''">
        {{ user.full_name || 'Пользователь' }}
      </div>
      <div v-if="size === 'lg'" class="user-chip-email" :title="user.email">{{ user.email }}</div>
    </div>
  </div>
</template>

<style scoped>
.user-chip {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 14px 22px 14px 14px;
  background: #F1F1F1;
  border-radius: 100px;
  font-size: 16px;
  color: var(--text);
  max-width: 100%;
  min-width: 0;
}

.user-chip-avatar {
  width: 52px;
  height: 52px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--primary-dark), var(--primary));
  color: #fff;
  font-weight: 700;
  font-size: 22px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.user-chip-text { min-width: 0; }

.user-chip-name {
  font-weight: 700;
  font-size: 18px;
  line-height: 1.2;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.user-chip-email {
  color: var(--text-light);
  font-size: 14px;
  margin-top: 2px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.user-chip.sm {
  gap: 8px;
  padding: 6px 12px;
  background: rgba(255, 255, 255, 0.2);
  color: #fff;
  font-size: 14px;
  backdrop-filter: blur(4px);
  border-radius: 8px;
}
.user-chip.sm .user-chip-avatar {
  width: 22px;
  height: 22px;
  background: #fff;
  color: #c64747;
  font-size: 11px;
}
.user-chip.sm .user-chip-name { font-weight: 500; font-size: 14px; }
</style>
