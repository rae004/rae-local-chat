import { useQueryClient } from '@tanstack/react-query'
import { useCallback, useEffect, useRef, useState } from 'react'

import { api, type StreamOptions } from '../api/client'
import { parseSSE } from '../api/sse'
import type { Message, ToolResult } from '../api/types'
import { chatsKey } from './useChats'
import { messagesKey } from './useMessages'

export interface ChatStream {
  send: (content: string, options?: Partial<StreamOptions>) => Promise<void>
  stop: () => void
  partial: string
  isStreaming: boolean
  error: string | null
  /** Results for this turn's tool calls, by call id, before their rows are persisted. */
  toolResults: Record<string, ToolResult>
}

const DEFAULTS: StreamOptions = { model: null, tools: true }

/**
 * Plain fetch + ReadableStream consumer for the SSE endpoint. TanStack Query
 * still owns persisted history: `user`, `message` and `done` events are spliced
 * into the `['messages', chatId]` cache via setQueryData; only the in-flight
 * assistant text and tool results live in local state.
 */
export function useChatStream(chatId: string): ChatStream {
  const qc = useQueryClient()
  const [partial, setPartial] = useState('')
  const [isStreaming, setIsStreaming] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [toolResults, setToolResults] = useState<Record<string, ToolResult>>({})
  const abortRef = useRef<AbortController | null>(null)

  const append = useCallback(
    (msg: Message) => {
      qc.setQueryData<Message[]>(messagesKey(chatId), (old = []) =>
        old.some((m) => m.id === msg.id) ? old : [...old, msg],
      )
    },
    [qc, chatId],
  )

  const stop = useCallback(() => {
    abortRef.current?.abort()
  }, [])

  // Abort any in-flight stream when the chat changes or the component unmounts.
  useEffect(() => stop, [chatId, stop])

  const send = useCallback(
    async (content: string, options: Partial<StreamOptions> = {}) => {
      abortRef.current?.abort()
      const ac = new AbortController()
      abortRef.current = ac
      setPartial('')
      setError(null)
      setToolResults({})
      setIsStreaming(true)
      let text = ''
      try {
        const body = await api.streamMessage(chatId, content, { ...DEFAULTS, ...options }, ac.signal)
        for await (const ev of parseSSE(body, ac.signal)) {
          switch (ev.event) {
            case 'user':
            case 'message':
              append(JSON.parse(ev.data) as Message)
              // A new persisted row means the in-flight prose (if any) was consumed.
              if (ev.event === 'message') {
                text = ''
                setPartial('')
              }
              break
            case 'token':
              text += (JSON.parse(ev.data) as { content: string }).content
              setPartial(text)
              break
            case 'tool_result': {
              const r = JSON.parse(ev.data) as ToolResult
              setToolResults((prev) => ({ ...prev, [r.id]: r }))
              break
            }
            case 'done':
              append(JSON.parse(ev.data) as Message)
              break
            case 'error':
              setError((JSON.parse(ev.data) as { detail: string }).detail)
              break
          }
        }
      } catch (e) {
        if (!ac.signal.aborted) setError(e instanceof Error ? e.message : String(e))
      } finally {
        if (abortRef.current === ac) {
          abortRef.current = null
          setIsStreaming(false)
          setPartial('')
          // The server persists whatever it had (partial on stop/error), so
          // refetch to pick that up and refresh sidebar ordering.
          void qc.invalidateQueries({ queryKey: messagesKey(chatId) })
          void qc.invalidateQueries({ queryKey: chatsKey })
        }
      }
    },
    [chatId, append, qc],
  )

  return { send, stop, partial, isStreaming, error, toolResults }
}
