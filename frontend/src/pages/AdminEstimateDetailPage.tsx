import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import {
  createEstimateShare,
  downloadAdminEstimatePdf,
  fetchAdminEstimate,
  fetchEstimateShareStatus,
  getAdminApiErrorMessage,
  revokeEstimateShare,
  updateEstimateStatus,
} from '../api/adminApi'
import type { EstimateShareStatus } from '../api/adminApi'
import type { EstimateDetail } from '../api/types'
import ApiState from '../components/ApiState'
import { EstimateDetailTable, EstimateMeta, EstimateTotals } from '../components/EstimateSummary'
import { ADMIN_STATUS_OPTIONS, statusClass, statusLabel } from '../utils/adminStatus'
import { formatArea, formatDateTime } from '../utils/format'

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

  const canCreateShare = estimate ? ['submitted', 'confirmed', 'completed'].includes(estimate.status) : false
  const safeEstimateId = Number.isFinite(estimateId) ? estimateId : 0

  function load() {
    if (!safeEstimateId) {
      setError('잘못된 견적 주소입니다.')
      setLoading(false)
      return
    }
    setLoading(true)
    Promise.allSettled([fetchAdminEstimate(safeEstimateId), fetchEstimateShareStatus(safeEstimateId)])
      .then(([estimateResult, shareResult]) => {
        if (estimateResult.status === 'fulfilled') {
          setEstimate(estimateResult.value)
          setError(null)
        } else {
          setError(getAdminApiErrorMessage(estimateResult.reason))
        }
        if (shareResult.status === 'fulfilled') setShareStatus(shareResult.value)
        else setShareStatus(null)
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

  async function handleStatusChange(nextStatus: string) {
    if (!estimate || nextStatus === estimate.status) return
    if (nextStatus === 'cancelled' && !window.confirm('견적을 취소 상태로 변경할까요? 활성 공유 링크가 차단될 수 있습니다.')) return
    setStatusSaving(true)
    setActionMessage(null)
    try {
      const updated = await updateEstimateStatus(estimate.id, nextStatus)
      setEstimate(updated)
      setActionMessage('상태가 변경되었습니다.')
      if (nextStatus === 'cancelled') setShareStatus(null)
    } catch (requestError) {
      setActionMessage(getAdminApiErrorMessage(requestError))
    } finally {
      setStatusSaving(false)
    }
  }

  async function handleCreateShare() {
    if (!estimate) return
    setShareLoading(true)
    setActionMessage(null)
    setManualCopyVisible(false)
    try {
      const created = await createEstimateShare(estimate.id, 30)
      const link = `${window.location.origin}/share#token=${created.share_token}`
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
          <label>처리 상태<select value={estimate.status} disabled={statusSaving} onChange={(event) => void handleStatusChange(event.target.value)}>{ADMIN_STATUS_OPTIONS.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}</select></label>
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
            {shareStatus && <p className="small-note">만료일: {formatDateTime(shareStatus.expires_at)} / 조회 {shareStatus.access_count}회</p>}
            {shareStatus && <button className="button ghost-button" type="button" disabled={shareLoading} onClick={handleRevokeShare}>공유 링크 폐기</button>}
            {shareLink && <label>공유 링크<input readOnly value={shareLink} onFocus={(event) => event.target.select()} /></label>}
            {manualCopyVisible && <p className="small-note">브라우저 복사가 차단되어 입력창에서 직접 복사해야 합니다.</p>}
            {!canCreateShare && <p className="small-note">상담 중, 견적 확정, 완료 상태에서 공유 링크를 만들 수 있습니다.</p>}
            <button className="button ghost-button" type="button" disabled={pdfLoading} onClick={handlePdfDownload}>{pdfLoading ? 'PDF 준비 중' : '관리자 PDF 다운로드'}</button>
          </div>
        </div>
      </section>

      {actionMessage && <p className="admin-action-message" role="status">{actionMessage}</p>}

      <section className="admin-panel full-width">
        <h2>시공 정보</h2>
        <EstimateDetailTable estimate={estimate} />
      </section>

      <section className="admin-panel full-width">
        <h2>고객 요청사항</h2>
        <p className="admin-note-text">{estimate.notes?.trim() || '등록된 요청사항이 없습니다.'}</p>
      </section>
    </main>
  )
}
