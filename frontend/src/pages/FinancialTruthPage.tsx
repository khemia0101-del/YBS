import { useState } from 'react'
import { ProfitabilityDashboard } from '../components/financial/ProfitabilityDashboard'
import { DSOChart } from '../components/financial/DSOChart'
import { ConcentrationRisk } from '../components/financial/ConcentrationRisk'
import clsx from 'clsx'

type Tab = 'profitability' | 'dso' | 'concentration'

const TABS: { id: Tab; label: string }[] = [
  { id: 'profitability', label: 'Profitability' },
  { id: 'dso', label: 'DSO Trend' },
  { id: 'concentration', label: 'Concentration Risk' },
]

export function FinancialTruthPage() {
  const [activeTab, setActiveTab] = useState<Tab>('profitability')

  return (
    <div className="space-y-5">
      <div>
        <h2 className="text-lg font-semibold text-slate-900">Financial Truth</h2>
        <p className="text-sm text-slate-500 mt-0.5">
          Single source of truth for profitability, receivables, and customer concentration.
        </p>
      </div>

      {/* Tab bar */}
      <div className="border-b border-slate-200">
        <nav className="flex gap-1">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              type="button"
              onClick={() => setActiveTab(tab.id)}
              className={clsx(
                'px-4 py-2.5 text-sm font-medium border-b-2 -mb-px transition-colors',
                activeTab === tab.id
                  ? 'border-primary text-primary'
                  : 'border-transparent text-slate-600 hover:text-slate-900 hover:border-slate-300'
              )}
            >
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab content */}
      <div>
        {activeTab === 'profitability' && <ProfitabilityDashboard />}
        {activeTab === 'dso' && (
          <div className="card px-5 py-5">
            <h3 className="font-semibold text-slate-900 mb-4">Days Sales Outstanding — 12 Month Trend</h3>
            <DSOChart />
          </div>
        )}
        {activeTab === 'concentration' && (
          <div className="card px-5 py-5">
            <h3 className="font-semibold text-slate-900 mb-1">Customer Revenue Concentration</h3>
            <p className="text-sm text-slate-500 mb-4">
              Top customers by revenue percentage. Red indicates &gt;25% concentration risk.
            </p>
            <ConcentrationRisk />
          </div>
        )}
      </div>
    </div>
  )
}
