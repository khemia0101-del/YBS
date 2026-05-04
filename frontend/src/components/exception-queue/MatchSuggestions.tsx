import { ExternalLink, Check } from 'lucide-react'
import type { MatchCandidate } from '../../types/models'

interface MatchSuggestionsProps {
  candidates: MatchCandidate[]
  onAcceptMatch: (entityId: string, entityType: string) => void
  isLoading?: boolean
}

export function MatchSuggestions({ candidates, onAcceptMatch, isLoading }: MatchSuggestionsProps) {
  if (!candidates || candidates.length === 0) {
    return (
      <div className="text-center py-6 text-sm text-slate-500">
        No match candidates found.
      </div>
    )
  }

  const top3 = candidates.slice(0, 3)

  return (
    <div className="space-y-3">
      <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wide">
        Match Candidates
      </h4>
      {top3.map((candidate) => {
        const pct = Math.round(candidate.confidence * 100)
        return (
          <div
            key={candidate.entity_id}
            className="border border-slate-200 rounded-lg p-3 bg-white hover:border-primary/40 transition-colors"
          >
            <div className="flex items-start justify-between gap-2 mb-2">
              <div>
                <p className="text-sm font-medium text-slate-900">{candidate.entity_name}</p>
                <p className="text-xs text-slate-500 capitalize">{candidate.entity_type}</p>
              </div>
              <span className="text-xs font-mono font-semibold text-slate-600 flex-shrink-0">
                {pct}%
              </span>
            </div>

            {/* Confidence bar */}
            <div className="w-full h-1.5 bg-slate-100 rounded-full mb-3">
              <div
                className={`h-full rounded-full ${
                  pct >= 90 ? 'bg-green-500' : pct >= 70 ? 'bg-yellow-500' : 'bg-red-500'
                }`}
                style={{ width: `${pct}%` }}
              />
            </div>

            {/* Match fields */}
            {Object.keys(candidate.match_fields).length > 0 && (
              <div className="mb-3 space-y-0.5">
                {Object.entries(candidate.match_fields)
                  .slice(0, 3)
                  .map(([field, value]) => (
                    <div key={field} className="flex gap-2 text-xs text-slate-600">
                      <span className="text-slate-400 capitalize">{field.replace(/_/g, ' ')}:</span>
                      <span className="font-medium truncate max-w-[120px]">
                        {String(value)}
                      </span>
                    </div>
                  ))}
              </div>
            )}

            <div className="flex items-center gap-2">
              <button
                type="button"
                disabled={isLoading}
                onClick={() => onAcceptMatch(candidate.entity_id, candidate.entity_type)}
                className="flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium bg-primary text-white rounded-md hover:bg-primary-dark transition-colors disabled:opacity-50"
              >
                <Check className="w-3 h-3" />
                Accept Match
              </button>
              <button
                type="button"
                className="flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium text-slate-600 bg-slate-100 rounded-md hover:bg-slate-200 transition-colors"
              >
                <ExternalLink className="w-3 h-3" />
                View
              </button>
            </div>
          </div>
        )
      })}
    </div>
  )
}
