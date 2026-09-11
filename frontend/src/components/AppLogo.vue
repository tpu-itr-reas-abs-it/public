<script setup lang="ts">
withDefaults(defineProps<{ height?: number }>(), { height: 50 })
</script>

<template>
  <img
    class="app-logo"
    src="/img/logo.png"
    alt="Логотип Abstract IT"
    :style="{ height: `${height}px` }"
  />
</template>

<style scoped>
.app-logo { width: auto; display: block; }
</style>
