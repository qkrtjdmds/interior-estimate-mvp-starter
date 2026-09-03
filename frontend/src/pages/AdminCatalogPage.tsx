import { FormEvent, useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import {
  createAdminCategory,
  createAdminItem,
  createAdminOption,
  fetchAdminCategories,
  fetchAdminItems,
  fetchAdminOptions,
  updateAdminCategory,
  updateAdminItem,
  updateAdminOption,
} from '../api/adminCatalogApi'
import type { AdminCategory, AdminItem, AdminOption, CategoryPayload, ItemPayload, OptionPayload } from '../api/adminCatalogApi'
import { getAdminApiErrorMessage } from '../api/adminApi'
import ApiState from '../components/ApiState'
import { formatCurrency } from '../utils/format'

const UNIT_OPTIONS = ['평', '㎡', 'm', '개', '식', '세트', '건']

type EditorMode =
  | { type: 'category'; item: AdminCategory | null }
  | { type: 'item'; item: AdminItem | null }
  | { type: 'option'; item: AdminOption | null }
  | null

interface CategoryFormState {
  name: string
  description: string
  active: boolean
  customer_visible: boolean
  sort_order: string
}

interface ItemFormState extends CategoryFormState {
  category_id: string
}

interface OptionFormState extends CategoryFormState {
  item_id: string
  unit: string
  default_price: string
  recommended: boolean
}

function emptyCategoryForm(nextSortOrder: number): CategoryFormState {
  return { name: '', description: '', active: true, customer_visible: true, sort_order: String(nextSortOrder) }
}

function categoryForm(category: AdminCategory): CategoryFormState {
  return { name: category.name, description: category.description ?? '', active: category.active, customer_visible: category.customer_visible, sort_order: String(category.sort_order) }
}

function emptyItemForm(categoryId: number, nextSortOrder: number): ItemFormState {
  return { ...emptyCategoryForm(nextSortOrder), category_id: String(categoryId || '') }
}

function itemForm(item: AdminItem): ItemFormState {
  return { ...categoryForm(item), category_id: String(item.category_id) }
}

function emptyOptionForm(itemId: number, nextSortOrder: number): OptionFormState {
  return { ...emptyCategoryForm(nextSortOrder), item_id: String(itemId || ''), unit: '평', default_price: '0', recommended: false }
}

function optionForm(option: AdminOption): OptionFormState {
  return { ...categoryForm(option), item_id: String(option.item_id), unit: option.unit, default_price: String(option.default_price), recommended: option.recommended }
}

function numericSort(value: string): number {
  const parsed = Number(value)
  return Number.isInteger(parsed) && parsed >= 0 ? parsed : -1
}

function normalizeMoneyInput(value: string): string {
  return value.replace(/,/g, '').trim()
}

function priceLooksValid(value: string): boolean {
  const normalized = normalizeMoneyInput(value)
  return /^\d+(\.\d{1,2})?$/.test(normalized) && Number(normalized) >= 0
}

function nextOrder(rows: Array<{ sort_order: number }>): number {
  if (rows.length === 0) return 10
  return Math.max(...rows.map((row) => row.sort_order)) + 10
}

function visibilityText(active: boolean, customerVisible: boolean): string {
  if (!active) return '비활성'
  if (!customerVisible) return '관리자만'
  return '고객 노출'
}

function rowClass(active: boolean, selected: boolean): string {
  return ['catalog-admin-row', selected ? 'selected' : '', active ? '' : 'inactive'].filter(Boolean).join(' ')
}

function byOrder<T extends { sort_order: number; id: number }>(rows: T[]): T[] {
  return [...rows].sort((a, b) => a.sort_order - b.sort_order || a.id - b.id)
}

export default function AdminCatalogPage() {
  const [categories, setCategories] = useState<AdminCategory[]>([])
  const [items, setItems] = useState<AdminItem[]>([])
  const [options, setOptions] = useState<AdminOption[]>([])
  const [selectedCategoryId, setSelectedCategoryId] = useState<number | null>(null)
  const [selectedItemId, setSelectedItemId] = useState<number | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [editor, setEditor] = useState<EditorMode>(null)
  const [dirty, setDirty] = useState(false)

  const sortedCategories = useMemo(() => byOrder(categories), [categories])
  const selectedCategory = categories.find((category) => category.id === selectedCategoryId) ?? null
  const categoryItems = useMemo(() => byOrder(items.filter((item) => item.category_id === selectedCategoryId)), [items, selectedCategoryId])
  const selectedItem = items.find((item) => item.id === selectedItemId) ?? null
  const itemOptions = useMemo(() => byOrder(options.filter((option) => option.item_id === selectedItemId)), [options, selectedItemId])

  useEffect(() => {
    loadCatalog()
  }, [])

  function loadCatalog() {
    setLoading(true)
    setError(null)
    Promise.all([fetchAdminCategories(), fetchAdminItems(), fetchAdminOptions()])
      .then(([categoryRows, itemRows, optionRows]) => {
        setCategories(categoryRows)
        setItems(itemRows)
        setOptions(optionRows)
        const firstCategory = selectedCategoryId && categoryRows.some((row) => row.id === selectedCategoryId) ? selectedCategoryId : byOrder(categoryRows)[0]?.id ?? null
        setSelectedCategoryId(firstCategory)
        const itemsForCategory = itemRows.filter((row) => row.category_id === firstCategory)
        const firstItem = selectedItemId && itemRows.some((row) => row.id === selectedItemId) ? selectedItemId : byOrder(itemsForCategory)[0]?.id ?? null
        setSelectedItemId(firstItem)
      })
      .catch((requestError) => setError(getAdminApiErrorMessage(requestError)))
      .finally(() => setLoading(false))
  }

  function canChangeSelection(): boolean {
    if (!dirty) return true
    return window.confirm('작성 중인 변경사항이 있습니다. 저장하지 않고 이동할까요?')
  }

  function chooseCategory(categoryId: number) {
    if (!canChangeSelection()) return
    setSelectedCategoryId(categoryId)
    setSelectedItemId(byOrder(items.filter((item) => item.category_id === categoryId))[0]?.id ?? null)
    setEditor(null)
    setDirty(false)
  }

  function chooseItem(itemId: number) {
    if (!canChangeSelection()) return
    setSelectedItemId(itemId)
    setEditor(null)
    setDirty(false)
  }

  function openEditor(next: EditorMode) {
    if (!canChangeSelection()) return
    setEditor(next)
    setDirty(false)
    setNotice(null)
  }

  async function saveCategory(form: CategoryFormState, category: AdminCategory | null) {
    const sortOrder = numericSort(form.sort_order)
    if (!form.name.trim()) throw new Error('카테고리 이름을 입력해 주세요.')
    if (sortOrder < 0) throw new Error('노출 순서는 0 이상의 정수로 입력해 주세요.')
    const payload: CategoryPayload = { name: form.name.trim(), description: form.description.trim() || null, active: form.active, customer_visible: form.customer_visible, sort_order: sortOrder }
    const saved = category ? await updateAdminCategory(category.id, payload) : await createAdminCategory(payload)
    setCategories((current) => category ? current.map((row) => row.id === saved.id ? saved : row) : [...current, saved])
    setSelectedCategoryId(saved.id)
    setNotice('카테고리를 저장했습니다.')
  }

  async function saveItem(form: ItemFormState, item: AdminItem | null) {
    const sortOrder = numericSort(form.sort_order)
    const categoryId = Number(form.category_id)
    if (!form.name.trim()) throw new Error('시공 항목 이름을 입력해 주세요.')
    if (!categoryId) throw new Error('연결할 카테고리를 선택해 주세요.')
    if (sortOrder < 0) throw new Error('노출 순서는 0 이상의 정수로 입력해 주세요.')
    const payload: ItemPayload = { category_id: categoryId, name: form.name.trim(), description: form.description.trim() || null, active: form.active, customer_visible: form.customer_visible, sort_order: sortOrder }
    const saved = item ? await updateAdminItem(item.id, payload) : await createAdminItem(payload)
    setItems((current) => item ? current.map((row) => row.id === saved.id ? saved : row) : [...current, saved])
    setSelectedCategoryId(saved.category_id)
    setSelectedItemId(saved.id)
    setNotice('시공 항목을 저장했습니다.')
  }

  async function saveOption(form: OptionFormState, option: AdminOption | null) {
    const sortOrder = numericSort(form.sort_order)
    const itemId = Number(form.item_id)
    const price = normalizeMoneyInput(form.default_price)
    if (!form.name.trim()) throw new Error('옵션 이름을 입력해 주세요.')
    if (!itemId) throw new Error('연결할 시공 항목을 선택해 주세요.')
    if (!form.unit.trim()) throw new Error('단위를 입력해 주세요.')
    if (!priceLooksValid(price)) throw new Error('단가는 0 이상의 숫자이며 소수점은 둘째 자리까지만 입력해 주세요.')
    if (sortOrder < 0) throw new Error('노출 순서는 0 이상의 정수로 입력해 주세요.')
    const payload: OptionPayload = { item_id: itemId, name: form.name.trim(), description: form.description.trim() || null, unit: form.unit.trim(), default_price: price, recommended: form.recommended, active: form.active, customer_visible: form.customer_visible, sort_order: sortOrder }
    const saved = option ? await updateAdminOption(option.id, payload) : await createAdminOption(payload)
    setOptions((current) => option ? current.map((row) => row.id === saved.id ? saved : row) : [...current, saved])
    const parentItem = items.find((row) => row.id === saved.item_id)
    if (parentItem) setSelectedCategoryId(parentItem.category_id)
    setSelectedItemId(saved.item_id)
    setNotice('옵션을 저장했습니다.')
  }

  async function submitEditor(form: CategoryFormState | ItemFormState | OptionFormState) {
    if (!editor) return
    setSaving(true)
    setError(null)
    try {
      if (editor.type === 'category') await saveCategory(form as CategoryFormState, editor.item)
      if (editor.type === 'item') await saveItem(form as ItemFormState, editor.item)
      if (editor.type === 'option') await saveOption(form as OptionFormState, editor.item)
      setEditor(null)
      setDirty(false)
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : getAdminApiErrorMessage(requestError))
    } finally {
      setSaving(false)
    }
  }

  async function patchCategory(category: AdminCategory, payload: Partial<CategoryPayload>, message: string) {
    if (payload.active === false && !window.confirm('카테고리를 비활성화하면 고객 카탈로그에서 하위 시공 항목과 옵션도 함께 숨겨집니다. 계속할까요?')) return
    setSaving(true)
    try {
      const saved = await updateAdminCategory(category.id, payload)
      setCategories((current) => current.map((row) => row.id === saved.id ? saved : row))
      setNotice(message)
    } catch (requestError) {
      setError(getAdminApiErrorMessage(requestError))
    } finally {
      setSaving(false)
    }
  }

  async function patchItem(item: AdminItem, payload: Partial<ItemPayload>, message: string) {
    if (payload.active === false && !window.confirm('시공 항목을 비활성화하면 고객 카탈로그에서 연결된 옵션도 숨겨집니다. 계속할까요?')) return
    setSaving(true)
    try {
      const saved = await updateAdminItem(item.id, payload)
      setItems((current) => current.map((row) => row.id === saved.id ? saved : row))
      setNotice(message)
    } catch (requestError) {
      setError(getAdminApiErrorMessage(requestError))
    } finally {
      setSaving(false)
    }
  }

  async function patchOption(option: AdminOption, payload: Partial<OptionPayload>, message: string) {
    if (payload.active === false && !window.confirm('옵션을 비활성화하면 신규 고객 견적에서 선택할 수 없습니다. 과거 견적의 snapshot은 유지됩니다. 계속할까요?')) return
    setSaving(true)
    try {
      const saved = await updateAdminOption(option.id, payload)
      setOptions((current) => current.map((row) => row.id === saved.id ? saved : row))
      setNotice(message)
    } catch (requestError) {
      setError(getAdminApiErrorMessage(requestError))
    } finally {
      setSaving(false)
    }
  }

  return (
    <main className="admin-content admin-catalog-content">
      <header className="admin-page-header">
        <div>
          <h1>카탈로그 관리</h1>
          <p>고객 견적 화면에 노출되는 카테고리, 시공 항목, 옵션 단가와 순서를 관리합니다.</p>
        </div>
        <button className="button ghost-button" type="button" onClick={loadCatalog} disabled={loading || saving}>새로고침</button>
      </header>

      <section className="admin-catalog-note" aria-label="카탈로그 관리 안내">
        옵션 단가는 preview 계산에 쓰이는 기준 단가입니다. 저장된 견적은 당시 snapshot 단가와 금액을 보존합니다.
      </section>

      {notice && <p className="admin-success" role="status">{notice}</p>}
      {error && <ApiState title="처리 실패" message={error} action={<button className="button ghost-button" type="button" onClick={() => setError(null)}>닫기</button>} />}
      {loading && <ApiState title="카탈로그를 불러오는 중" message="관리자 기준정보를 조회하고 있습니다." />}

      {!loading && (
        <div className="admin-catalog-grid">
          <CatalogSection title="카테고리" description="비활성 카테고리는 고객 카탈로그에서 하위 항목까지 숨겨집니다." empty="등록된 카테고리가 없습니다." action={<button className="button primary-button" type="button" onClick={() => openEditor({ type: 'category', item: null })}>카테고리 추가</button>}>
            {sortedCategories.map((category) => (
              <article className={rowClass(category.active, category.id === selectedCategoryId)} key={category.id}>
                <button type="button" className="catalog-row-main" onClick={() => chooseCategory(category.id)}>
                  <span>{category.name}</span>
                  <strong>{items.filter((item) => item.category_id === category.id).length}개 항목</strong>
                  <em>{visibilityText(category.active, category.customer_visible)}</em>
                </button>
                <RowActions onEdit={() => openEditor({ type: 'category', item: category })} onToggle={() => patchCategory(category, { active: !category.active }, category.active ? '카테고리를 비활성화했습니다.' : '카테고리를 활성화했습니다.')} onMoveUp={() => patchCategory(category, { sort_order: Math.max(0, category.sort_order - 10) }, '카테고리 순서를 변경했습니다.')} onMoveDown={() => patchCategory(category, { sort_order: category.sort_order + 10 }, '카테고리 순서를 변경했습니다.')} active={category.active} saving={saving} />
              </article>
            ))}
          </CatalogSection>

          <CatalogSection title="시공 항목" description={selectedCategory ? `${selectedCategory.name} 안의 시공 항목입니다.` : '카테고리를 먼저 선택해 주세요.'} empty={selectedCategory ? '등록된 시공 항목이 없습니다.' : '선택된 카테고리가 없습니다.'} action={<button className="button primary-button" type="button" disabled={!selectedCategoryId} onClick={() => openEditor({ type: 'item', item: null })}>시공 항목 추가</button>}>
            {categoryItems.map((item) => (
              <article className={rowClass(item.active, item.id === selectedItemId)} key={item.id}>
                <button type="button" className="catalog-row-main" onClick={() => chooseItem(item.id)}>
                  <span>{item.name}</span>
                  <strong>{options.filter((option) => option.item_id === item.id).length}개 옵션</strong>
                  <em>{visibilityText(item.active, item.customer_visible)}</em>
                </button>
                <RowActions onEdit={() => openEditor({ type: 'item', item })} onToggle={() => patchItem(item, { active: !item.active }, item.active ? '시공 항목을 비활성화했습니다.' : '시공 항목을 활성화했습니다.')} onMoveUp={() => patchItem(item, { sort_order: Math.max(0, item.sort_order - 10) }, '시공 항목 순서를 변경했습니다.')} onMoveDown={() => patchItem(item, { sort_order: item.sort_order + 10 }, '시공 항목 순서를 변경했습니다.')} active={item.active} saving={saving} />
              </article>
            ))}
          </CatalogSection>

          <CatalogSection title="세부 옵션" description={selectedItem ? `${selectedItem.name} 옵션입니다. 표시된 단가는 신규 preview 계산 기준입니다.` : '시공 항목을 먼저 선택해 주세요.'} empty={selectedItem ? '등록된 옵션이 없습니다.' : '선택된 시공 항목이 없습니다.'} action={<button className="button primary-button" type="button" disabled={!selectedItemId} onClick={() => openEditor({ type: 'option', item: null })}>옵션 추가</button>}>
            {itemOptions.map((option) => (
              <article className={rowClass(option.active, false)} key={option.id}>
                <button type="button" className="catalog-row-main option-row-main" onClick={() => openEditor({ type: 'option', item: option })}>
                  <span>{option.name}</span>
                  <strong>{formatCurrency(option.default_price)} / {option.unit}</strong>
                  <em>{visibilityText(option.active, option.customer_visible)}{option.recommended ? ' · 추천' : ''}</em>
                </button>
                <RowActions onEdit={() => openEditor({ type: 'option', item: option })} onToggle={() => patchOption(option, { active: !option.active }, option.active ? '옵션을 비활성화했습니다.' : '옵션을 활성화했습니다.')} onMoveUp={() => patchOption(option, { sort_order: Math.max(0, option.sort_order - 10) }, '옵션 순서를 변경했습니다.')} onMoveDown={() => patchOption(option, { sort_order: option.sort_order + 10 }, '옵션 순서를 변경했습니다.')} active={option.active} saving={saving} />
              </article>
            ))}
          </CatalogSection>
        </div>
      )}

      {editor && <CatalogEditor editor={editor} categories={sortedCategories} items={byOrder(items)} selectedCategoryId={selectedCategoryId} selectedItemId={selectedItemId} saving={saving} onDirty={() => setDirty(true)} onCancel={() => { setEditor(null); setDirty(false) }} onSubmit={submitEditor} />}
    </main>
  )
}

