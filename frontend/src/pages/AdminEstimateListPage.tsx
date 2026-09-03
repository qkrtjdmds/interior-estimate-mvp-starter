import { useEffect, useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { fetchAdminEstimates, getAdminApiErrorMessage } from '../api/adminApi'
import type { EstimateListItem } from '../api/adminApi'
import ApiState from '../components/ApiState'
import { ADMIN_STATUS_OPTIONS, statusClass, statusLabel } from '../utils/adminStatus'
import { formatArea, formatCurrency, formatDateTime } from '../utils/format'

const PAGE_SIZE = 20

export default function AdminEstimateListPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [estimates, setEstimates] = useState<EstimateListItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const page = Math.max(1, Number(searchParams.get('page') ?? '1'))
  const status = searchParams.get('status') ?? ''
  const query = searchParams.get('q') ?? ''

  const params = useMemo(() => ({
    status: status || undefined,
    customer_name: query || undefined,
    estimate_number: undefined,
    skip: (page - 1) * PAGE_SIZE,
    limit: PAGE_SIZE,
  }), [page, query, status])

  function load() {
    setLoading(true)
    fetchAdminEstimates(params)
      .then((data) => {
        setEstimates(data)
        setError(null)
      })
      .catch((requestError) => setError(getAdminApiErrorMessage(requestError)))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    load()
  }, [params])

  function updateFilter(next: { status?: string; query?: string; page?: number }) {
    const nextParams = new URLSearchParams(searchParams)
    if (next.status !== undefined) next.status ? nextParams.set('status', next.status) : nextParams.delete('status')
    if (next.query !== undefined) next.query ? nextParams.set('q', next.query) : nextParams.delete('q')
    nextParams.set('page', String(next.page ?? 1))
    setSearchParams(nextParams)
  }

  return (
    <main className="admin-content">
      <header className="admin-page-header">
        <div><h1>접수된 견적</h1><p>최근 접수 순서로 고객 견적을 확인합니다.</p></div>
        <button className="button ghost-button" type="button" onClick={load}>새로고침</button>
      </header>

      <section className="admin-filters" aria-label="견적 필터">
        <label>검색<input value={query} onChange={(event) => updateFilter({ query: event.target.value, page: 1 })} placeholder="고객명 검색" /></label>
        <label>상태<select value={status} onChange={(event) => updateFilter({ status: event.target.value, page: 1 })}><option value="">전체</option>{ADMIN_STATUS_OPTIONS.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}</select></label>
      </section>

      {loading && <ApiState title="견적 목록을 불러오는 중" message="접수된 견적을 확인하고 있습니다." />}
      {error && <ApiState title="견적 목록 조회 실패" message={error} action={<button className="button ghost-button" type="button" onClick={load}>다시 시도</button>} />}
      {!loading && !error && estimates.length === 0 && <ApiState title="접수된 견적이 없습니다" message="조건에 맞는 견적이 없습니다." />}

      {!loading && !error && estimates.length > 0 && (
        <div className="admin-estimate-list">
          {estimates.map((estimate) => (
            <Link className="admin-estimate-card" to={`/admin/estimates/${estimate.id}`} key={estimate.id}>
              <div><span>견적번호</span><strong>{estimate.estimate_number}</strong></div>
              <div><span>접수일</span><strong>{formatDateTime(estimate.created_at)}</strong></div>
              <div><span>고객</span><strong>{estimate.customer_name}</strong><p>{estimate.customer_phone ?? '-'}</p></div>
              <div><span>주거</span><strong>{estimate.housing_type ?? '-'}</strong><p>{formatArea(estimate.floor_area_pyeong)} / {estimate.renovation_scope ?? '-'}</p></div>
              <div><span>금액</span><strong>{formatCurrency(estimate.total_amount)}</strong></div>
              <div><span className={statusClass(estimate.status)}>{statusLabel(estimate.status)}</span></div>
            </Link>
          ))}
        </div>
      )}

      <div className="admin-pagination">
        <button className="button ghost-button" type="button" disabled={page <= 1} onClick={() => updateFilter({ page: page - 1 })}>이전</button>
        <span>{page}페이지</span>
        <button className="button ghost-button" type="button" disabled={estimates.length < PAGE_SIZE} onClick={() => updateFilter({ page: page + 1 })}>다음</button>
      </div>
    </main>
  )
}
