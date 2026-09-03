import type { CatalogCategory, EstimateDetail, EstimatePreview, PublicEstimate } from '../api/types'
import { findOption } from '../utils/catalog'
import { formatCurrency, formatDateTime, formatQuantity } from '../utils/format'
import { useEstimateDraft } from '../context/EstimateDraftContext'

interface EstimateSummaryProps {
  catalog?: CatalogCategory[]
  preview: EstimatePreview | null
  loading?: boolean
  error?: string | null
  compact?: boolean
}

export default function EstimateSummary({ catalog = [], preview, loading = false, error = null, compact = false }: EstimateSummaryProps) {
  const { selectedItems, updateQuantity, removeItem } = useEstimateDraft()

  return (
    <aside className={compact ? 'summary-panel compact' : 'summary-panel'} aria-label="현재 견적 요약">
      <div className="summary-header">
        <span className="section-kicker">예상 견적</span>
        <strong>{selectedItems.length}개 선택</strong>
      </div>

      {selectedItems.length === 0 ? (
        <p className="muted">시공 항목을 선택하면 예상 금액이 표시됩니다.</p>
      ) : (
        <div className="selected-list">
          {selectedItems.map((selected) => {
            const found = findOption(catalog, selected.option_id)
            const previewItem = preview?.items.find((item) => item.option_id === selected.option_id)
            return (
              <div className="selected-row" key={selected.option_id}>
                <div>
                  <strong>{previewItem?.option_name ?? found?.option.name ?? '선택 옵션'}</strong>
                  <p>{previewItem ? `${previewItem.category_name} / ${previewItem.item_name}` : found ? `${found.category.name} / ${found.item.name}` : ''}</p>
                </div>
                <div className="quantity-line">
                  <label>
                    수량
                    <input
                      min="0.01"
                      step="0.01"
                      type="number"
                      value={selected.quantity}
                      onChange={(event) => updateQuantity(selected.option_id, event.target.value)}
                    />
                  </label>
                  <span>{previewItem?.unit ?? found?.option.unit}</span>
                </div>
                <div className="selected-total">
                  {previewItem ? formatCurrency(previewItem.line_total) : '-'}
                  <button className="text-button danger" type="button" onClick={() => removeItem(selected.option_id)}>
                    삭제
                  </button>
                </div>
              </div>
            )
          })}
        </div>
      )}

      {loading && <p className="notice">예상 금액을 계산하고 있습니다.</p>}
      {error && <p className="error-text">{error}</p>}

      <dl className="total-box">
        <div>
          <dt>공급가</dt>
          <dd>{formatCurrency(preview?.subtotal)}</dd>
        </div>
        <div>
          <dt>부가세</dt>
          <dd>{formatCurrency(preview?.vat_amount)}</dd>
        </div>
        <div className="grand-total">
          <dt>총 예상 금액</dt>
          <dd>{formatCurrency(preview?.total_amount)}</dd>
        </div>
      </dl>
      <p className="small-note">실제 계약 금액은 현장 조건, 자재, 일정에 따라 달라질 수 있습니다.</p>
    </aside>
  )
}

export function EstimateDetailTable({ estimate }: { estimate: EstimateDetail | PublicEstimate }) {
  const items = 'items' in estimate ? estimate.items : []
  return (
    <div className="detail-table" role="table" aria-label="견적 항목">
      <div className="detail-table-head" role="row">
        <span>항목</span>
        <span>수량</span>
        <span>단가</span>
        <span>금액</span>
      </div>
      {items.map((item, index) => {
        const categoryName = 'category_name_snapshot' in item ? item.category_name_snapshot : item.category_name
        const itemName = 'item_name_snapshot' in item ? item.item_name_snapshot : item.item_name
        const optionName = 'option_name_snapshot' in item ? item.option_name_snapshot : item.option_name
        const unit = 'unit_snapshot' in item ? item.unit_snapshot : item.unit
        const unitPrice = 'unit_price_snapshot' in item ? item.unit_price_snapshot : item.unit_price
        return (
          <div className="detail-table-row" role="row" key={`${optionName}-${index}`}>
            <div>
              <strong>{optionName}</strong>
              <p>{categoryName} / {itemName}</p>
            </div>
            <span>{formatQuantity(item.quantity)} {unit}</span>
            <span>{formatCurrency(unitPrice)}</span>
            <span>{formatCurrency(item.line_total)}</span>
          </div>
        )
      })}
    </div>
  )
}

export function EstimateTotals({ estimate }: { estimate: EstimateDetail | PublicEstimate }) {
  return (
    <dl className="total-box result-total">
      <div>
        <dt>공급가</dt>
        <dd>{formatCurrency(estimate.subtotal)}</dd>
      </div>
      <div>
        <dt>부가세</dt>
        <dd>{formatCurrency(estimate.vat_amount)}</dd>
      </div>
      <div className="grand-total">
        <dt>총 예상 금액</dt>
        <dd>{formatCurrency(estimate.total_amount)}</dd>
      </div>
    </dl>
  )
}

export function EstimateMeta({ estimate }: { estimate: EstimateDetail | PublicEstimate }) {
  const estimateNumber = estimate.estimate_number
  const createdAt = estimate.created_at
  const customerName = 'customer_name' in estimate ? estimate.customer_name : estimate.customer_name_masked
  return (
    <div className="result-meta">
      <div>
        <span>견적번호</span>
        <strong>{estimateNumber}</strong>
      </div>
      <div>
        <span>작성일</span>
        <strong>{formatDateTime(createdAt)}</strong>
      </div>
      <div>
        <span>고객명</span>
        <strong>{customerName}</strong>
      </div>
    </div>
  )
}
