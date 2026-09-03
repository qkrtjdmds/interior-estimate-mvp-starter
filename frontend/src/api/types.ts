export type MoneyValue = string | number

export interface CatalogOption {
  id: number
  name: string
  description: string | null
  unit: string
  default_price: MoneyValue
  recommended: boolean
  sort_order: number
}

export interface CatalogItem {
  id: number
  name: string
  description: string | null
  sort_order: number
  options: CatalogOption[]
}

export interface CatalogCategory {
  id: number
  name: string
  description: string | null
  sort_order: number
  items: CatalogItem[]
}

export interface EstimateLineInput {
  option_id: number
  quantity: string
  sort_order?: number
}

export interface EstimatePreviewItem {
  option_id: number
  category_name: string
  item_name: string
  option_name: string
  unit: string
  unit_price: MoneyValue
  quantity: MoneyValue
  line_total: MoneyValue
  sort_order: number
}

export interface EstimatePreview {
  items: EstimatePreviewItem[]
  subtotal: MoneyValue
  vat_rate: MoneyValue
  vat_amount: MoneyValue
  total_amount: MoneyValue
}

export interface EstimateItemResponse {
  id: number
  estimate_id: number
  option_id: number | null
  category_name_snapshot: string
  item_name_snapshot: string
  option_name_snapshot: string
  description_snapshot: string | null
  unit_snapshot: string
  unit_price_snapshot: MoneyValue
  quantity: MoneyValue
  line_total: MoneyValue
  sort_order: number
  created_at: string
  updated_at: string
}

export interface EstimateDetail {
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
  notes: string | null
  subtotal: MoneyValue
  vat_rate: MoneyValue
  vat_amount: MoneyValue
  total_amount: MoneyValue
  valid_until: string | null
  created_at: string
  updated_at: string
  items: EstimateItemResponse[]
}

export interface EstimateCreatePayload {
  customer_name: string
  customer_phone?: string | null
  customer_email?: string | null
  housing_type?: string | null
  floor_area_pyeong?: string | null
  renovation_scope?: string | null
  preferred_timeline?: string | null
  project_address?: string | null
  notes?: string | null
  items: EstimateLineInput[]
}

export interface PublicEstimateItem {
  category_name: string
  item_name: string
  option_name: string
  description: string | null
  unit: string
  unit_price: MoneyValue
  quantity: MoneyValue
  line_total: MoneyValue
  sort_order: number
}

export interface PublicEstimate {
  estimate_number: string
  status: string
  customer_name_masked: string
  created_at: string
  valid_until: string | null
  items: PublicEstimateItem[]
  subtotal: MoneyValue
  vat_rate: MoneyValue
  vat_amount: MoneyValue
  total_amount: MoneyValue
}
