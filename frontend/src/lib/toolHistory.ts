import type { ToolCallHistory } from '../api/types'

export type HistoryFilter = 'all' | 'asked' | 'failed'

/**
 * `asked` = the user decided (rows persisted before statuses existed read `auto`, so go by
 * the decision, not the status); `failed` = denied, errored, or never answered.
 */
export function matches(row: ToolCallHistory, filter: HistoryFilter): boolean {
  switch (filter) {
    case 'all':
      return true
    case 'asked':
      return row.approved !== null
    case 'failed':
      return row.approved === false || row.is_error !== false
  }
}

export function summarize(rows: ToolCallHistory[]): string {
  if (rows.length === 0) return 'No calls'
  const n = rows.length
  const asked = rows.filter((r) => r.approved !== null).length
  const denied = rows.filter((r) => r.approved === false).length
  const errors = rows.filter((r) => r.approved !== false && r.is_error !== false).length
  const parts = [`${n} ${n === 1 ? 'call' : 'calls'}`, `${asked} asked`]
  if (denied) parts.push(`${denied} denied`)
  if (errors) parts.push(`${errors} ${errors === 1 ? 'error' : 'errors'}`)
  return parts.join(' · ')
}
