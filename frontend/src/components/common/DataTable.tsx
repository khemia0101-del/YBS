import { ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight } from 'lucide-react'
import clsx from 'clsx'

export interface Column<T> {
  key: string
  header: string
  render: (row: T) => React.ReactNode
  className?: string
  headerClassName?: string
  sortable?: boolean
}

interface DataTableProps<T> {
  columns: Column<T>[]
  data: T[]
  keyExtractor: (row: T) => string
  isLoading?: boolean
  emptyMessage?: string
  totalItems?: number
  currentPage?: number
  pageSize?: number
  onPageChange?: (page: number) => void
  onRowClick?: (row: T) => void
  expandedRowId?: string | null
  renderExpanded?: (row: T) => React.ReactNode
  selectable?: boolean
  selectedIds?: Set<string>
  onSelectRow?: (id: string) => void
  onSelectAll?: (ids: string[]) => void
  sortBy?: string
  sortDir?: 'asc' | 'desc'
  onSort?: (key: string, dir: 'asc' | 'desc') => void
}

function SkeletonRow({ cols }: { cols: number }) {
  return (
    <tr>
      {Array.from({ length: cols }).map((_, i) => (
        <td key={i} className="px-4 py-3">
          <div className="h-4 bg-slate-200 rounded animate-pulse" />
        </td>
      ))}
    </tr>
  )
}

export function DataTable<T>({
  columns,
  data,
  keyExtractor,
  isLoading,
  emptyMessage = 'No data available.',
  totalItems = 0,
  currentPage = 1,
  pageSize = 25,
  onPageChange,
  onRowClick,
  expandedRowId,
  renderExpanded,
  selectable,
  selectedIds,
  onSelectRow,
  onSelectAll,
  sortBy,
  sortDir,
  onSort,
}: DataTableProps<T>) {
  const totalPages = Math.ceil(totalItems / pageSize)
  const allSelected = data.length > 0 && data.every((row) => selectedIds?.has(keyExtractor(row)))
  const someSelected = !allSelected && data.some((row) => selectedIds?.has(keyExtractor(row)))

  const handleSort = (col: Column<T>) => {
    if (!col.sortable || !onSort) return
    const newDir = sortBy === col.key && sortDir === 'asc' ? 'desc' : 'asc'
    onSort(col.key, newDir)
  }

  const handleSelectAll = () => {
    if (!onSelectAll) return
    if (allSelected) {
      onSelectAll([])
    } else {
      onSelectAll(data.map(keyExtractor))
    }
  }

  return (
    <div className="flex flex-col">
      <div className="overflow-x-auto rounded-lg border border-slate-200">
        <table className="min-w-full divide-y divide-slate-200">
          <thead className="bg-slate-50">
            <tr>
              {selectable && (
                <th className="w-10 px-4 py-3">
                  <input
                    type="checkbox"
                    checked={allSelected}
                    ref={(el) => {
                      if (el) el.indeterminate = someSelected
                    }}
                    onChange={handleSelectAll}
                    className="rounded border-slate-300 text-primary focus:ring-primary"
                  />
                </th>
              )}
              {columns.map((col) => (
                <th
                  key={col.key}
                  onClick={() => handleSort(col)}
                  className={clsx(
                    'px-4 py-3 text-left text-xs font-semibold text-slate-600 uppercase tracking-wide whitespace-nowrap',
                    col.headerClassName,
                    col.sortable && 'cursor-pointer select-none hover:bg-slate-100'
                  )}
                >
                  <span className="inline-flex items-center gap-1">
                    {col.header}
                    {col.sortable && sortBy === col.key && (
                      <span className="text-primary">{sortDir === 'asc' ? '↑' : '↓'}</span>
                    )}
                  </span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 bg-white">
            {isLoading ? (
              Array.from({ length: 5 }).map((_, i) => (
                <SkeletonRow key={i} cols={(selectable ? 1 : 0) + columns.length} />
              ))
            ) : data.length === 0 ? (
              <tr>
                <td
                  colSpan={(selectable ? 1 : 0) + columns.length}
                  className="px-4 py-12 text-center text-sm text-slate-500"
                >
                  {emptyMessage}
                </td>
              </tr>
            ) : (
              data.map((row) => {
                const id = keyExtractor(row)
                const isExpanded = expandedRowId === id
                const isSelected = selectedIds?.has(id)

                return (
                  <>
                    <tr
                      key={id}
                      onClick={() => onRowClick?.(row)}
                      className={clsx(
                        'transition-colors',
                        onRowClick && 'cursor-pointer',
                        isSelected ? 'bg-blue-50' : 'hover:bg-slate-50',
                        isExpanded && 'bg-blue-50 border-l-2 border-l-primary'
                      )}
                    >
                      {selectable && (
                        <td className="w-10 px-4 py-3" onClick={(e) => e.stopPropagation()}>
                          <input
                            type="checkbox"
                            checked={isSelected ?? false}
                            onChange={() => onSelectRow?.(id)}
                            className="rounded border-slate-300 text-primary focus:ring-primary"
                          />
                        </td>
                      )}
                      {columns.map((col) => (
                        <td
                          key={col.key}
                          className={clsx('px-4 py-3 text-sm text-slate-700', col.className)}
                        >
                          {col.render(row)}
                        </td>
                      ))}
                    </tr>
                    {isExpanded && renderExpanded && (
                      <tr key={`${id}-expanded`}>
                        <td
                          colSpan={(selectable ? 1 : 0) + columns.length}
                          className="bg-blue-50/50 px-4 py-4 border-b border-blue-100"
                        >
                          {renderExpanded(row)}
                        </td>
                      </tr>
                    )}
                  </>
                )
              })
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {totalItems > pageSize && onPageChange && (
        <div className="flex items-center justify-between px-2 py-3 mt-2">
          <span className="text-sm text-slate-600">
            Showing {(currentPage - 1) * pageSize + 1}–
            {Math.min(currentPage * pageSize, totalItems)} of {totalItems.toLocaleString()}
          </span>
          <div className="flex items-center gap-1">
            <button
              type="button"
              onClick={() => onPageChange(1)}
              disabled={currentPage === 1}
              className="btn-secondary px-2 py-1 disabled:opacity-40"
            >
              <ChevronsLeft className="w-4 h-4" />
            </button>
            <button
              type="button"
              onClick={() => onPageChange(currentPage - 1)}
              disabled={currentPage === 1}
              className="btn-secondary px-2 py-1 disabled:opacity-40"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <span className="px-3 py-1 text-sm text-slate-700">
              Page {currentPage} of {totalPages}
            </span>
            <button
              type="button"
              onClick={() => onPageChange(currentPage + 1)}
              disabled={currentPage >= totalPages}
              className="btn-secondary px-2 py-1 disabled:opacity-40"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
            <button
              type="button"
              onClick={() => onPageChange(totalPages)}
              disabled={currentPage >= totalPages}
              className="btn-secondary px-2 py-1 disabled:opacity-40"
            >
              <ChevronsRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
