import { FormEvent, useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import {
  createEstimateShare,
  downloadAdminEstimatePdf,
  fetchAdminEstimate,
  fetchEstimateShareStatus,
  getAdminApiErrorMessage,
  revokeEstimateShare,
  updateEstimateConsultation,
  updateEstimateStatus,
} from '../api/adminApi'
import type { EstimateConsultationUpdateItem, EstimateShareStatus } from '../api/adminApi'
import { fetchAdminCategories, fetchAdminItems, fetchAdminOptions } from '../api/adminCatalogApi'
import type { AdminCategory, AdminItem, AdminOption } from '../api/adminCatalogApi'
import { FRONTEND_BASE_URL } from '../api/client'
import type { EstimateDetail, EstimateItemResponse } from '../api/types'
import ApiState from '../components/ApiState'
import { EstimateDetailTable, EstimateMeta, EstimateTotals } from '../components/EstimateSummary'
import { ADMIN_STATUS_OPTIONS, statusClass, statusLabel } from '../utils/adminStatus'
import { formatArea, formatCurrency, formatDateTime, toNumber } from '../utils/format'

const EDITABLE_STATUS = 'submitted'
const VAT_RATE = 0.1

interface EditState {
  housing_type: string
  floor_area_pyeong: string
  renovation_scope: string
  project_address: string
  preferred_timeline: string
  admin_consultation_note: string
  items: EstimateConsultationUpdateItem[]
}

function editStateFromEstimate(estimate: EstimateDetail): EditState {
  return {
    housing_type: estimate.housing_type ?? '',
    floor_area_pyeong: estimate.floor_area_pyeong === null ? '' : String(estimate.floor_area_pyeong),
    renovation_scope: estimate.renovation_scope ?? '',
    project_address: estimate.project_address ?? '',
    preferred_timeline: estimate.preferred_timeline ?? '',
    admin_consultation_note: estimate.admin_consultation_note ?? '',
    items: estimate.items
      .filter((item) => item.option_id !== null)
      .map((item, index) => ({ option_id: item.option_id as number, quantity: String(item.quantity), sort_order: index + 1 })),
  }
}

function currentItemLabel(item: EstimateItemResponse): string {
  return `${item.category_name_snapshot} / ${item.item_name_snapshot} / ${item.option_name_snapshot}`
}

export default function AdminEstimateDetailPage() {
  const params = useParams()
  const navigate = useNavigate()
  const estimateId = Number(params.estimateId)
  const [estimate, setEstimate] = useState<EstimateDetail | null>(null)
  const [shareStatus, setShareStatus] = useState<EstimateShareStatus | null>(null)
  const [shareLink, setShareLink] = useState('')
  const [manualCopyVisible, setManualCopyVisible] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [statusSaving, setStatusSaving] = useState(false)
  const [shareLoading, setShareLoading] = useState(false)
  const [pdfLoading, setPdfLoading] = useState(false)
  const [actionMessage, setActionMessage] = useState<string | null>(null)
  const [editing, setEditing] = useState(false)
  const [editState, setEditState] = useState<EditState | null>(null)
  const [editCatalogLoading, setEditCatalogLoading] = useState(false)
  const [editSaving, setEditSaving] = useState(false)
  const [editError, setEditError] = useState<string | null>(null)
  const [categories, setCategories] = useState<AdminCategory[]>([])
  const [items, setItems] = useState<AdminItem[]>([])
  const [options, setOptions] = useState<AdminOption[]>([])

  const canCreateShare = estimate ? ['submitted', 'confirmed', 'completed'].includes(estimate.status) : false
  const canEdit = estimate?.status === EDITABLE_STATUS
  const safeEstimateId = Number.isFinite(estimateId) ? estimateId : 0

  function load() {
    if (!safeEstimateId) {
      setError('잘못된 견적 주소입니다.')
      setLoading(false)
      return
    }
    setLoading(true)
    setError(null)
    setShareStatus(null)
    setActionMessage(null)
    fetchAdminEstimate(safeEstimateId)
      .then((estimateData) => {
        setEstimate(estimateData)
        return fetchEstimateShareStatus(safeEstimateId)
          .then((shareData) => setShareStatus(shareData.active ? shareData : null))
          .catch((shareError) => {
            setShareStatus(null)
            setActionMessage(getAdminApiErrorMessage(shareError))
          })
      })
      .catch((requestError) => {
        setEstimate(null)
        setShareStatus(null)
        setError(getAdminApiErrorMessage(requestError))
      })
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    load()
  }, [safeEstimateId])

  const customerLinks = useMemo(() => {
    if (!estimate) return { phone: '', email: '' }
    return {
      phone: estimate.customer_phone ? `tel:${estimate.customer_phone.replace(/[^0-9+]/g, '')}` : '',
      email: estimate.customer_email ? `mailto:${estimate.customer_email}` : '',
    }
  }, [estimate])

  const optionById = useMemo(() => new Map(options.map((option) => [option.id, option])), [options])
  const itemById = useMemo(() => new Map(items.map((item) => [item.id, item])), [items])
  const categoryById = useMemo(() => new Map(categories.map((category) => [category.id, category])), [categories])
  const editableOptions = useMemo(() => options.filter((option) => option.active && (itemById.get(option.item_id)?.active ?? false) && (categoryById.get(itemById.get(option.item_id)?.category_id ?? 0)?.active ?? false)), [categoryById, itemById, options])

  const editPreview = useMemo(() => {
    if (!editState) return { subtotal: 0, vat: 0, total: 0 }
    const subtotal = editState.items.reduce((sum, item) => sum + toNumber(optionById.get(item.option_id)?.default_price) * toNumber(item.quantity), 0)
    const vat = Math.round(subtotal * VAT_RATE)
    return { subtotal, vat, total: subtotal + vat }
  }, [editState, optionById])

  async function handleStatusChange(nextStatus: string) {
    if (!estimate || nextStatus === estimate.status) return
    if (nextStatus === 'cancelled' && !window.confirm('견적을 취소 상태로 변경할까요? 활성 공유 링크가 차단될 수 있습니다.')) return
    setStatusSaving(true)
    setActionMessage(null)
    try {
      const updated = await updateEstimateStatus(estimate.id, nextStatus)
      setEstimate(updated)
      setEditing(false)
      setEditState(null)
      setActionMessage('상태가 변경되었습니다.')
      if (nextStatus === 'cancelled') setShareStatus(null)
    } catch (requestError) {
      setActionMessage(getAdminApiErrorMessage(requestError))
    } finally {
      setStatusSaving(false)
    }
  }

  async function startEditing() {
    if (!estimate || !canEdit) return
    setEditError(null)
    setActionMessage(null)
    setEditCatalogLoading(true)
    try {
      const [categoryData, itemData, optionData] = await Promise.all([fetchAdminCategories(), fetchAdminItems(), fetchAdminOptions()])
      setCategories(categoryData)
      setItems(itemData)
      setOptions(optionData)
      setEditState(editStateFromEstimate(estimate))
      setEditing(true)
    } catch (requestError) {
      setEditError(getAdminApiErrorMessage(requestError))
    } finally {
      setEditCatalogLoading(false)
    }
  }

  function updateEditState(patch: Partial<EditState>) {
    setEditState((current) => (current ? { ...current, ...patch } : current))
  }

  function updateEditItem(index: number, patch: Partial<EstimateConsultationUpdateItem>) {
    setEditState((current) => {
      if (!current) return current
      const nextItems = current.items.map((item, itemIndex) => (itemIndex === index ? { ...item, ...patch } : item))
      return { ...current, items: nextItems.map((item, sortIndex) => ({ ...item, sort_order: sortIndex + 1 })) }
    })
  }

  function addEditItem() {
    const firstAvailable = editableOptions.find((option) => !editState?.items.some((item) => item.option_id === option.id))
    if (!firstAvailable) {
      setEditError('추가할 수 있는 활성 옵션이 없습니다.')
      return
    }
    setEditState((current) => current ? { ...current, items: [...current.items, { option_id: firstAvailable.id, quantity: '1.00', sort_order: current.items.length + 1 }] } : current)
  }

  function removeEditItem(index: number) {
    setEditState((current) => {
      if (!current) return current
      return { ...current, items: current.items.filter((_, itemIndex) => itemIndex !== index).map((item, sortIndex) => ({ ...item, sort_order: sortIndex + 1 })) }
    })
  }

  function validateEdit(): string | null {
    if (!editState) return '수정할 견적 정보를 불러오지 못했습니다.'
    if (!editState.housing_type.trim()) return '주거 형태를 입력해 주세요.'
    if (!editState.floor_area_pyeong || Number(editState.floor_area_pyeong) <= 0) return '평수는 0보다 큰 숫자로 입력해 주세요.'
    if (!editState.renovation_scope.trim()) return '시공 범위를 입력해 주세요.'
    if (!editState.project_address.trim()) return '시공 지역을 입력해 주세요.'
    if (!editState.preferred_timeline.trim()) return '희망 시기를 입력해 주세요.'
    if (editState.items.length === 0) return '시공 옵션을 하나 이상 추가해 주세요.'
    if (new Set(editState.items.map((item) => item.option_id)).size !== editState.items.length) return '같은 옵션은 한 번만 추가할 수 있습니다.'
    if (editState.items.some((item) => !item.quantity || Number(item.quantity) <= 0)) return '옵션별 수량은 0보다 큰 숫자로 입력해 주세요.'
    return null
  }

  async function handleEditSubmit(event: FormEvent) {
    event.preventDefault()
    if (!estimate || !editState || editSaving) return
    const validationError = validateEdit()
    if (validationError) {
      setEditError(validationError)
      return
    }
    setEditSaving(true)
    setEditError(null)
    setActionMessage(null)
    try {
      const updated = await updateEstimateConsultation(estimate.id, {
        expected_updated_at: estimate.updated_at,
        housing_type: editState.housing_type.trim(),
        floor_area_pyeong: editState.floor_area_pyeong,
        renovation_scope: editState.renovation_scope.trim(),
        preferred_timeline: editState.preferred_timeline.trim(),
        project_address: editState.project_address.trim(),
        admin_consultation_note: editState.admin_consultation_note.trim() || null,
        items: editState.items.map((item, index) => ({ option_id: item.option_id, quantity: item.quantity, sort_order: index + 1 })),
      })
      setEstimate(updated)
      setEditing(false)
      setEditState(null)
      setActionMessage('견적 수정이 저장되었습니다.')
    } catch (requestError) {
      setEditError(getAdminApiErrorMessage(requestError))
    } finally {
      setEditSaving(false)
    }
  }

  async function handleCreateShare() {
    if (!estimate) return
    setShareLoading(true)
    setActionMessage(null)
    setManualCopyVisible(false)
    try {
      const created = await createEstimateShare(estimate.id, 30)
      const link = `${FRONTEND_BASE_URL}/share#token=${created.share_token}`
      setShareLink(link)
      setShareStatus({ active: true, expires_at: created.expires_at, revoked_at: null, created_at: created.created_at, last_accessed_at: null, access_count: 0 })
      try {
        await navigator.clipboard.writeText(link)
        setActionMessage('공유 링크를 생성하고 복사했습니다.')
      } catch {
        setManualCopyVisible(true)
        setActionMessage('공유 링크를 생성했습니다. 아래 입력창에서 직접 복사해 주세요.')
      }
    } catch (requestError) {
      setActionMessage(getAdminApiErrorMessage(requestError))
    } finally {
      setShareLoading(false)
    }
  }

  async function handleRevokeShare() {
    if (!estimate) return
    if (!window.confirm('현재 활성 공유 링크를 폐기할까요?')) return
    setShareLoading(true)
    setActionMessage(null)
    try {
      await revokeEstimateShare(estimate.id)
      setShareStatus(null)
      setShareLink('')
      setActionMessage('공유 링크를 폐기했습니다.')
    } catch (requestError) {
      setActionMessage(getAdminApiErrorMessage(requestError))
    } finally {
      setShareLoading(false)
    }
  }

  async function handlePdfDownload() {
    if (!estimate) return
    setPdfLoading(true)
    setActionMessage(null)
    try {
      const { blob, filename } = await downloadAdminEstimatePdf(estimate.id)
      const url = window.URL.createObjectURL(blob)
      const anchor = document.createElement('a')
      anchor.href = url
      anchor.download = filename ?? `estimate_${estimate.estimate_number}.pdf`
      document.body.appendChild(anchor)
      anchor.click()
      anchor.remove()
      window.URL.revokeObjectURL(url)
      setActionMessage('PDF 다운로드를 시작했습니다.')
    } catch (requestError) {
      setActionMessage(getAdminApiErrorMessage(requestError))
    } finally {
      setPdfLoading(false)
    }
  }

  if (loading) return <main className="admin-content"><ApiState title="견적 상세를 불러오는 중" message="접수 내용을 확인하고 있습니다." /></main>
  if (error || !estimate) return <main className="admin-content"><ApiState title="견적을 찾을 수 없습니다" message={error ?? '요청한 견적이 없습니다.'} action={<button className="button ghost-button" type="button" onClick={() => navigate('/admin/estimates')}>목록으로</button>} /></main>

  return (
    <main className="admin-content">
      <header className="admin-page-header">
        <div><h1>견적 상세</h1><p>{estimate.estimate_number}</p></div>
        <Link className="button ghost-button" to="/admin/estimates">목록으로</Link>
      </header>

      <section className="admin-detail-grid">
        <div className="admin-panel">
          <div className="admin-panel-heading"><h2>기본 정보</h2><span className={statusClass(estimate.status)}>{statusLabel(estimate.status)}</span></div>
          <EstimateMeta estimate={estimate} />
          <EstimateTotals estimate={estimate} />
          <label>처리 상태<select value={estimate.status} disabled={statusSaving || editSaving} onChange={(event) => void handleStatusChange(event.target.value)}>{ADMIN_STATUS_OPTIONS.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}</select></label>
          {canEdit && !editing && <button className="button primary-button" type="button" disabled={editCatalogLoading} onClick={() => void startEditing()}>{editCatalogLoading ? '수정 준비 중' : '견적 수정'}</button>}
          {!canEdit && <p className="small-note">상담 중 상태에서만 견적 내용을 수정할 수 있습니다.</p>}
        </div>

        <div className="admin-panel">
          <h2>고객 정보</h2>
          <dl className="admin-info-list">
            <div><dt>이름</dt><dd>{estimate.customer_name}</dd></div>
            <div><dt>연락처</dt><dd>{customerLinks.phone ? <a href={customerLinks.phone}>{estimate.customer_phone}</a> : '-'}</dd></div>
            <div><dt>이메일</dt><dd>{customerLinks.email ? <a href={customerLinks.email}>{estimate.customer_email}</a> : '-'}</dd></div>
          </dl>
        </div>

        <div className="admin-panel">
          <h2>주택 정보</h2>
          <dl className="admin-info-list">
            <div><dt>주거 형태</dt><dd>{estimate.housing_type ?? '-'}</dd></div>
            <div><dt>평수</dt><dd>{formatArea(estimate.floor_area_pyeong)}</dd></div>
            <div><dt>시공 범위</dt><dd>{estimate.renovation_scope ?? '-'}</dd></div>
            <div><dt>시공 지역</dt><dd>{estimate.project_address ?? '-'}</dd></div>
            <div><dt>희망 시기</dt><dd>{estimate.preferred_timeline ?? '-'}</dd></div>
          </dl>
        </div>

        <div className="admin-panel">
          <h2>공유와 PDF</h2>
          <div className="admin-actions-column">
            <button className="button primary-button" type="button" disabled={!canCreateShare || shareLoading} onClick={handleCreateShare}>{shareLoading ? '생성 중' : shareStatus?.active ? '새 공유 링크 발급' : '공유 링크 생성'}</button>
            {shareStatus?.active && <p className="small-note">만료일: {formatDateTime(shareStatus.expires_at)} / 조회 {shareStatus.access_count}회</p>}
            {!shareStatus && canCreateShare && <p className="small-note">생성된 공유 링크가 없습니다.</p>}
            {shareStatus?.active && <button className="button ghost-button" type="button" disabled={shareLoading} onClick={handleRevokeShare}>공유 링크 폐기</button>}
            {shareLink && <label>공유 링크<input readOnly value={shareLink} onFocus={(event) => event.target.select()} /></label>}
            {manualCopyVisible && <p className="small-note">브라우저 복사가 차단되어 입력창에서 직접 복사해야 합니다.</p>}
            {!canCreateShare && <p className="small-note">상담 중, 견적 확정, 완료 상태에서 공유 링크를 만들 수 있습니다.</p>}
            <button className="button ghost-button" type="button" disabled={pdfLoading} onClick={handlePdfDownload}>{pdfLoading ? 'PDF 준비 중' : '관리자 PDF 다운로드'}</button>
          </div>
        </div>
      </section>

      {actionMessage && <p className="admin-action-message" role="status">{actionMessage}</p>}
      {editError && <p className="field-error" role="alert">{editError}</p>}

      {editing && editState && (
        <form className="admin-panel full-width consultation-editor" onSubmit={handleEditSubmit}>
          <div className="admin-panel-heading"><h2>상담 중 견적 수정</h2><span className="small-note">저장 시 현재 카탈로그 가격으로 snapshot이 다시 생성됩니다.</span></div>
          <div className="consultation-form-grid">
            <label>주거 형태<input value={editState.housing_type} onChange={(event) => updateEditState({ housing_type: event.target.value })} /></label>
            <label>평수<input type="number" min="0.01" step="0.01" value={editState.floor_area_pyeong} onChange={(event) => updateEditState({ floor_area_pyeong: event.target.value })} /></label>
            <label>시공 범위<input value={editState.renovation_scope} onChange={(event) => updateEditState({ renovation_scope: event.target.value })} /></label>
            <label>시공 지역<input value={editState.project_address} onChange={(event) => updateEditState({ project_address: event.target.value })} /></label>
            <label>희망 시기<input value={editState.preferred_timeline} onChange={(event) => updateEditState({ preferred_timeline: event.target.value })} /></label>
          </div>
          <label>관리자 상담 메모<textarea rows={5} value={editState.admin_consultation_note} onChange={(event) => updateEditState({ admin_consultation_note: event.target.value })} placeholder="상담 중 확인한 변경 범위, 고객 선호, 내부 전달사항을 입력하세요." /></label>
          <div className="consultation-items-heading"><h3>시공 옵션</h3><button className="button ghost-button" type="button" onClick={addEditItem}>옵션 추가</button></div>
          <div className="consultation-item-list">
            {editState.items.map((item, index) => {
              const option = optionById.get(item.option_id)
              const adminItem = option ? itemById.get(option.item_id) : null
              const category = adminItem ? categoryById.get(adminItem.category_id) : null
              const selectedIds = new Set(editState.items.map((selectedItem) => selectedItem.option_id))
              return (
                <div className="consultation-item-row" key={`${item.option_id}-${index}`}>
                  <label>옵션
                    <select value={item.option_id} onChange={(event) => updateEditItem(index, { option_id: Number(event.target.value) })}>
                      {option && !editableOptions.some((editable) => editable.id === option.id) && <option value={option.id}>{currentItemLabel(estimate.items.find((estimateItem) => estimateItem.option_id === option.id) ?? estimate.items[0])}</option>}
                      {editableOptions.map((editableOption) => {
                        const editableItem = itemById.get(editableOption.item_id)
                        const editableCategory = editableItem ? categoryById.get(editableItem.category_id) : null
                        const disabled = selectedIds.has(editableOption.id) && editableOption.id !== item.option_id
                        return <option key={editableOption.id} value={editableOption.id} disabled={disabled}>{editableCategory?.name ?? '-'} / {editableItem?.name ?? '-'} / {editableOption.name} ({formatCurrency(editableOption.default_price)} / {editableOption.unit})</option>
                      })}
                    </select>
                  </label>
                  <label>수량<input type="number" min="0.01" step="0.01" value={item.quantity} onChange={(event) => updateEditItem(index, { quantity: event.target.value })} /></label>
                  <div className="consultation-row-price"><span>{category?.name ?? '-'}</span><strong>{formatCurrency(toNumber(option?.default_price) * toNumber(item.quantity))}</strong></div>
                  <button className="button ghost-button danger" type="button" onClick={() => removeEditItem(index)}>삭제</button>
                </div>
              )
            })}
          </div>
          <div className="consultation-preview-total">
            <span>저장 전 예상 공급가 {formatCurrency(editPreview.subtotal)}</span>
            <span>부가세 {formatCurrency(editPreview.vat)}</span>
            <strong>예상 총금액 {formatCurrency(editPreview.total)}</strong>
          </div>
          <div className="form-actions">
            <button className="button ghost-button" type="button" disabled={editSaving} onClick={() => { setEditing(false); setEditState(null); setEditError(null) }}>취소</button>
            <button className="button primary-button" type="submit" disabled={editSaving}>{editSaving ? '저장 중' : '저장'}</button>
          </div>
        </form>
      )}

      <section className="admin-panel full-width">
        <h2>시공 정보</h2>
        <EstimateDetailTable estimate={estimate} />
      </section>

      <section className="admin-panel full-width">
        <h2>고객 요청사항</h2>
        <p className="admin-note-text">{estimate.notes?.trim() || '등록된 요청사항이 없습니다.'}</p>
      </section>

      <section className="admin-panel full-width">
        <h2>관리자 상담 메모</h2>
        <p className="admin-note-text">{estimate.admin_consultation_note?.trim() || '등록된 상담 메모가 없습니다.'}</p>
      </section>
    </main>
  )
}