function CatalogSection({ title, description, empty, action, children }: { title: string; description: string; empty: string; action: ReactNode; children: ReactNode }) {
  const hasChildren = Array.isArray(children) ? children.length > 0 : Boolean(children)
  return (
    <section className="admin-catalog-section">
      <header><div><h2>{title}</h2><p>{description}</p></div>{action}</header>
      <div className="catalog-admin-list">{hasChildren ? children : <div className="catalog-empty">{empty}</div>}</div>
    </section>
  )
}

function RowActions({ onEdit, onToggle, onMoveUp, onMoveDown, active, saving }: { onEdit: () => void; onToggle: () => void; onMoveUp: () => void; onMoveDown: () => void; active: boolean; saving: boolean }) {
  return <div className="catalog-row-actions"><button type="button" onClick={onEdit} disabled={saving}>수정</button><button type="button" onClick={onMoveUp} disabled={saving}>위</button><button type="button" onClick={onMoveDown} disabled={saving}>아래</button><button type="button" onClick={onToggle} disabled={saving}>{active ? '비활성화' : '활성화'}</button></div>
}

function CatalogEditor({ editor, categories, items, selectedCategoryId, selectedItemId, saving, onDirty, onCancel, onSubmit }: { editor: EditorMode; categories: AdminCategory[]; items: AdminItem[]; selectedCategoryId: number | null; selectedItemId: number | null; saving: boolean; onDirty: () => void; onCancel: () => void; onSubmit: (form: CategoryFormState | ItemFormState | OptionFormState) => Promise<void> }) {
  const [categoryState, setCategoryState] = useState<CategoryFormState>(() => editor?.type === 'category' && editor.item ? categoryForm(editor.item) : emptyCategoryForm(nextOrder(categories)))
  const [itemState, setItemState] = useState<ItemFormState>(() => editor?.type === 'item' && editor.item ? itemForm(editor.item) : emptyItemForm(selectedCategoryId ?? 0, nextOrder(items.filter((item) => item.category_id === selectedCategoryId))))
  const [optionState, setOptionState] = useState<OptionFormState>(() => editor?.type === 'option' && editor.item ? optionForm(editor.item) : emptyOptionForm(selectedItemId ?? 0, 10))

  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') onCancel()
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [onCancel])

  if (!editor) return null
  const title = editor.type === 'category' ? (editor.item ? '카테고리 수정' : '카테고리 추가') : editor.type === 'item' ? (editor.item ? '시공 항목 수정' : '시공 항목 추가') : editor.item ? '옵션 수정' : '옵션 추가'
  const form = editor.type === 'category' ? categoryState : editor.type === 'item' ? itemState : optionState

  function handleSubmit(event: FormEvent) {
    event.preventDefault()
    onSubmit(form)
  }

  return (
    <section className="catalog-editor" aria-label={title}>
      <form onSubmit={handleSubmit}>
        <header><div><span>관리자 편집</span><h2>{title}</h2></div><button type="button" className="admin-close-button" onClick={onCancel} aria-label="닫기">×</button></header>
        {editor.type === 'category' && <CategoryFields state={categoryState} setState={setCategoryState} onDirty={onDirty} />}
        {editor.type === 'item' && <ItemFields state={itemState} setState={setItemState} categories={categories} onDirty={onDirty} />}
        {editor.type === 'option' && <OptionFields state={optionState} setState={setOptionState} items={items} onDirty={onDirty} />}
        <div className="catalog-editor-actions"><button className="button ghost-button" type="button" onClick={onCancel} disabled={saving}>취소</button><button className="button primary-button" type="submit" disabled={saving}>{saving ? '저장 중' : '저장'}</button></div>
      </form>
    </section>
  )
}

