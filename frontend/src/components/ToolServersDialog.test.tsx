import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { ToolsInfo } from '../api/types'
import { allowRulesKey, toolsKey } from '../hooks/useTools'
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

function renderDialog(onClose = vi.fn(), rules: { tool: string }[] = []) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  qc.setQueryData(toolsKey, info)
  qc.setQueryData(allowRulesKey, rules)
  render(
    <QueryClientProvider client={qc}>
      <ToolServersDialog open onClose={onClose} />
    </QueryClientProvider>,
  )
  return onClose
}

beforeEach(() => toolServers.reset())
afterEach(() => vi.restoreAllMocks())

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

  it('lists always-allow rules and revokes one', async () => {
    const fetchMock = vi
      .spyOn(globalThis, 'fetch')
      .mockResolvedValue(new Response(null, { status: 204 }))
    renderDialog(vi.fn(), [{ tool: 'shell__run' }])
    expect(screen.getByText('shell__run')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Revoke' }))
    await waitFor(() =>
      expect(
        fetchMock.mock.calls.some(
          ([url, init]) =>
            String(url).endsWith('/tools/allow-rules/shell__run') &&
            (init as RequestInit | undefined)?.method === 'DELETE',
        ),
      ).toBe(true),
    )
  })

  it('says so when there are no rules', () => {
    renderDialog()
    expect(screen.getByText(/Every tool that modifies state asks first/)).toBeInTheDocument()
  })

  it('Done closes', () => {
    const onClose = renderDialog()
    fireEvent.click(screen.getByRole('button', { name: 'Done' }))
    expect(onClose).toHaveBeenCalled()
  })
})
