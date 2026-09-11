import { createApp } from 'vue'
import { createPinia } from 'pinia'
import PrimeVue from 'primevue/config'
import ToastService from 'primevue/toastservice'
import ConfirmationService from 'primevue/confirmationservice'
import Tooltip from 'primevue/tooltip'

import 'primeicons/primeicons.css'
import '@/assets/main.css'

import App from './App.vue'
import router from './router'
import { preset } from '@/assets/theme'
import { ruLocale } from '@/assets/locale'

const app = createApp(App)

app.use(createPinia())
app.use(PrimeVue, {
  theme: {
    preset,
    options: {
      darkModeSelector: false,
      cssLayer: { name: 'primevue', order: 'theme, base, primevue, app' },
    },
  },
  locale: ruLocale,
})
app.use(ToastService)
app.use(ConfirmationService)
app.directive('tooltip', Tooltip)
app.use(router)

app.mount('#app')
