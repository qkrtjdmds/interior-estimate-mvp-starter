import { Link } from 'react-router-dom'
import { EstimateDetailTable, EstimateMeta, EstimateTotals } from '../components/EstimateSummary'
import ApiState from '../components/ApiState'
import { useEstimateDraft } from '../context/EstimateDraftContext'
import { formatArea } from '../utils/format'

export default function EstimateResultPage() {
  const { lastEstimate, project, resetDraft } = useEstimateDraft()

  if (!lastEstimate) {
    return (
      <main className="app-page narrow-page">
        <ApiState
          title="저장된 견적 결과가 없습니다"
          message="브라우저 저장 상태에 견적 결과가 남아 있지 않습니다. 새 견적을 작성해 주세요."
          action={<Link className="button primary-button" to="/estimate/contact">견적 작성하기</Link>}
        />
      </main>
    )
  }

  return (
    <main className="app-page narrow-page">
      <header className="page-header">
        <div>
          <span className="section-kicker">RESULT</span>
          <h1>견적이 정상적으로 접수되었습니다</h1>
          <p>상담 시 아래 견적번호를 알려주시면 더 빠르게 확인할 수 있습니다.</p>
        </div>
      </header>

      <section className="result-section">
        <EstimateMeta estimate={lastEstimate} />
        <div className="result-meta project-meta">
          <div><span>주거 형태</span><strong>{lastEstimate.housing_type ?? project.housingType ?? '-'}</strong></div>
          <div><span>평수</span><strong>{formatArea(lastEstimate.floor_area_pyeong ?? project.floorAreaPyeong)}</strong></div>
          <div><span>시공 범위</span><strong>{lastEstimate.renovation_scope ?? project.renovationScope ?? '-'}</strong></div>
          <div><span>시공 지역</span><strong>{lastEstimate.project_address ?? project.projectAddress ?? '-'}</strong></div>
          <div><span>희망 시기</span><strong>{lastEstimate.preferred_timeline ?? project.preferredTimeline ?? '-'}</strong></div>
        </div>
        <EstimateDetailTable estimate={lastEstimate} />
        <EstimateTotals estimate={lastEstimate} />
      </section>

      <section className="share-info">
        <h2>안내</h2>
        <p>이 금액은 예상 견적이며 실제 상담, 현장 확인, 자재 선택에 따라 변경될 수 있습니다. 공유 링크와 PDF는 현재 백엔드 권한 구조상 관리자 발급 또는 공유 토큰이 있는 경우에만 사용할 수 있습니다.</p>
      </section>

      <div className="form-actions">
        <Link className="button ghost-button" to="/estimate/review">입력 내용 다시 보기</Link>
        <Link className="button primary-button" to="/" onClick={resetDraft}>처음부터 다시 작성</Link>
      </div>
    </main>
  )
}
