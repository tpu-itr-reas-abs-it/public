import dayjs from 'dayjs'
import 'dayjs/locale/ru'
import utc from 'dayjs/plugin/utc'

dayjs.extend(utc)
dayjs.locale('ru')

export { dayjs }

const ISO_DATE = 'YYYY-MM-DD'

export function toApiDate(value: Date | string | null | undefined): string {
  if (!value) return ''
  return dayjs(value).format(ISO_DATE)
}

export function toDate(value: string | null | undefined): Date | null {
  return value ? dayjs(value, ISO_DATE).toDate() : null
}

export function todayIso(): string {
  return dayjs().format(ISO_DATE)
}

export function addDays(iso: string, days: number): string {
  return dayjs(iso).add(days, 'day').format(ISO_DATE)
}

export function formatDate(value: string | null | undefined): string {
  return value ? dayjs(value).format('DD.MM.YYYY') : ''
}

export function formatDateShort(value: string | null | undefined): string {
  return value ? dayjs(value).format('DD.MM') : ''
}

export function formatDateTime(value: string | null | undefined): string {
  if (!value) return ''
  const hasZone = value.endsWith('Z') || /[+-]\d{2}:\d{2}$/.test(value)
  const parsed = hasZone ? dayjs(value) : dayjs.utc(value).local()
  return parsed.format('DD.MM.YYYY HH:mm')
}

export function durationDays(start: string | null | undefined, end: string | null | undefined): number {
  if (!start || !end) return 0
  return dayjs(end).diff(dayjs(start), 'day') + 1
}

export function pluralDays(count: number): string {
  const abs = Math.abs(count)
  const mod10 = abs % 10
  const mod100 = abs % 100
  if (mod10 === 1 && mod100 !== 11) return `${count} день`
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 10 || mod100 >= 20)) return `${count} дня`
  return `${count} дней`
}

export function pluralTasks(count: number): string {
  const mod10 = count % 10
  const mod100 = count % 100
  if (mod10 === 1 && mod100 !== 11) return `${count} задача`
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 10 || mod100 >= 20)) return `${count} задачи`
  return `${count} задач`
}

export function initials(user: { full_name?: string | null; email?: string | null } | null): string {
  if (!user) return '?'
  const name = (user.full_name ?? '').trim()
  if (name) {
    const parts = name.split(/\s+/)
    if (parts.length === 1) return parts[0]!.slice(0, 2).toUpperCase()
    return (parts[0]![0]! + parts[1]![0]!).toUpperCase()
  }
  return (user.email ?? '').slice(0, 2).toUpperCase() || '?'
}

export function shortName(full: string | null | undefined): string {
  if (!full) return ''
  const s = String(full).trim()
  if (s.includes('@')) return s.split('@')[0]!
  const clean = s.replace(/\s*\([^)]*\)\s*$/, '').trim()
  const parts = clean.split(/\s+/).filter(Boolean)
  return parts.at(-1) ?? ''
}

export function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}
