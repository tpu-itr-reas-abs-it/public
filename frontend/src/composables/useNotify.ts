import { useToast } from 'primevue/usetoast'
import { errorMessage } from '@/api/http'

export function useNotify() {
  const toast = useToast()
  return {
    success(detail: string, summary = 'Готово') {
      toast.add({ severity: 'success', summary, detail, life: 3000 })
    },
    info(detail: string, summary = 'Обновление') {
      toast.add({ severity: 'info', summary, detail, life: 4000 })
    },
    warn(detail: string, summary = 'Внимание') {
      toast.add({ severity: 'warn', summary, detail, life: 6000 })
    },
    error(error: unknown, fallback = 'Что-то пошло не так') {
      toast.add({ severity: 'error', summary: 'Ошибка', detail: errorMessage(error, fallback), life: 5000 })
    },
  }
}
