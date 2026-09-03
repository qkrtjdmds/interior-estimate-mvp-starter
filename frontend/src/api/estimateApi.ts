import { apiClient } from './client'
import type { CatalogCategory, EstimateCreatePayload, EstimateDetail, EstimateLineInput, EstimatePreview, PublicEstimate } from './types'

export async function fetchCatalog(): Promise<CatalogCategory[]> {
  const { data } = await apiClient.get<CatalogCategory[]>('/api/catalog')
  return data
}

export async function previewEstimate(items: EstimateLineInput[]): Promise<EstimatePreview> {
  const { data } = await apiClient.post<EstimatePreview>('/api/estimates/preview', { items })
  return data
}

export async function createEstimate(payload: EstimateCreatePayload): Promise<EstimateDetail> {
  const { data } = await apiClient.post<EstimateDetail>('/api/estimates', payload)
  return data
}

export async function fetchSharedEstimate(shareToken: string): Promise<PublicEstimate> {
  const { data } = await apiClient.get<PublicEstimate>('/api/public/estimate', {
    headers: { 'X-Estimate-Share-Token': shareToken },
  })
  return data
}

export async function downloadSharedEstimatePdf(shareToken: string): Promise<Blob> {
  const { data } = await apiClient.get<Blob>('/api/public/estimate/pdf', {
    headers: { 'X-Estimate-Share-Token': shareToken },
    responseType: 'blob',
  })
  return data
}
