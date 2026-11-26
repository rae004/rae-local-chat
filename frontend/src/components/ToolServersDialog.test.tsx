import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import type { ToolsInfo } from '../api/types'
import { toolsKey } from '../hooks/useTools'
import { toolServers } from '../lib/toolServers'
import { ToolServersDialog } from './ToolServersDialog'

const info: ToolsInfo = {
  servers: { filesystem: 'ok', github: 'error: 401' },
  tools: [
    { server: 'filesystem', name: 'a', qualified: 'filesystem__a', description: '', read_only: true },
    { server: 'filesystem', name: 'b', qualified: 'filesystem__b', description: '', read_only: true },
    { server: 'github', name: 'c', qualified: 'github__c', description: '', read_only: true },
  ],
}

function renderDialog(onClose = vi.fn()) {
  const qc = new QueryClient()
  qc.setQueryData(toolsKey, info)
  render(
    <QueryClientProvider client={qc}>
      <ToolServersDialog open onClose={onClose} />
    </QueryClientProvider>,
  )
  return onClose
}

beforeEach(() => toolServers.reset())

describe('ToolServersDialog', () => {
  it('lists servers with counts, status and the default github-off state', () => {
    renderDialog()
    expect(screen.getByText('2 tools')).toBeInTheDocument()
    expect(screen.getByLabelText('Enable filesystem')).toBeChecked()
    expect(screen.getByLabelText('Enable github')).not.toBeChecked()
    expect(screen.getByLabelText('github error: 401')).toBeInTheDocument()
  })

  it('toggling a server updates the shared store', () => {
    renderDialog()
    fireEvent.click(screen.getByLabelText('Enable github'))
    expect(toolServers.isEnabled('github')).toBe(true)
    fireEvent.click(screen.getByLabelText('Enable filesystem'))
    expect(toolServers.isEnabled('filesystem')).toBe(false)
  })

  it('Done closes', () => {
    const onClose = renderDialog()
    fireEvent.click(screen.getByRole('button', { name: 'Done' }))
    expect(onClose).toHaveBeenCalled()
  })
})
