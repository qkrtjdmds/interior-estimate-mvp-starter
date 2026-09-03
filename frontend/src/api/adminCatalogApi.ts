import type { MoneyValue } from './types'
import { adminApiClient } from './adminApi'

export interface AdminCategory {
  id: number
  name: string
  description: string | null
  active: boolean
  customer_visible: boolean
  sort_order: number
  created_at: string
  updated_at: string
}

export interface AdminItem {
  id: number
  category_id: number
  name: string
  description: string | null
  active: boolean
  customer_visible: boolean
  sort_order: number
  created_at: string
  updated_at: string
}

export interface AdminOption {
  id: number
  item_id: number
  name: string
  description: string | null
  unit: string
  default_price: MoneyValue
  recommended: boolean
  active: boolean
  customer_visible: boolean
  sort_order: number
  created_at: string
  updated_at: string
}

export interface CategoryPayload {
  name: string
  description?: string | null
  active?: boolean
  customer_visible?: boolean
  sort_order?: number
}

export interface ItemPayload extends CategoryPayload {
  category_id: number
}

export interface OptionPayload extends CategoryPayload {
  item_id: number
  unit: string
  default_price: string
  recommended?: boolean
}

export async function fetchAdminCategories(): Promise<AdminCategory[]> {
  const { data } = await adminApiClient.get<AdminCategory[]>('/api/categories', { params: { limit: 100 } })
  return data
}

export async function createAdminCategory(payload: CategoryPayload): Promise<AdminCategory> {
  const { data } = await adminApiClient.post<AdminCategory>('/api/categories', payload)
  return data
}

export async function updateAdminCategory(categoryId: number, payload: Partial<CategoryPayload>): Promise<AdminCategory> {
  const { data } = await adminApiClient.patch<AdminCategory>(`/api/categories/${categoryId}`, payload)
  return data
}

export async function fetchAdminItems(categoryId?: number): Promise<AdminItem[]> {
  const params: Record<string, number> = { limit: 100 }
  if (categoryId) params.category_id = categoryId
  const { data } = await adminApiClient.get<AdminItem[]>('/api/items', { params })
  return data
}

export async function createAdminItem(payload: ItemPayload): Promise<AdminItem> {
  const { data } = await adminApiClient.post<AdminItem>('/api/items', payload)
  return data
}

export async function updateAdminItem(itemId: number, payload: Partial<ItemPayload>): Promise<AdminItem> {
  const { data } = await adminApiClient.patch<AdminItem>(`/api/items/${itemId}`, payload)
  return data
}

export async function fetchAdminOptions(itemId?: number): Promise<AdminOption[]> {
  const params: Record<string, number> = { limit: 100 }
  if (itemId) params.item_id = itemId
  const { data } = await adminApiClient.get<AdminOption[]>('/api/options', { params })
  return data
}

export async function createAdminOption(payload: OptionPayload): Promise<AdminOption> {
  const { data } = await adminApiClient.post<AdminOption>('/api/options', payload)
  return data
}

export async function updateAdminOption(optionId: number, payload: Partial<OptionPayload>): Promise<AdminOption> {
  const { data } = await adminApiClient.patch<AdminOption>(`/api/options/${optionId}`, payload)
  return data
}