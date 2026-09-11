<script setup lang="ts">
import AppLogo from '@/components/AppLogo.vue'
import type { FeatureItem } from '@/types/ui'

withDefaults(
  defineProps<{
    title: string
    description: string
    features: FeatureItem[]
    cardTitle?: string
    cardSubtitle: string
    scrollable?: boolean
  }>(),
  { cardTitle: 'Abstract IT', scrollable: false },
)
</script>

<template>
  <div class="auth-container">
    <div class="left-content">
      <AppLogo class="logo" />
      <h2>{{ title }}</h2>
      <p>{{ description }}</p>
      <ul class="features-list">
        <li v-for="item in features" :key="item.text" class="feature-item">
          <span class="feature-dot" :class="item.color" />
          <span>{{ item.text }}</span>
        </li>
      </ul>
    </div>

    <div class="auth-card" :class="{ scrollable }">
      <h1 class="aut_logo_name">{{ cardTitle }}</h1>
      <p class="auth-subtitle">{{ cardSubtitle }}</p>
      <slot />
    </div>
  </div>
</template>

<style scoped>
.auth-container {
  display: flex;
  height: 100vh;
  width: 100%;
  position: relative;
  overflow: hidden;
  background: #FFFFFF;
}

.auth-container::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  width: 65%;
  height: 100%;
  background: linear-gradient(135deg, var(--primary-dark), var(--primary), rgba(255, 255, 255, 0.1) 100%);
  z-index: 1;
}

.left-content {
  position: absolute;
  left: 0;
  top: 0;
  width: 65%;
  height: 100%;
  z-index: 2;
  padding: 60px 0 0 60px;
  color: #FFFFFF;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.left-content .logo {
  position: absolute;
  top: 40px;
  left: 40px;
}

.left-content h2 {
  font-size: 48px;
  font-weight: 400;
  margin-bottom: 16px;
  line-height: 58px;
}

.left-content > p {
  font-size: 20px;
  font-weight: 400;
  max-width: 486px;
  line-height: 24px;
  margin-bottom: 60px;
}

.features-list { list-style: none; padding: 0; margin: 0; }

.feature-item {
  display: flex;
  align-items: center;
  gap: 20px;
  margin-bottom: 47px;
  font-size: 20px;
  font-weight: 400;
}

.feature-dot { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }
.feature-dot.blue { background: #4F8FF0; }
.feature-dot.green { background: #4FF07D; }
.feature-dot.yellow { background: #F0E04F; }

.auth-card {
  position: relative;
  z-index: 2;
  margin-left: auto;
  width: 648px;
  max-width: 100%;
  height: 100%;
  background: #FFFFFF;
  padding: 60px 85px 50px;
  display: flex;
  flex-direction: column;
  box-shadow: -10px 0 30px rgba(0, 0, 0, 0.1);
  overflow-y: auto;
}

.aut_logo_name {
  font-size: 32px;
  color: #000000;
  margin: 60px 0 8px 0;
  font-weight: 400;
}

.auth-subtitle {
  font-size: 15px;
  color: #000000;
  margin-bottom: 40px;
}

@media (max-width: 1100px) {
  .auth-card { width: 560px; padding: 40px 48px 40px; }
}
@media (max-width: 860px) {
  .auth-container::before, .left-content { display: none; }
  .auth-card { width: 100%; padding: 32px 24px; box-shadow: none; }
  .aut_logo_name { margin-top: 20px; }
}
</style>
