import { FormEvent, useEffect, useState } from 'react'
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom'
import { getAdminApiErrorMessage } from '../api/adminApi'
import { useAdminAuth } from '../context/AdminAuthContext'

export default function AdminLoginPage() {
  const { token, login } = useAdminAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const from = typeof location.state === 'object' && location.state && 'from' in location.state ? String(location.state.from) : '/admin/estimates'

  useEffect(() => {
    setError(null)
  }, [email, password])

  if (token) return <Navigate to="/admin/estimates" replace />

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!email.trim() || !password) {
      setError('아이디 또는 비밀번호를 확인해 주세요.')
      return
    }
    setLoading(true)
    setError(null)
    try {
      await login(email, password)
      navigate(from, { replace: true })
    } catch (requestError) {
      setError(getAdminApiErrorMessage(requestError))
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="admin-login-page">
      <section className="admin-login-card">
        <span className="section-kicker">ADMIN</span>
        <h1>관리자 로그인</h1>
        <p>견적 접수 내용을 확인하려면 관리자 계정으로 로그인하세요.</p>
        <form onSubmit={handleSubmit}>
          <label>아이디 또는 이메일<input autoComplete="username" value={email} onChange={(event) => setEmail(event.target.value)} /></label>
          <label>비밀번호<div className="password-row"><input autoComplete="current-password" type={showPassword ? 'text' : 'password'} value={password} onChange={(event) => setPassword(event.target.value)} /><button type="button" onClick={() => setShowPassword((value) => !value)}>{showPassword ? '숨기기' : '표시'}</button></div></label>
          {error && <p className="field-error" role="alert">{error}</p>}
          <button className="button primary-button" type="submit" disabled={loading}>{loading ? '로그인 중' : '로그인'}</button>
        </form>
        <Link className="admin-login-back" to="/">고객 화면으로 돌아가기</Link>
      </section>
    </main>
  )
}