function CategoryFields({ state, setState, onDirty }: { state: CategoryFormState; setState: (value: CategoryFormState) => void; onDirty: () => void }) {
  function update(next: Partial<CategoryFormState>) { setState({ ...state, ...next }); onDirty() }
  return (
    <div className="catalog-form-grid">
      <label htmlFor="catalog-name">이름<input id="catalog-name" value={state.name} maxLength={100} onChange={(event) => update({ name: event.target.value })} required /></label>
      <label htmlFor="catalog-description">설명<textarea id="catalog-description" rows={3} value={state.description} onChange={(event) => update({ description: event.target.value })} /></label>
      <label htmlFor="catalog-sort-order">노출 순서<input id="catalog-sort-order" type="number" min="0" step="1" value={state.sort_order} onChange={(event) => update({ sort_order: event.target.value })} required /></label>
      <label className="checkbox-label"><input type="checkbox" checked={state.active} onChange={(event) => update({ active: event.target.checked })} />활성 상태</label>
      <label className="checkbox-label"><input type="checkbox" checked={state.customer_visible} onChange={(event) => update({ customer_visible: event.target.checked })} />고객 화면 노출</label>
    </div>
  )
}

function ItemFields({ state, setState, categories, onDirty }: { state: ItemFormState; setState: (value: ItemFormState) => void; categories: AdminCategory[]; onDirty: () => void }) {
  function update(next: Partial<ItemFormState>) { setState({ ...state, ...next }); onDirty() }
  return <><CategoryFields state={state} setState={(value) => setState({ ...state, ...value })} onDirty={onDirty} /><label htmlFor="item-category">연결 카테고리<select id="item-category" value={state.category_id} onChange={(event) => update({ category_id: event.target.value })} required>{categories.map((category) => <option value={category.id} key={category.id}>{category.name}</option>)}</select></label></>
}

