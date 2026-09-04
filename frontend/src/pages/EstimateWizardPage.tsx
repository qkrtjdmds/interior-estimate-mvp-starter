import { FormEvent, useEffect, useMemo, useState } from 'react'
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom'
import { createEstimate, fetchCatalog, previewEstimate } from '../api/estimateApi'
import type { CatalogCategory, CatalogItem, EstimatePreview } from '../api/types'
import { getApiErrorMessage } from '../api/client'
import ApiState from '../components/ApiState'
import { EstimateDetailTable, EstimateTotals } from '../components/EstimateSummary'
import { useEstimateDraft } from '../context/EstimateDraftContext'
import { useDebouncedValue } from '../hooks/useDebouncedValue'
import { formatArea, formatCurrency } from '../utils/format'

const STEPS = [
  { key: 'contact', path: '/estimate/contact', title: '연락받을 정보를 알려주세요', description: '견적 상담에 필요한 기본 정보만 입력합니다.' },
  { key: 'home', path: '/estimate/home', title: '집 정보를 알려주세요', description: '주거 형태, 평수, 시공 지역과 희망 시기를 선택합니다.' },
  { key: 'categories', path: '/estimate/categories', title: '어떤 인테리어를 원하시나요?', description: '원하는 시공 항목을 모두 선택해 주세요.' },
  { key: 'options', path: '/estimate/options', title: '세부 옵션과 수량을 정해주세요', description: '선택한 항목별로 실제 기준정보 옵션을 선택합니다.' },
  { key: 'requests', path: '/estimate/requests', title: '추가 요청사항이 있나요?', description: '원하는 분위기나 현장 관련 내용을 자유롭게 적어주세요.' },
  { key: 'review', path: '/estimate/review', title: '입력한 내용을 확인해 주세요', description: '저장 전 전체 견적 내용을 마지막으로 확인합니다.' },
]

const HOUSING_TYPES = ['아파트', '빌라', '단독주택', '오피스텔', '기타']
const AREA_OPTIONS = ['10평대', '20평대', '30평대', '40평대', '50평 이상', '직접 입력']
const SCOPE_OPTIONS = ['전체 인테리어', '부분 인테리어']
const TIMELINE_OPTIONS = ['최대한 빠르게', '1개월 이내', '1~3개월 이내', '3개월 이후', '아직 정하지 않음']

function currentStepIndex(pathname: string): number {
  const index = STEPS.findIndex((step) => step.path === pathname)
  return index === -1 ? 0 : index
}

function phoneLooksValid(value: string): boolean {
  return /^[0-9\-\s]{8,20}$/.test(value.trim())
}

function emailLooksValid(value: string): boolean {
  return !value.trim() || /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(value.trim())
}

function areaValueFromMode(mode: string, customValue: string): string {
  if (mode === '직접 입력') return customValue
  const match = mode.match(/\d+/)
  return match ? match[0] : ''
}

function flattenItems(catalog: CatalogCategory[]): Array<{ category: CatalogCategory; item: CatalogItem }> {
  return catalog.flatMap((category) => category.items.map((item) => ({ category, item })))
}

function buildPreviewLikeEstimate(preview: EstimatePreview) {
  return {
    estimate_number: 'preview',
    status: 'draft',
    customer_name_masked: '고객',
    created_at: new Date().toISOString(),
    valid_until: null,
    items: preview.items.map((item) => ({
      category_name: item.category_name,
      item_name: item.item_name,
      option_name: item.option_name,
      description: null,
      unit: item.unit,
      unit_price: item.unit_price,
      quantity: item.quantity,
      line_total: item.line_total,
      sort_order: item.sort_order,
    })),
    subtotal: preview.subtotal,
    vat_rate: preview.vat_rate,
    vat_amount: preview.vat_amount,
    total_amount: preview.total_amount,
  }
}

