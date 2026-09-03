import type { CatalogCategory, CatalogItem, CatalogOption } from '../api/types'

export function findOption(catalog: CatalogCategory[], optionId: number): { category: CatalogCategory; item: CatalogItem; option: CatalogOption } | null {
  for (const category of catalog) {
    for (const item of category.items) {
      const option = item.options.find((candidate) => candidate.id === optionId)
      if (option) return { category, item, option }
    }
  }
  return null
}
