import type { MoneyValue } from '../api/types'

export function toNumber(value: MoneyValue | null | undefined): number {
  if (value === null || value === undefined || value === '') return 0
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : 0
}

export function formatCurrency(value: MoneyValue | null | undefined): string {
  return `${Math.round(toNumber(value)).toLocaleString('ko-KR')}원`
}

export function formatQuantity(value: MoneyValue | null | undefined): string {
  const parsed = toNumber(value)
  if (Number.isInteger(parsed)) return parsed.toLocaleString('ko-KR')
  return parsed.toLocaleString('ko-KR', { maximumFractionDigits: 2 })
}

export function formatDateTime(value: string | null | undefined): string {
  if (!value) return '-'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '-'
  return new Intl.DateTimeFormat('ko-KR', { dateStyle: 'medium', timeStyle: 'short' }).format(date)
}

export function formatArea(value: string | number | null | undefined): string {
  const parsed = toNumber(value)
  return parsed > 0 ? `${formatQuantity(parsed)}평` : '-'
}
