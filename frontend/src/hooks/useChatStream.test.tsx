import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, renderHook, waitFor } from '@testing-library/react'
import type { ReactNode } from 'react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { Message } from '../api/types'
import { useChatStream } from './useChatStream'
import { messagesKey } from './useMessages'

const CHAT = 'c1'
const msg = (id: string, role: Message['role'], content: string): Message => ({
  id,
  chat_id: CHAT,
  role,
  content,
  model: role === 'assistant' ? 'fake' : null,
  created_at: '2026-10-25T00:00:00Z',
})

function sseResponse(blocks: string[]) {
  const enc = new TextEncoder()
  const body = new ReadableStream<Uint8Array>({
    start(controller) {
      for (const b of blocks) controller.enqueue(enc.encode(b))
      controller.close()
    },
  })
  return new Response(body, { status: 200, headers: { 'Content-Type': 'text/event-stream' } })
}

const ev = (event: string, data: unknown) => `event: ${event}\ndata: ${JSON.stringify(data)}\n\n`

function setup() {
  const qc = new QueryClient()
  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={qc}>{children}</QueryClientProvider>
  )
  const hook = renderHook(() => useChatStream(CHAT), { wrapper })
  return { qc, hook }
}

afterEach(() => vi.restoreAllMocks())

describe('useChatStream', () => {
  it('splices user + assistant into the Query cache and clears partial on done', async () => {
    const user = msg('u1', 'user', 'hi')
    const assistant = msg('a1', 'assistant', 'Hello!')
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      sseResponse([
        ev('user', user),
        ev('token', { content: 'Hel' }),
        ev('token', { content: 'lo!' }),
        ev('done', assistant),
      ]),
    )
    const { qc, hook } = setup()

    await act(() => hook.result.current.send('hi'))

    await waitFor(() => expect(hook.result.current.isStreaming).toBe(false))
    expect(hook.result.current.partial).toBe('')
    expect(hook.result.current.error).toBeNull()
    expect(qc.getQueryData<Message[]>(messagesKey(CHAT))).toEqual([user, assistant])
  })

  it('surfaces server error events and keeps the user message', async () => {
    const user = msg('u1', 'user', 'hi')
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      sseResponse([ev('user', user), ev('error', { detail: 'model exploded' })]),
    )
    const { qc, hook } = setup()

    await act(() => hook.result.current.send('hi'))

    await waitFor(() => expect(hook.result.current.error).toBe('model exploded'))
    expect(qc.getQueryData<Message[]>(messagesKey(CHAT))).toEqual([user])
  })

  it('splices tool rounds into the cache and exposes results before their rows land', async () => {
    const user = msg('u1', 'user', 'read notes')
    const call = {
      id: 'c1',
      name: 'fs__read',
      server: 'fs',
      arguments: { path: 'notes.txt' },
      read_only: true,
    }
    const turn: Message = { ...msg('a1', 'assistant', ''), tool_calls: [call] }
    const toolRow: Message = {
      ...msg('t1', 'tool', 'buy milk'),
      tool_call_id: 'c1',
      tool_name: 'fs__read',
      tool_is_error: false,
    }
    const final = msg('a2', 'assistant', 'It says: buy milk')
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      sseResponse([
        ev('user', user),
        ev('message', turn),
        ev('tool_call', call),
        ev('tool_result', { id: 'c1', name: 'fs__read', content: 'buy milk', is_error: false }),
        ev('message', toolRow),
        ev('token', { content: 'It says: ' }),
        ev('token', { content: 'buy milk' }),
        ev('done', final),
      ]),
    )
    const { qc, hook } = setup()

    await act(() => hook.result.current.send('read notes', { tools: false }))

    await waitFor(() => expect(hook.result.current.isStreaming).toBe(false))
    expect(qc.getQueryData<Message[]>(messagesKey(CHAT))).toEqual([user, turn, toolRow, final])
    expect(hook.result.current.toolResults).toEqual({
      c1: { id: 'c1', name: 'fs__read', content: 'buy milk', is_error: false },
    })
    const body = JSON.parse(String((fetchSpy.mock.calls[0]![1] as RequestInit).body))
    expect(body).toEqual({ content: 'read notes', model: null, tools: false })
  })

  it('tracks pending calls until a decision arrives and posts the user decision', async () => {
    const user = msg('u1', 'user', 'write it')
    const call = {
      id: 'w1',
      name: 'fs__write',
      server: 'fs',
      arguments: { path: 'x' },
      read_only: false,
      status: 'pending' as const,
    }
    const turn: Message = { ...msg('a1', 'assistant', ''), tool_calls: [call] }
    // The stream stays open after `tool_call`; decide() is called while it's parked.
    let release!: () => void
    const gate = new Promise<void>((r) => (release = r))
    const enc = new TextEncoder()
    const body = new ReadableStream<Uint8Array>({
      async start(controller) {
        controller.enqueue(enc.encode(ev('user', user) + ev('message', turn) + ev('tool_call', call)))
        await gate
        controller.enqueue(
          enc.encode(
            ev('tool_decision', { id: 'w1', approved: true, by: 'user' }) +
              ev('done', msg('a2', 'assistant', 'written')),
          ),
        )
        controller.close()
      },
    })
    const fetchSpy = vi
      .spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(new Response(body, { status: 200 }))
      .mockResolvedValueOnce(new Response(null, { status: 204 }))
    const { hook } = setup()

    // Not wrapped in act(): the stream parks, and act() would hold back state
    // updates until the promise settles.
    const sending = hook.result.current.send('write it')
    await waitFor(() => expect(hook.result.current.pendingCalls).toHaveProperty('w1'))

    await act(() => hook.result.current.decide('w1', true))
    expect(fetchSpy.mock.calls[1]![0]).toContain('/chats/c1/tool-calls/w1/decision')
    expect(JSON.parse(String((fetchSpy.mock.calls[1]![1] as RequestInit).body))).toEqual({
      approved: true,
      always: false,
    })

    await act(async () => {
      release()
      await sending
    })
    expect(hook.result.current.isStreaming).toBe(false)
    expect(hook.result.current.pendingCalls).toEqual({})
  })

  it('reports HTTP failures', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response('Chat not found', { status: 404 }),
    )
    const { hook } = setup()

    await act(() => hook.result.current.send('hi'))

    await waitFor(() => expect(hook.result.current.error).toBe('Chat not found'))
    expect(hook.result.current.isStreaming).toBe(false)
  })
})
