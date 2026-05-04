import { create } from 'zustand'

interface ExceptionFiltersState {
  status: string
  record_type: string
  source_system: string
  min_confidence: number
  max_confidence: number
  date_from: string
  date_to: string
  page: number
  page_size: number
  sort_by: string
  sort_dir: 'asc' | 'desc'
  // Selected rows for bulk actions
  selectedIds: Set<string>
}

interface ExceptionStoreActions {
  setStatus: (status: string) => void
  setRecordType: (type: string) => void
  setSourceSystem: (system: string) => void
  setConfidenceRange: (min: number, max: number) => void
  setDateRange: (from: string, to: string) => void
  setPage: (page: number) => void
  setPageSize: (size: number) => void
  setSortBy: (field: string, dir: 'asc' | 'desc') => void
  resetFilters: () => void
  toggleSelected: (id: string) => void
  selectAll: (ids: string[]) => void
  clearSelected: () => void
}

type ExceptionStore = ExceptionFiltersState & ExceptionStoreActions

const defaultFilters: ExceptionFiltersState = {
  status: '',
  record_type: '',
  source_system: '',
  min_confidence: 0,
  max_confidence: 1,
  date_from: '',
  date_to: '',
  page: 1,
  page_size: 25,
  sort_by: 'created_at',
  sort_dir: 'desc',
  selectedIds: new Set(),
}

export const useExceptionStore = create<ExceptionStore>((set) => ({
  ...defaultFilters,

  setStatus: (status) => set({ status, page: 1 }),
  setRecordType: (record_type) => set({ record_type, page: 1 }),
  setSourceSystem: (source_system) => set({ source_system, page: 1 }),
  setConfidenceRange: (min_confidence, max_confidence) =>
    set({ min_confidence, max_confidence, page: 1 }),
  setDateRange: (date_from, date_to) => set({ date_from, date_to, page: 1 }),
  setPage: (page) => set({ page }),
  setPageSize: (page_size) => set({ page_size, page: 1 }),
  setSortBy: (sort_by, sort_dir) => set({ sort_by, sort_dir }),
  resetFilters: () => set({ ...defaultFilters, selectedIds: new Set() }),

  toggleSelected: (id) =>
    set((state) => {
      const next = new Set(state.selectedIds)
      if (next.has(id)) {
        next.delete(id)
      } else {
        next.add(id)
      }
      return { selectedIds: next }
    }),

  selectAll: (ids) => set({ selectedIds: new Set(ids) }),
  clearSelected: () => set({ selectedIds: new Set() }),
}))