export default function EstimateWizardPage() {
  const location = useLocation()
  const navigate = useNavigate()
  const stepIndex = currentStepIndex(location.pathname)
  const step = STEPS[stepIndex]
  const isFirst = stepIndex === 0
  const isLast = stepIndex === STEPS.length - 1
  const {
    customer,
    project,
    selectedItemIds,
    setSelectedItemIds,
    selectedItems,
    setCustomer,
    setProject,
    toggleSelectedItemId,
    addOrUpdateItem,
    updateQuantity,
    removeItem,
    setLastEstimate,
  } = useEstimateDraft()
  const [catalog, setCatalog] = useState<CatalogCategory[]>([])
  const [catalogLoading, setCatalogLoading] = useState(false)
  const [catalogError, setCatalogError] = useState<string | null>(null)
  const [catalogLoaded, setCatalogLoaded] = useState(false)
  const [catalogSyncNotice, setCatalogSyncNotice] = useState<string | null>(null)
  const [preview, setPreview] = useState<EstimatePreview | null>(null)
  const [previewLoading, setPreviewLoading] = useState(false)
  const [previewError, setPreviewError] = useState<string | null>(null)
  const [formError, setFormError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const debouncedItems = useDebouncedValue(selectedItems, 400)

  useEffect(() => {
    if (!['categories', 'options', 'review'].includes(step.key)) return
    let alive = true
    setCatalogLoading(true)
    setCatalogLoaded(false)
    fetchCatalog()
      .then((data) => {
        if (!alive) return
        setCatalog(data)
        setCatalogLoaded(true)
        setCatalogError(null)
      })
      .catch((error) => {
        if (!alive) return
        setCatalogError(getApiErrorMessage(error))
      })
      .finally(() => {
        if (alive) setCatalogLoading(false)
      })
    return () => {
      alive = false
    }
  }, [step.key])

  useEffect(() => {
    if (!catalogLoaded) return
    const availableItemIds = new Set(catalog.flatMap((category) => category.items.map((item) => item.id)))
    const availableOptionIds = new Set(catalog.flatMap((category) => category.items.flatMap((item) => item.options.map((option) => option.id))))
    const validItemIds = selectedItemIds.filter((itemId) => availableItemIds.has(itemId))
    const removedItemCount = selectedItemIds.length - validItemIds.length
    const invalidOptionIds = selectedItems.filter((item) => !availableOptionIds.has(item.option_id)).map((item) => item.option_id)

    if (removedItemCount > 0) setSelectedItemIds(validItemIds)
    invalidOptionIds.forEach((optionId) => removeItem(optionId))
    if (removedItemCount > 0 || invalidOptionIds.length > 0) {
      setCatalogSyncNotice('현재 카탈로그에서 사용할 수 없는 저장 항목을 제거했습니다. 옵션을 다시 확인해 주세요.')
    }
  }, [catalog, catalogLoaded, removeItem, selectedItemIds, selectedItems, setSelectedItemIds])

  useEffect(() => {
    if (debouncedItems.length === 0) {
      setPreview(null)
      setPreviewError(null)
      return
    }
    let alive = true
    setPreviewLoading(true)
    previewEstimate(debouncedItems.map((item, index) => ({ ...item, sort_order: index + 1 })))
      .then((data) => {
        if (!alive) return
        setPreview(data)
        setPreviewError(null)
      })
      .catch((error) => {
        if (!alive) return
        setPreviewError(getApiErrorMessage(error))
      })
      .finally(() => {
        if (alive) setPreviewLoading(false)
      })
    return () => {
      alive = false
    }
  }, [debouncedItems])

  if (location.pathname === '/estimate') return <Navigate to="/estimate/contact" replace />

  const catalogItems = flattenItems(catalog)
  const selectedCatalogItems = catalogItems.filter(({ item }) => selectedItemIds.includes(item.id))

  function goNext() {
    setFormError(null)
    const error = validateCurrentStep()
    if (error) {
      setFormError(error)
      return
    }
    if (!isLast) navigate(STEPS[stepIndex + 1].path)
  }

  function goPrevious() {
    setFormError(null)
    if (isFirst) navigate('/')
    else navigate(STEPS[stepIndex - 1].path)
  }

  function validateCurrentStep(): string | null {
    if (step.key === 'contact') {
      if (!customer.name.trim()) return '이름을 입력해 주세요.'
      if (!customer.phone.trim()) return '연락처를 입력해 주세요.'
      if (!phoneLooksValid(customer.phone)) return '연락처는 숫자와 하이픈 중심으로 입력해 주세요.'
      if (!emailLooksValid(customer.email)) return '이메일 형식을 확인해 주세요.'
      if (!customer.privacyAccepted) return '개인정보 수집 및 이용에 동의해 주세요.'
    }
    if (step.key === 'home') {
      if (!project.housingType) return '주거 형태를 선택해 주세요.'
      if (!project.floorAreaMode) return '집 평수를 선택해 주세요.'
      if (project.floorAreaMode === '직접 입력' && (!project.floorAreaPyeong || Number(project.floorAreaPyeong) <= 0)) return '정확한 평수를 숫자로 입력해 주세요.'
      if (!project.renovationScope) return '시공 범위를 선택해 주세요.'
      if (!project.projectAddress.trim()) return '시공 지역을 입력해 주세요.'
      if (!project.preferredTimeline) return '시공 희망 시기를 선택해 주세요.'
    }
    if (step.key === 'categories' && selectedItemIds.length === 0) return '원하는 시공 항목을 하나 이상 선택해 주세요.'
    if (step.key === 'options') {
      if (selectedItems.length === 0) return '선택한 시공 항목의 옵션을 하나 이상 선택해 주세요.'
      const invalidQuantity = selectedItems.some((item) => !item.quantity || Number(item.quantity) <= 0)
      if (invalidQuantity) return '옵션 수량은 0보다 큰 숫자로 입력해 주세요.'
      if (previewError) return previewError
    }
    if (step.key === 'review') {
      if (!preview) return '예상 견적 계산이 완료된 뒤 저장할 수 있습니다.'
      if (previewError) return previewError
    }
    return null
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    const error = validateCurrentStep()
    if (error) {
      setFormError(error)
      return
    }
    setSubmitting(true)
    setFormError(null)
    try {
      const estimate = await createEstimate({
        customer_name: customer.name.trim(),
        customer_phone: customer.phone.trim(),
        customer_email: customer.email.trim() || null,
        housing_type: project.housingType || null,
        floor_area_pyeong: areaValueFromMode(project.floorAreaMode, project.floorAreaPyeong) || null,
        renovation_scope: project.renovationScope || null,
        preferred_timeline: project.preferredTimeline || null,
        project_address: project.projectAddress.trim() || null,
        notes: project.requestNotes.trim() || null,
        items: selectedItems.map((item, index) => ({ ...item, sort_order: index + 1 })),
      })
      setLastEstimate(estimate)
      navigate('/estimate/result')
    } catch (requestError) {
      setFormError(getApiErrorMessage(requestError))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <main className="wizard-page">
      <header className="wizard-header">
        <Link className="brand-link" to="/">INTERIOR ESTIMATE</Link>
        <div className="step-count">{stepIndex + 1} / {STEPS.length}단계</div>
      </header>

      <div className="progress-track" aria-hidden="true">
        <span style={{ width: `${((stepIndex + 1) / STEPS.length) * 100}%` }} />
      </div>

      <form className="wizard-card" onSubmit={handleSubmit}>
        <div className="wizard-title">
          <span className="section-kicker">상담형 견적</span>
          <h1>{step.title}</h1>
          <p>{step.description}</p>
        </div>

        {step.key === 'contact' && (
          <section className="step-section">
            <label>이름<input value={customer.name} maxLength={100} onChange={(event) => setCustomer({ name: event.target.value })} placeholder="홍길동" /></label>
            <label>연락처<input value={customer.phone} maxLength={50} inputMode="tel" onChange={(event) => setCustomer({ phone: event.target.value })} placeholder="010-0000-0000" /></label>
            <label>이메일 <span>선택</span><input type="email" value={customer.email} onChange={(event) => setCustomer({ email: event.target.value })} placeholder="name@example.com" /></label>
            <label className="checkbox-label"><input type="checkbox" checked={customer.privacyAccepted} onChange={(event) => setCustomer({ privacyAccepted: event.target.checked })} /><span>견적 상담을 위한 개인정보 수집 및 이용에 동의합니다.</span></label>
            <p className="small-note">이름, 연락처, 이메일은 새로고침 복구용 localStorage에 저장하지 않습니다.</p>
          </section>
        )}

        {step.key === 'home' && (
          <section className="step-section">
            <ChoiceGroup title="주거 형태" options={HOUSING_TYPES} value={project.housingType} onSelect={(value) => setProject({ housingType: value })} />
            <ChoiceGroup title="집 평수" options={AREA_OPTIONS} value={project.floorAreaMode} onSelect={(value) => setProject({ floorAreaMode: value })} />
            {project.floorAreaMode === '직접 입력' && <label>직접 입력 평수<input type="number" min="1" step="0.1" value={project.floorAreaPyeong} onChange={(event) => setProject({ floorAreaPyeong: event.target.value })} placeholder="예: 32.5" /></label>}
            <ChoiceGroup title="시공 범위" options={SCOPE_OPTIONS} value={project.renovationScope} onSelect={(value) => setProject({ renovationScope: value })} />
            <label>시공 지역<input maxLength={255} value={project.projectAddress} onChange={(event) => setProject({ projectAddress: event.target.value })} placeholder="예: 서울 마포구, 경기 성남시" /></label>
            <ChoiceGroup title="시공 희망 시기" options={TIMELINE_OPTIONS} value={project.preferredTimeline} onSelect={(value) => setProject({ preferredTimeline: value })} />
          </section>
        )}

        {step.key === 'categories' && (
          <section className="step-section">
            {catalogLoading && <ApiState title="카탈로그를 불러오는 중" message="등록된 기준정보를 확인하고 있습니다." />}
            {catalogError && <ApiState title="카탈로그 조회 실패" message={catalogError} />}
            {catalogSyncNotice && <p className="notice" role="status">{catalogSyncNotice}</p>}
            {!catalogLoading && !catalogError && catalog.length === 0 && <ApiState title="등록된 기준정보가 없습니다" message="관리자가 기준정보를 등록해야 견적을 시작할 수 있습니다." />}
            <div className="consult-category-grid">
              {catalogItems.map(({ category, item }) => {
                const selected = selectedItemIds.includes(item.id)
                return (
                  <button className={selected ? 'consult-card selected' : 'consult-card'} type="button" key={item.id} onClick={() => toggleSelectedItemId(item.id)} aria-pressed={selected}>
                    <span>{category.name}</span>
                    <strong>{item.name}</strong>
                    {item.description && <p>{item.description}</p>}
                    <em>{item.options.length}개 옵션</em>
                  </button>
                )
              })}
            </div>
          </section>
        )}

        {step.key === 'options' && (
          <section className="step-section">
            {catalogSyncNotice && <p className="notice" role="status">{catalogSyncNotice}</p>}
            {selectedCatalogItems.length === 0 ? <ApiState title="선택한 시공 항목이 없습니다" message="이전 단계에서 시공 항목을 먼저 선택해 주세요." /> : null}
            {selectedCatalogItems.map(({ category, item }, index) => (
              <article className="option-question" key={item.id}>
                <div className="question-label">{index + 1}. {category.name} / {item.name}</div>
                <div className="option-grid">
                  {item.options.map((option) => {
                    const selected = selectedItems.some((selectedItem) => selectedItem.option_id === option.id)
                    const selectedInput = selectedItems.find((selectedItem) => selectedItem.option_id === option.id)
                    return (
                      <div className={selected ? 'option-card selected' : 'option-card'} key={option.id}>
                        <button type="button" onClick={() => addOrUpdateItem({ option_id: option.id, quantity: selectedInput?.quantity ?? '1.00' })} aria-pressed={selected}>
                          <span className="option-topline"><strong>{option.name}</strong>{option.recommended && <span className="badge">추천</span>}</span>
                          {option.description && <span className="option-description">{option.description}</span>}
                          <span className="option-price">{formatCurrency(option.default_price)} / {option.unit}</span>
                        </button>
                        {selected && (
                          <div className="quantity-line">
                            <label>수량 또는 면적<input type="number" min="0.01" step="0.01" value={selectedInput?.quantity ?? '1.00'} onChange={(event) => updateQuantity(option.id, event.target.value)} /></label>
                            <span>{option.unit}</span>
                            <button className="text-button danger" type="button" onClick={() => removeItem(option.id)}>삭제</button>
                          </div>
                        )}
                      </div>
                    )
                  })}
                </div>
              </article>
            ))}
            {previewLoading && <p className="notice">예상 금액을 계산하고 있습니다.</p>}
            {previewError && <p className="error-text">{previewError}</p>}
            {preview && <div className="inline-total">현재 예상 금액 <strong>{formatCurrency(preview.total_amount)}</strong></div>}
          </section>
        )}

        {step.key === 'requests' && (
          <section className="step-section">
            <label>추가 요청사항 <span>선택</span><textarea rows={8} value={project.requestNotes} onChange={(event) => setProject({ requestNotes: event.target.value })} placeholder="예: 안방은 우드톤을 원하고 주방 수납공간은 넉넉하게 만들고 싶어요." /></label>
          </section>
        )}

        {step.key === 'review' && (
          <section className="step-section review-grid">
            <ReviewBlock title="개인정보" editPath="/estimate/contact" items={[['이름', customer.name], ['연락처', customer.phone], ['이메일', customer.email || '-']]} />
            <ReviewBlock title="집 정보" editPath="/estimate/home" items={[["주거 형태", project.housingType], ["평수", formatArea(areaValueFromMode(project.floorAreaMode, project.floorAreaPyeong))], ["시공 범위", project.renovationScope], ["시공 지역", project.projectAddress], ["희망 시기", project.preferredTimeline]]} />
            <ReviewBlock title="추가 요청사항" editPath="/estimate/requests" items={[["요청사항", project.requestNotes || '-']]} />
            {preview ? (
              <div className="review-estimate">
                <div className="review-heading"><h2>예상 견적</h2><Link to="/estimate/options">수정하기</Link></div>
                <EstimateDetailTable estimate={buildPreviewLikeEstimate(preview)} />
                <EstimateTotals estimate={buildPreviewLikeEstimate(preview)} />
              </div>
            ) : <ApiState title="예상 견적 계산 대기" message="선택 옵션을 확인하고 있습니다." />}
          </section>
        )}

        {formError && <p className="field-error" role="alert">{formError}</p>}

        <div className="wizard-actions">
          <button className="button ghost-button" type="button" onClick={goPrevious}>{isFirst ? '메인으로' : '이전'}</button>
          {isLast ? (
            <button className="button primary-button" type="submit" disabled={submitting || previewLoading}>{submitting ? '저장 중' : '예상 견적 저장하기'}</button>
          ) : (
            <button className="button primary-button" type="button" onClick={goNext}>다음</button>
          )}
        </div>
      </form>
    </main>
  )
}

function ChoiceGroup({ title, options, value, onSelect }: { title: string; options: string[]; value: string; onSelect: (value: string) => void }) {
  return (
    <fieldset className="choice-group">
      <legend>{title}</legend>
      <div className="choice-grid">
        {options.map((option) => (
          <button className={value === option ? 'choice-card selected' : 'choice-card'} type="button" key={option} onClick={() => onSelect(option)} aria-pressed={value === option}>
            {option}
          </button>
        ))}
      </div>
    </fieldset>
  )
}

function ReviewBlock({ title, editPath, items }: { title: string; editPath: string; items: Array<[string, string]> }) {
  return (
    <section className="review-block">
      <div className="review-heading"><h2>{title}</h2><Link to={editPath}>수정하기</Link></div>
      <dl>
        {items.map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{value || '-'}</dd></div>)}
      </dl>
    </section>
  )
}