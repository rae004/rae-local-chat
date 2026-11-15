import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { ToolCallCard } from './ToolCallCard'

const call = {
  id: 'c1',
  name: 'fs__read_text_file',
  server: 'fs',
  arguments: { path: 'notes.txt' },
  read_only: true,
}

describe('ToolCallCard', () => {
  it('shows server · tool, a spinner while running, and the arguments', () => {
    render(<ToolCallCard call={call} running />)
    expect(screen.getByText('read_text_file')).toBeInTheDocument()
    expect(screen.getByText('fs ·')).toBeInTheDocument()
    expect(screen.getByLabelText('running')).toBeInTheDocument()
    expect(screen.getByText(/"path": "notes.txt"/)).toBeInTheDocument()
  })

  it('renders a successful read-only result as auto-approved', () => {
    render(
      <ToolCallCard
        call={call}
        result={{ id: 'c1', name: call.name, content: 'buy milk', is_error: false }}
      />,
    )
    expect(screen.getByText('auto · read-only')).toBeInTheDocument()
    expect(screen.getByText('buy milk')).toBeInTheDocument()
  })

  it('shows Approve/Deny while pending and reports the click', () => {
    const onDecide = vi.fn()
    render(<ToolCallCard call={{ ...call, read_only: false }} pending onDecide={onDecide} />)
    expect(screen.getByText('needs approval')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Approve' }))
    expect(onDecide).toHaveBeenCalledWith(true)
    fireEvent.click(screen.getByRole('button', { name: 'Deny' }))
    expect(onDecide).toHaveBeenCalledWith(false)
  })

  it('renders a denied call from its persisted decision', () => {
    render(
      <ToolCallCard
        call={{ ...call, read_only: false }}
        approved={false}
        result={{ id: 'c1', name: call.name, content: 'not run: denied', is_error: true }}
      />,
    )
    expect(screen.getByText('denied')).toBeInTheDocument()
    expect(screen.queryByRole('button')).toBeNull()
  })

  it('renders an approved write as approved', () => {
    render(
      <ToolCallCard
        call={{ ...call, read_only: false }}
        approved
        result={{ id: 'c1', name: call.name, content: 'ok', is_error: false }}
      />,
    )
    expect(screen.getByText('approved')).toBeInTheDocument()
  })

  it('flags errors', () => {
    render(
      <ToolCallCard
        call={{ ...call, read_only: false }}
        result={{ id: 'c1', name: call.name, content: 'needs approval', is_error: true }}
      />,
    )
    expect(screen.getByText('error', { selector: '.badge' })).toBeInTheDocument()
    expect(screen.getByText('needs approval')).toBeInTheDocument()
  })
})
