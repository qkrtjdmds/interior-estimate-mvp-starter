import axios from 'axios'
import { API_BASE_URL, getApiErrorMessage } from './client'
import type { EstimateDetail, MoneyValue } from './types'

export const ADMIN_TOKEN_STORAGE_KEY = 'interior-admin-access-token'

export interface AdminUser {
  id: number
  email: string
  active: boolean
  last_login_at: string | null
  created_at: string
}

export interface LoginResponse {
  access_token: string
  token_type: string
  expires_in: number
}

export interface EstimateListItem {
  id: number
  estimate_number: string
  customer_name: string
  customer_phone: string | null
  customer_email: string | null
  housing_type: string | null
  floor_area_pyeong: MoneyValue | null
  renovation_scope: string | null
  preferred_timeline: string | null
  project_address: string | null
  status: string
  subtotal: MoneyValue
  vat_rate: MoneyValue
  vat_amount: MoneyValue
  total_amount: MoneyValue
  valid_until: string | null
  created_at: string
  updated_at: string
}

export interface EstimateShareStatus {
  active: boolean
  expires_at: string
  revoked_at: string | null
  created_at: string
  last_accessed_at: string | null
  access_count: number
}

export interface EstimateShareCreated {
  share_token: string
  expires_at: string
  created_at: string
  notice: string
}

export interface EstimateListParams {
  status?: string
  customer_name?: string
  estimate_number?: string
  skip?: number
  limit?: number
}

export const adminApiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: { 'Content-Type': 'application/json' },
})

adminApiClient.interceptors.request.use((config) => {
  const token = window.sessionStorage.getItem(ADMIN_TOKEN_STORAGE_KEY)
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

adminApiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (axios.isAxiosError(error) && error.response?.status === 401) {
      window.sessionStorage.removeItem(ADMIN_TOKEN_STORAGE_KEY)
      window.dispatchEvent(new Event('admin-auth-expired'))
    }
    return Promise.reject(error)
  },
)

export async function loginAdmin(email: string, password: string): Promise<LoginResponse> {
  const { data } = await adminApiClient.post<LoginResponse>('/api/auth/login', { email, password })
  return data
}

export async function fetchCurrentAdmin(): Promise<AdminUser> {
  const { data } = await adminApiClient.get<AdminUser>('/api/auth/me')
  return data
}

export async function fetchAdminEstimates(params: EstimateListParams): Promise<EstimateListItem[]> {
  const { data } = await adminApiClient.get<EstimateListItem[]>('/api/estimates', { params })
  return data
}

export async function fetchAdminEstimate(estimateId: number): Promise<EstimateDetail> {
  const { data } = await adminApiClient.get<EstimateDetail>(`/api/estimates/${estimateId}`)
  return data
}

export async function updateEstimateStatus(estimateId: number, status: string): Promise<EstimateDetail> {
  const { data } = await adminApiClient.patch<EstimateDetail>(`/api/estimates/${estimateId}`, { status })
  return data
}

export async function createEstimateShare(estimateId: number, expiresInDays = 30): Promise<EstimateShareCreated> {
  const { data } = await adminApiClient.post<EstimateShareCreated>(`/api/estimates/${estimateId}/share`, { expires_in_days: expiresInDays })
  return data
}

export async function fetchEstimateShareStatus(estimateId: number): Promise<EstimateShareStatus> {
  const { data } = await adminApiClient.get<EstimateShareStatus>(`/api/estimates/${estimateId}/share`)
  return data
}

export async function revokeEstimateShare(estimateId: number): Promise<void> {
  await adminApiClient.delete(`/api/estimates/${estimateId}/share`)
}

export async function downloadAdminEstimatePdf(estimateId: number): Promise<{ blob: Blob; filename: string | null }> {
  const response = await adminApiClient.get<Blob>(`/api/estimates/${estimateId}/pdf`, { responseType: 'blob' })
  const disposition = response.headers['content-disposition']
  const filename = typeof disposition === 'string' ? disposition.match(/filename="?([^";]+)"?/)?.[1] ?? null : null
  return { blob: response.data, filename }
}

export function getAdminApiErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    if (error.response?.status === 401) return '아이디 또는 비밀번호를 확인해 주세요.'
    if (error.response?.status === 403) return '접근 권한이 없는 관리자 계정입니다.'
  }
  return getApiErrorMessage(error)
}
