import { ExceptionQueue } from '../components/exception-queue/ExceptionQueue'

export function ExceptionQueuePage() {
  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-lg font-semibold text-slate-900">Exception Queue</h2>
        <p className="text-sm text-slate-500 mt-0.5">
          Review, approve, reject, or match staged records that could not be automatically processed.
        </p>
      </div>
      <ExceptionQueue />
    </div>
  )
}
