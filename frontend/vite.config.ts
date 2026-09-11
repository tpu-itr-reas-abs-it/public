import { fileURLToPath, URL } from 'node:url'
import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  // Только для `npm run dev`: /api проксируется на бэкенд (см. .env).
  const devApiTarget = env.VITE_DEV_API_TARGET || 'http://176.109.108.93'

  return {
    plugins: [vue()],
    resolve: {
      alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) },
    },
    server: {
      host: true,
      port: 5174,
      proxy: {
        '/api': { target: devApiTarget, changeOrigin: true, ws: true },
      },
    },
  }
})
