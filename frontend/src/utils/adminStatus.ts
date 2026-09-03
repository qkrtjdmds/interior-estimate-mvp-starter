export const ADMIN_STATUS_OPTIONS = [
  { value: 'draft', label: '신규 접수' },
  { value: 'submitted', label: '상담 중' },
  { value: 'confirmed', label: '견적 확정' },
  { value: 'completed', label: '완료' },
  { value: 'cancelled', label: '취소' },
]

export function statusLabel(status: string): string {
  return ADMIN_STATUS_OPTIONS.find((option) => option.value === status)?.label ?? status
}

export function statusClass(status: string): string {
  return `status-badge status-${status}`
}
