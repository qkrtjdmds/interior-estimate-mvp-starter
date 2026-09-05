import { Link } from 'react-router-dom'
import { useEstimateDraft } from '../context/EstimateDraftContext'

export default function HomePage() {
  const { resetDraft } = useEstimateDraft()

  return (
    <main className="landing-page">
      <section className="hero-section consult-hero">
        <div className="hero-copy">
          <span className="section-kicker">INTERIOR ESTIMATE</span>
          <h1>우리 집 인테리어, 얼마쯤 들까?</h1>
          <p>몇 가지 질문에 답하면 간편하게 예상 견적을 확인할 수 있어요.</p>
          <div className="hero-actions">
            <Link className="button primary-button" to="/estimate/contact" onClick={resetDraft}>
              견적 확인하기
            </Link>
          </div>
          <p className="disclaimer">표시 금액은 실제 계약금액이 아닌 MVP 테스트용 예상 견적입니다. 현장 조건과 자재에 따라 달라질 수 있습니다.</p>
        </div>
      </section>

      <section className="process-section" aria-labelledby="process-title">
        <div className="section-title-row">
          <span className="section-kicker">PROCESS</span>
          <h2 id="process-title">이렇게 진행됩니다</h2>
        </div>
        <div className="process-grid">
          {[
            ['1', '집 정보 입력', '주거 형태, 평수, 시공 지역을 알려주세요.'],
            ['2', '원하는 시공 선택', '필요한 인테리어 항목을 고릅니다.'],
            ['3', '예상 견적 확인', '백엔드 기준 단가로 계산된 금액을 확인합니다.'],
            ['4', '상담 접수', '연락처를 남기면 견적번호가 발급됩니다.'],
          ].map(([number, title, description]) => (
            <article className="process-card" key={number}>
              <span>{number}</span>
              <h3>{title}</h3>
              <p>{description}</p>
            </article>
          ))}
        </div>
      </section>
    </main>
  )
}