function OptionFields({ state, setState, items, onDirty }: { state: OptionFormState; setState: (value: OptionFormState) => void; items: AdminItem[]; onDirty: () => void }) {
  function update(next: Partial<OptionFormState>) { setState({ ...state, ...next }); onDirty() }
  return (
    <>
      <CategoryFields state={state} setState={(value) => setState({ ...state, ...value })} onDirty={onDirty} />
      <label htmlFor="option-item">연결 시공 항목<select id="option-item" value={state.item_id} onChange={(event) => update({ item_id: event.target.value })} required>{items.map((item) => <option value={item.id} key={item.id}>{item.name}</option>)}</select></label>
      <label htmlFor="option-unit">단위<input id="option-unit" list="unit-options" value={state.unit} maxLength={20} onChange={(event) => update({ unit: event.target.value })} required /></label>
      <datalist id="unit-options">{UNIT_OPTIONS.map((unit) => <option value={unit} key={unit} />)}</datalist>
      <label htmlFor="option-price">단가<input id="option-price" inputMode="decimal" value={state.default_price} onChange={(event) => update({ default_price: event.target.value })} required /></label>
      <label className="checkbox-label"><input type="checkbox" checked={state.recommended} onChange={(event) => update({ recommended: event.target.checked })} />추천 옵션</label>
    </>
  )
}