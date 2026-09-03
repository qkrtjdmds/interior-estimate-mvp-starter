import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import type { EstimateDetail, EstimateLineInput } from '../api/types'

interface CustomerInfo {
  name: string
  phone: string
  email: string
  privacyAccepted: boolean
}

interface ProjectInfo {
  housingType: string
  floorAreaMode: string
  floorAreaPyeong: string
  renovationScope: string
  projectAddress: string
  preferredTimeline: string
  requestNotes: string
}

interface PersistedDraftState {
  selectedItemIds: number[]
  selectedItems: EstimateLineInput[]
  project: ProjectInfo
  lastEstimate: EstimateDetail | null
}

interface EstimateDraftState extends PersistedDraftState {
  customer: CustomerInfo
}

interface EstimateDraftContextValue extends EstimateDraftState {
  setSelectedItemIds: (itemIds: number[]) => void
  toggleSelectedItemId: (itemId: number) => void
  addOrUpdateItem: (item: EstimateLineInput) => void
  updateQuantity: (optionId: number, quantity: string) => void
  removeItem: (optionId: number) => void
  removeOptionsForItems: (itemIds: number[]) => void
  setCustomer: (customer: Partial<CustomerInfo>) => void
  setProject: (project: Partial<ProjectInfo>) => void
  setLastEstimate: (estimate: EstimateDetail | null) => void
  resetDraft: () => void
}

const STORAGE_KEY = 'interior-estimate-draft-v2'

const initialCustomer: CustomerInfo = {
  name: '',
  phone: '',
  email: '',
  privacyAccepted: false,
}

const initialProject: ProjectInfo = {
  housingType: '',
  floorAreaMode: '',
  floorAreaPyeong: '',
  renovationScope: '',
  projectAddress: '',
  preferredTimeline: '',
  requestNotes: '',
}

const initialPersistedState: PersistedDraftState = {
  selectedItemIds: [],
  selectedItems: [],
  project: initialProject,
  lastEstimate: null,
}

const EstimateDraftContext = createContext<EstimateDraftContextValue | null>(null)

function loadPersistedState(): PersistedDraftState {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY)
    if (!raw) return initialPersistedState
    const parsed = JSON.parse(raw) as Partial<PersistedDraftState>
    return {
      selectedItemIds: Array.isArray(parsed.selectedItemIds) ? parsed.selectedItemIds : [],
      selectedItems: Array.isArray(parsed.selectedItems) ? parsed.selectedItems : [],
      project: { ...initialProject, ...(parsed.project ?? {}) },
      lastEstimate: parsed.lastEstimate ?? null,
    }
  } catch {
    return initialPersistedState
  }
}

function toPersistedState(state: EstimateDraftState): PersistedDraftState {
  return {
    selectedItemIds: state.selectedItemIds,
    selectedItems: state.selectedItems,
    project: state.project,
    lastEstimate: state.lastEstimate,
  }
}

export function EstimateDraftProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<EstimateDraftState>(() => ({ ...loadPersistedState(), customer: initialCustomer }))

  useEffect(() => {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(toPersistedState(state)))
  }, [state.selectedItemIds, state.selectedItems, state.project, state.lastEstimate])

  const setSelectedItemIds = useCallback((itemIds: number[]) => {
    setState((current) => ({ ...current, selectedItemIds: itemIds }))
  }, [])

  const toggleSelectedItemId = useCallback((itemId: number) => {
    setState((current) => {
      const selected = current.selectedItemIds.includes(itemId)
      const selectedItemIds = selected ? current.selectedItemIds.filter((id) => id !== itemId) : [...current.selectedItemIds, itemId]
      return { ...current, selectedItemIds }
    })
  }, [])

  const addOrUpdateItem = useCallback((item: EstimateLineInput) => {
    setState((current) => {
      const withoutSame = current.selectedItems.filter((selected) => selected.option_id !== item.option_id)
      return {
        ...current,
        selectedItems: [...withoutSame, { ...item, sort_order: withoutSame.length + 1 }],
      }
    })
  }, [])

  const updateQuantity = useCallback((optionId: number, quantity: string) => {
    setState((current) => ({
      ...current,
      selectedItems: current.selectedItems.map((item) => (item.option_id === optionId ? { ...item, quantity } : item)),
    }))
  }, [])

  const removeItem = useCallback((optionId: number) => {
    setState((current) => ({
      ...current,
      selectedItems: current.selectedItems
        .filter((item) => item.option_id !== optionId)
        .map((item, index) => ({ ...item, sort_order: index + 1 })),
    }))
  }, [])

  const removeOptionsForItems = useCallback((itemIds: number[]) => {
    setState((current) => ({
      ...current,
      selectedItems: current.selectedItems
        .filter((selected) => !itemIds.includes(selected.option_id))
        .map((item, index) => ({ ...item, sort_order: index + 1 })),
    }))
  }, [])

  const setCustomer = useCallback((customer: Partial<CustomerInfo>) => {
    setState((current) => ({ ...current, customer: { ...current.customer, ...customer } }))
  }, [])

  const setProject = useCallback((project: Partial<ProjectInfo>) => {
    setState((current) => ({ ...current, project: { ...current.project, ...project } }))
  }, [])

  const setLastEstimate = useCallback((estimate: EstimateDetail | null) => {
    setState((current) => ({ ...current, lastEstimate: estimate }))
  }, [])

  const resetDraft = useCallback(() => {
    setState({ ...initialPersistedState, customer: initialCustomer })
    window.localStorage.removeItem(STORAGE_KEY)
  }, [])

  const value = useMemo(
    () => ({
      ...state,
      setSelectedItemIds,
      toggleSelectedItemId,
      addOrUpdateItem,
      updateQuantity,
      removeItem,
      removeOptionsForItems,
      setCustomer,
      setProject,
      setLastEstimate,
      resetDraft,
    }),
    [state, setSelectedItemIds, toggleSelectedItemId, addOrUpdateItem, updateQuantity, removeItem, removeOptionsForItems, setCustomer, setProject, setLastEstimate, resetDraft],
  )

  return <EstimateDraftContext.Provider value={value}>{children}</EstimateDraftContext.Provider>
}

export function useEstimateDraft(): EstimateDraftContextValue {
  const context = useContext(EstimateDraftContext)
  if (!context) throw new Error('useEstimateDraft must be used within EstimateDraftProvider')
  return context
}
