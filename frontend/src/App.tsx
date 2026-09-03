import { Navigate, Route, Routes } from 'react-router-dom'
import { AdminLayout, ProtectedAdminRoute } from './components/AdminLayout'
import { AdminAuthProvider } from './context/AdminAuthContext'
import { EstimateDraftProvider } from './context/EstimateDraftContext'
import AdminEstimateDetailPage from './pages/AdminEstimateDetailPage'
import AdminEstimateListPage from './pages/AdminEstimateListPage'
import AdminLoginPage from './pages/AdminLoginPage'
import EstimateResultPage from './pages/EstimateResultPage'
import EstimateWizardPage from './pages/EstimateWizardPage'
import HomePage from './pages/HomePage'
import SharedEstimatePage from './pages/SharedEstimatePage'

export default function App() {
  return (
    <AdminAuthProvider>
      <EstimateDraftProvider>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/estimate" element={<EstimateWizardPage />} />
          <Route path="/estimate/contact" element={<EstimateWizardPage />} />
          <Route path="/estimate/home" element={<EstimateWizardPage />} />
          <Route path="/estimate/categories" element={<EstimateWizardPage />} />
          <Route path="/estimate/options" element={<EstimateWizardPage />} />
          <Route path="/estimate/requests" element={<EstimateWizardPage />} />
          <Route path="/estimate/review" element={<EstimateWizardPage />} />
          <Route path="/estimate/result" element={<EstimateResultPage />} />
          <Route path="/share" element={<SharedEstimatePage />} />
          <Route path="/admin/login" element={<AdminLoginPage />} />
          <Route element={<ProtectedAdminRoute />}>
            <Route path="/admin" element={<AdminLayout />}>
              <Route index element={<Navigate to="/admin/estimates" replace />} />
              <Route path="estimates" element={<AdminEstimateListPage />} />
              <Route path="estimates/:estimateId" element={<AdminEstimateDetailPage />} />
            </Route>
          </Route>
          <Route path="/admin/*" element={<Navigate to="/admin/estimates" replace />} />
        </Routes>
      </EstimateDraftProvider>
    </AdminAuthProvider>
  )
}
