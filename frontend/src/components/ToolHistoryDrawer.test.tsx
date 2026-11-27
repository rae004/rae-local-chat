import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import type { ToolCallHistory } from '../api/types'
import { toolCallsKey } from '../hooks/useToolCallHistory'
import { matches, summarize } from '../lib/toolHistory'
import { ToolHistoryDrawer } from './ToolHistoryDrawer'

const base = {
  server: 'fs',
  arguments: { path: 'x' },
  message_id: 'm1',
  created_at: '2026-11-26T10:00:00Z',
} as const

const rows: ToolCallHistory[] = [
  {
    ...base,
    id: 'c3',
    name: 'fs__write',
    read_only: false,
    status: 'pending',
    approved: false,
    result: 'denied',
    is_error: true,
  },
  {
    ...base,
    id: 'c2',
    name: 'fs__read',
    read_only: true,
    status: 'auto',
    approved: null,
    result: 'No such file',
    is_error: true,
  },
  {
    ...base,
    id: 'c1',
    name: 'fs__read',
    read_only: true,
    status: 'auto',
    approved: null,
    result: 'ok',
    is_error: false,
  },
  {
    ...base,
    id: 'c0',
    name: 'fs__write',
    read_only: false,
    status: 'pending',
    approved: true,
    result: '{}',
    is_error: false,
  },
]

function renderDrawer(data: ToolCallHistory[] = rows) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  qc.setQueryData(toolCallsKey('chat-1'), data)
  const onClose = vi.fn()
  render(
    <QueryClientProvider client={qc}>
      <ToolHistoryDrawer chatId="chat-1" onClose={onClose} />
    </QueryClientProvider>,
  )
  return onClose
}

describe('ToolHistoryDrawer', () => {
  it('shows a summary and one card per call, newest first', () => {
    renderDrawer()
    expect(screen.getByText('4 calls · 2 asked · 1 denied · 1 error')).toBeInTheDocument()
    const cards = screen.getAllByTestId('tool-call')
    expect(cards).toHaveLength(4)
    expect(cards[0]).toHaveTextContent('write')
    expect(cards[0]).toHaveTextContent('denied')
    expect(cards[1]).toHaveTextContent('error')
  })

  it('filters to asked and failed calls', () => {
    renderDrawer()
    fireEvent.click(screen.getByRole('button', { name: 'Asked' }))
    expect(screen.getAllByTestId('tool-call')).toHaveLength(2)
    fireEvent.click(screen.getByRole('button', { name: 'Failed' }))
    expect(screen.getAllByTestId('tool-call')).toHaveLength(2)
    fireEvent.click(screen.getByRole('button', { name: 'All' }))
    expect(screen.getAllByTestId('tool-call')).toHaveLength(4)
  })

  it('has an empty state and a close button', () => {
    const onClose = renderDrawer([])
    expect(screen.getByText('No tool calls in this chat yet.')).toBeInTheDocument()
    expect(screen.getByText('No calls')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Close history' }))
    expect(onClose).toHaveBeenCalled()
  })
})

describe('matches / summarize', () => {
  it('treats a call with no result row as failed', () => {
    const lost: ToolCallHistory = { ...rows[2], id: 'c9', result: null, is_error: null }
    expect(matches(lost, 'failed')).toBe(true)
    expect(matches(lost, 'asked')).toBe(false)
    expect(summarize([lost])).toBe('1 call · 0 asked · 1 error')
  })
})
