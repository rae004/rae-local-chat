import { useState } from 'react'

import { useToolCallHistory } from '../hooks/useToolCallHistory'
import { type HistoryFilter, matches, summarize } from '../lib/toolHistory'
import { ToolCallCard } from './ToolCallCard'

const FILTERS: { key: HistoryFilter; label: string }[] = [
  { key: 'all', label: 'All' },
  { key: 'asked', label: 'Asked' },
  { key: 'failed', label: 'Failed' },
]

interface Props {
  chatId: string
  onClose: () => void
}

/** Side panel listing every tool call in the chat, newest first, with a summary and filters. */
export function ToolHistoryDrawer({ chatId, onClose }: Props) {
  const history = useToolCallHistory(chatId)
  const [filter, setFilter] = useState<HistoryFilter>('all')
  const rows = history.data ?? []
  const shown = rows.filter((r) => matches(r, filter))

  return (
    <aside
      className="flex w-80 shrink-0 flex-col border-l border-base-300 bg-base-100"
      aria-label="Tool call history"
    >
      <div className="flex items-center gap-2 border-b border-base-300 px-3 py-2">
        <h3 className="flex-1 text-sm font-semibold">Tool calls</h3>
        <button
          type="button"
          className="btn btn-ghost btn-xs btn-circle"
          aria-label="Close history"
          onClick={onClose}
        >
          ✕
        </button>
      </div>
      <div className="space-y-2 border-b border-base-300 px-3 py-2">
        <p className="text-xs opacity-70">{summarize(rows)}</p>
        <div className="join" role="group" aria-label="Filter">
          {FILTERS.map((f) => (
            <button
              key={f.key}
              type="button"
              className={`btn join-item btn-xs ${filter === f.key ? 'btn-active' : ''}`}
              aria-pressed={filter === f.key}
              onClick={() => setFilter(f.key)}
            >
              {f.label}
            </button>
          ))}
        </div>
      </div>
      <div className="flex-1 overflow-y-auto px-3 py-2">
        {history.isPending ? (
          <span className="loading loading-dots loading-sm" />
        ) : history.isError ? (
          <div role="alert" className="alert alert-error text-xs">
            Failed to load history: {history.error.message}
          </div>
        ) : shown.length === 0 ? (
          <p className="text-sm opacity-60">
            {rows.length === 0 ? 'No tool calls in this chat yet.' : 'Nothing matches this filter.'}
          </p>
        ) : (
          shown.map((row) => (
            <div key={row.id} data-testid="history-row">
              <time
                dateTime={row.created_at}
                className="block pt-1 text-right text-[10px] opacity-50"
              >
                {new Date(row.created_at).toLocaleString()}
              </time>
              <ToolCallCard
                call={row}
                approved={row.approved}
                result={
                  row.result === null
                    ? null
                    : {
                        id: row.id,
                        name: row.name,
                        content: row.result,
                        is_error: Boolean(row.is_error),
                      }
                }
              />
            </div>
          ))
        )}
      </div>
    </aside>
  )
}
