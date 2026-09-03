import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { downloadSharedEstimatePdf, fetchSharedEstimate } from '../api/estimateApi'
import type { PublicEstimate } from '../api/types'
import { getApiErrorMessage } from '../api/client'
import ApiState from '../components/ApiState'
import { EstimateDetailTable, EstimateMeta, EstimateTotals } from '../components/EstimateSummary'

function extractTokenFromHash(): string {
  const hash = window.location.hash.replace(/^#/, '')
  if (!hash) return ''
  const params = new URLSearchParams(hash)
  return params.get('token') ?? hash
}

export default function SharedEstimatePage() {
  const [shareToken, setShareToken] = useState('')
  const [estimate, setEstimate] = useState<PublicEstimate | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [pdfLoading, setPdfLoading] = useState(false)
  const [pdfError, setPdfError] = useState<string | null>(null)

  useEffect(() => {
    const token = extractTokenFromHash()
    setShareToken(token)
    if (token) {
      window.history.replaceState(null, document.title, window.location.pathname)
    }
  }, [])

  useEffect(() => {
    if (!shareToken) {
      setLoading(false)
      setError('공유 토큰이 없습니다. 링크를 다시 확인해 주세요.')
      return
    }
    let alive = true
    fetchSharedEstimate(shareToken)
      .then((data) => {
        if (!alive) return
        setEstimate(data)
        setError(null)
      })
      .catch((requestError) => {
        if (!alive) return
        setError(getApiErrorMessage(requestError))
      })
      .finally(() => {
        if (alive) setLoading(false)
      })
    return () => {
      alive = false
    }
  }, [shareToken])

  const filename = useMemo(() => {
    const number = estimate?.estimate_number.replace(/[^a-zA-Z0-9_-]/g, '_') ?? 'estimate'
    return `estimate_${number}.pdf`
  }, [estimate?.estimate_number])

  async function handleDownloadPdf() {
    if (!shareToken) return
    setPdfLoading(true)
    setPdfError(null)
    try {
      const blob = await downloadSharedEstimatePdf(shareToken)
      const url = window.URL.createObjectURL(blob)
      const anchor = document.createElement('a')
      anchor.href = url
      anchor.download = filename
      document.body.appendChild(anchor)
      anchor.click()
      anchor.remove()
      window.URL.revokeObjectURL(url)
    } catch (requestError) {
      setPdfError(getApiErrorMessage(requestError))
    } finally {
      setPdfLoading(false)
    }
  }

  if (loading) {
    return <main className="app-page narrow-page"><ApiState title="공유 견적을 불러오는 중" message="저장된 견적 정보를 확인하고 있습니다." /></main>
  }

  if (error || !estimate) {
    return (
      <main className="app-page narrow-page">
        <ApiState
          title="공유 견적을 열 수 없습니다"
          message={error ?? '공유 링크가 올바르지 않습니다.'}
          action={<Link className="button primary-button" to="/">처음으로</Link>}
        />
      </main>
    )
  }

  return (
    <main className="app-page narrow-page">
      <header className="page-header">
        <div>
          <span className="section-kicker">SHARED ESTIMATE</span>
          <h1>공유 견적 조회</h1>
          <p>공개 공유 범위의 견적 정보만 표시합니다.</p>
        </div>
        <Link className="button ghost-button" to="/">처음으로</Link>
      </header>

      <section className="result-section">
        <EstimateMeta estimate={estimate} />
        <EstimateDetailTable estimate={estimate} />
        <EstimateTotals estimate={estimate} />
      </section>

      <div className="form-actions">
        <button className="button primary-button" type="button" onClick={handleDownloadPdf} disabled={pdfLoading}>
          {pdfLoading ? 'PDF 준비 중' : 'PDF 다운로드'}
        </button>
      </div>
      {pdfError && <p className="error-text">{pdfError}</p>}
    </main>
  )
}
