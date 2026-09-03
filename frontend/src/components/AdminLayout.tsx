import { Link, NavLink, Navigate, Outlet, useLocation } from 'react-router-dom'
import { useState } from 'react'
import { useAdminAuth } from '../context/AdminAuthContext'

export function ProtectedAdminRoute() {
  const { token, loading } = useAdminAuth()
  const location = useLocation()

  if (loading) {
    return <main className="admin-shell"><div className="admin-loading">관리자 인증을 확인하고 있습니다.</div></main>
  }

  if (!token) {
    return <Navigate to="/admin/login" replace state={{ from: location.pathname }} />
  }

  return <Outlet />
}

export function AdminLayout() {
  const { admin, logout } = useAdminAuth()
  const [open, setOpen] = useState(false)

  return (
    <div className="admin-layout">
      <aside className={open ? 'admin-sidebar open' : 'admin-sidebar'}>
        <div className="admin-brand">Interior Admin</div>
        <nav aria-label="관리자 메뉴">
          <NavLink to="/admin/estimates" onClick={() => setOpen(false)}>견적 관리</NavLink>
          <NavLink to="/admin/catalog" onClick={() => setOpen(false)}>카탈로그 관리</NavLink>
        </nav>
        <div className="admin-user">
          <span>관리자</span>
          <strong>{admin?.email ?? '-'}</strong>
        </div>
        <Link className="admin-customer-link" to="/">고객 사이트로 이동</Link>
        <button className="admin-logout" type="button" onClick={logout}>로그아웃</button>
      </aside>
      <div className="admin-main">
        <header className="admin-topbar">
          <button className="admin-menu-button" type="button" onClick={() => setOpen((value) => !value)} aria-expanded={open}>메뉴</button>
          <span>관리자</span>
        </header>
        <Outlet />
      </div>
    </div>
  )
}