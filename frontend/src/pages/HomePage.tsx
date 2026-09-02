import { useEffect, useState } from 'react'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

export default function HomePage() {
  const [apiStatus, setApiStatus] = useState<'checking' | 'ok' | 'error'>('checking')

  useEffect(() => {
    fetch(`${API_BASE_URL}/api/health`)
      .then((response) => {
        if (!response.ok) throw new Error('health check failed')
        return response.json()
      })
      .then(() => setApiStatus('ok'))
      .catch(() => setApiStatus('error'))
  }, [])

  return (
    <main className="page">
      <section className="hero">
        <div className="eyebrow">INTERIOR ESTIMATE</div>
        <h1>우리 집 인테리어,<br />얼마 정도 필요할까요?</h1>
        <p className="description">
          집 정보와 원하는 공사를 선택하면 대략적인 예상 견적 범위를 확인할 수 있어요.
        </p>
        <button className="primary" type="button">무료 견적 알아보기</button>
        <div className="meta">약 3분 · 회원가입 없음 · 예상 견적은 실제 계약 금액과 다를 수 있습니다.</div>
      </section>

      <section className="steps" aria-label="견적 진행 과정">
        {['집 정보', '공사 선택', '세부 옵션', '예상 견적'].map((label, index) => (
          <div className="step" key={label}>
            <span>{index + 1}</span>
            <strong>{label}</strong>
          </div>
        ))}
      </section>

      <div className={`health health-${apiStatus}`}>
        API: {apiStatus === 'checking' ? '연결 확인 중' : apiStatus === 'ok' ? '연결됨' : '연결 실패'}
      </div>
    </main>
  )
}
