import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, renderHook, waitFor } from '@testing-library/react'
import type { ReactNode } from 'react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { Chat } from '../api/types'
import { chatsKey, useDeleteChat, useRenameChat } from './useChats'
import { messagesKey } from './useMessages'

const chat = (id: string, title: string): Chat => ({
  id,
  title,
  created_at: '2026-10-25T00:00:00Z',
  updated_at: '2026-10-25T00:00:00Z',
})

function setup<T>(hook: () => T) {
  const qc = new QueryClient()
  qc.setQueryData(chatsKey, [chat('a', 'Alpha'), chat('b', 'Beta')])
  qc.setQueryData(messagesKey('a'), [])
  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={qc}>{children}</QueryClientProvider>
  )
  return { qc, hook: renderHook(hook, { wrapper }) }
}

afterEach(() => vi.restoreAllMocks())

describe('chat mutations', () => {
  it('useDeleteChat drops the chat and its messages from the cache', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(null, { status: 204 }))
    const { qc, hook } = setup(() => useDeleteChat())

    await act(() => hook.result.current.mutateAsync('a'))

    await waitFor(() =>
      expect(qc.getQueryData<Chat[]>(chatsKey)?.map((c) => c.id)).toEqual(['b']),
    )
    expect(qc.getQueryData(messagesKey('a'))).toBeUndefined()
  })

  it('useRenameChat replaces the chat in the cache', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify(chat('b', 'Gamma')), { status: 200 }),
    )
    const { qc, hook } = setup(() => useRenameChat())

    await act(() => hook.result.current.mutateAsync({ chatId: 'b', title: 'Gamma' }))

    await waitFor(() =>
      expect(qc.getQueryData<Chat[]>(chatsKey)?.map((c) => c.title)).toEqual(['Alpha', 'Gamma']),
    )
  })
})
