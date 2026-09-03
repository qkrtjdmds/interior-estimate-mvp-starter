import { Route, Routes } from 'react-router-dom'
import { EstimateDraftProvider } from './context/EstimateDraftContext'
import EstimateResultPage from './pages/EstimateResultPage'
import EstimateWizardPage from './pages/EstimateWizardPage'
import HomePage from './pages/HomePage'
import SharedEstimatePage from './pages/SharedEstimatePage'

export default function App() {
  return (
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
      </Routes>
    </EstimateDraftProvider>
  )
}
