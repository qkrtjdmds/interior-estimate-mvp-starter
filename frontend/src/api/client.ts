import axios, { AxiosError } from 'axios'

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000'

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: { 'Content-Type': 'application/json' },
})

export function getApiErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const axiosError = error as AxiosError<{ detail?: unknown }>
    const status = axiosError.response?.status
    const detail = axiosError.response?.data?.detail
    if (status === 404) return '요청한 정보를 찾을 수 없습니다.'
    if (status === 409) return '현재 선택한 항목으로 처리할 수 없습니다. 항목을 다시 확인해 주세요.'
    if (status === 410) return '공유 링크가 만료되었습니다.'
    if (status === 422) return '입력값을 다시 확인해 주세요.'
    if (status === 503) return 'PDF 생성 준비가 완료되지 않았습니다. 관리자에게 문의해 주세요.'
    if (typeof detail === 'string') return detail
    if (status) return `서버 요청에 실패했습니다. 상태 코드: ${status}`
    return '서버에 연결할 수 없습니다. 백엔드 실행 상태를 확인해 주세요.'
  }
  return '알 수 없는 오류가 발생했습니다.'
}
