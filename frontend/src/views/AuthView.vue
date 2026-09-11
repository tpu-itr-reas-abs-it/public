<script setup lang="ts">
import { computed, reactive, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import InputText from 'primevue/inputtext'
import Password from 'primevue/password'
import Button from 'primevue/button'
import AuthLayout from '@/components/auth/AuthLayout.vue'
import { useAuthStore } from '@/stores/auth'
import { useNotify } from '@/composables/useNotify'
import type { FeatureItem } from '@/types/ui'

const props = defineProps<{ mode: 'login' | 'register' }>()

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()
const notify = useNotify()

const FEATURES: FeatureItem[] = [
  { color: 'blue', text: 'Диаграмма Ганта в реальном времени' },
  { color: 'green', text: 'Зависимости между задачами' },
  { color: 'yellow', text: 'Контроль просрочек и рисков срыва срока' },
]

const form = reactive({ email: '', password: '', full_name: '' })
const isLogin = computed(() => props.mode === 'login')

watch(() => props.mode, () => {
  form.password = ''
})

async function submit() {
  const email = form.email.trim()
  if (!email) return notify.warn('Укажите email')
  if (form.password.length < 8) return notify.warn('Пароль — минимум 8 символов')
  if (!isLogin.value && !form.full_name.trim()) return notify.warn('Укажите полное имя')

  try {
    if (isLogin.value) await auth.login(email, form.password)
    else await auth.register(email, form.password, form.full_name.trim())

    const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : null
    await router.replace(redirect ?? { name: 'projects' })
  } catch (error) {
    notify.error(error, isLogin.value ? 'Ошибка авторизации' : 'Ошибка регистрации')
  }
}
</script>

<template>
  <AuthLayout
    title="Проекты под контролем"
    description="Планируйте задачи, назначайте ответственных и следите за сроками на живой диаграмме Ганта"
    :features="FEATURES"
    :card-subtitle="isLogin ? 'Вход в систему' : 'Создание аккаунта'"
  >
    <div class="auth-tabs">
      <RouterLink :to="{ name: 'login' }" class="auth-tab" :class="{ active: isLogin }">
        Вход
      </RouterLink>
      <RouterLink :to="{ name: 'register' }" class="auth-tab" :class="{ active: !isLogin }">
        Регистрация
      </RouterLink>
    </div>

    <form class="auth-form" @submit.prevent="submit">
      <div class="form-group">
        <label for="auth-email">Email</label>
        <InputText
          id="auth-email"
          v-model="form.email"
          type="email"
          placeholder="user@example.com"
          autocomplete="email"
          required
        />
      </div>

      <div class="form-group">
        <label for="auth-password">Пароль</label>
        <Password
          v-model="form.password"
          input-id="auth-password"
          placeholder="Минимум 8 символов"
          :feedback="false"
          toggle-mask
          :input-props="{
            autocomplete: isLogin ? 'current-password' : 'new-password',
            required: true,
            minlength: 8,
          }"
        />
      </div>

      <div v-if="!isLogin" class="form-group">
        <label for="auth-fullname">Полное имя</label>
        <InputText
          id="auth-fullname"
          v-model="form.full_name"
          placeholder="Иван Петров"
          autocomplete="name"
          required
        />
      </div>

      <Button
        type="submit"
        class="btn-auth"
        :label="isLogin ? (auth.loading ? 'Вход...' : 'Войти') : auth.loading ? 'Создание...' : 'Зарегистрироваться'"
        :loading="auth.loading"
      />
    </form>
  </AuthLayout>
</template>

<style scoped>
.auth-tabs {
  display: flex;
  gap: 10px;
  margin-bottom: 40px;
  border-bottom: 1px solid #D9D9D9;
  padding-bottom: 10px;
}

.auth-tab {
  padding: 10px 20px;
  background: #FFFFFF;
  border: none;
  font-size: 15px;
  color: #000000;
  cursor: pointer;
  border-radius: 6px;
  font-weight: 400;
  text-decoration: none;
  transition: all 0.2s;
}

.auth-tab.active {
  background: #F1F1F1;
  font-weight: 500;
}

.form-group { margin-bottom: 30px; }

.form-group label {
  display: block;
  font-size: 15px;
  color: #000000;
  margin-bottom: 10px;
  font-weight: 400;
}
</style>
