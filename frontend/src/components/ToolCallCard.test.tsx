import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

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
