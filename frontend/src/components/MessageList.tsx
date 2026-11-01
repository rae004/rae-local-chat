import { useEffect, useRef } from 'react'

import type { Message, ToolResult } from '../api/types'
import { Markdown } from './Markdown'
import { ToolCallCard } from './ToolCallCard'

interface Props {
  messages: Message[]
  /** In-flight assistant text; rendered as a trailing bubble while streaming. */
  partial?: string
  isStreaming?: boolean
  /** Tool results already streamed for this turn but not yet persisted. */
  toolResults?: Record<string, ToolResult>
}

export function MessageList({
  messages,
  partial = '',
  isStreaming = false,
  toolResults = {},
}: Props) {
  const bottomRef = useRef<HTMLDivElement>(null)
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ block: 'end' })
  }, [messages.length, partial])

  if (messages.length === 0 && !isStreaming) {
    return (
      <div className="flex flex-1 items-center justify-center text-base-content/60">
        No messages yet.
      </div>
    )
  }

  // Tool rows fold into the card of the call they answer.
  const results = new Map<string, ToolResult>(Object.entries(toolResults))
  for (const m of messages) {
    if (m.role === 'tool' && m.tool_call_id) {
      results.set(m.tool_call_id, {
        id: m.tool_call_id,
        name: m.tool_name ?? '',
        content: m.content,
        is_error: Boolean(m.tool_is_error),
      })
    }
  }

  return (
    <div className="flex-1 space-y-2 overflow-y-auto p-4">
      {messages.map((m) => {
        if (m.role === 'tool') return null
        const header = m.model ? `${m.role} · ${m.model}` : m.role
        return (
          <div key={m.id}>
            {m.content || !m.tool_calls?.length ? (
              <Bubble role={m.role} header={header}>
                {m.role === 'assistant' ? <Markdown>{m.content}</Markdown> : m.content}
              </Bubble>
            ) : null}
            {m.tool_calls?.length ? (
              <div className="ml-2 max-w-prose">
                {m.tool_calls.map((c) => (
                  <ToolCallCard
                    key={c.id}
                    call={c}
                    result={results.get(c.id) ?? null}
                    running={isStreaming}
                  />
                ))}
              </div>
            ) : null}
          </div>
        )
      })}
      {isStreaming ? (
        <Bubble role="assistant" header="assistant">
          <Markdown>{partial}</Markdown>
          <span className="loading loading-dots loading-xs ml-1 align-middle" />
        </Bubble>
      ) : null}
      <div ref={bottomRef} />
    </div>
  )
}

function Bubble({
  role,
  header,
  children,
}: {
  role: Message['role']
  header: string
  children: React.ReactNode
}) {
  const mine = role === 'user'
  return (
    <div className={`chat ${mine ? 'chat-end' : 'chat-start'}`}>
      <div className="chat-header text-xs opacity-60">{header}</div>
      <div className={`chat-bubble ${mine ? 'chat-bubble-primary whitespace-pre-wrap' : ''}`}>
        {children}
      </div>
    </div>
  )
}
