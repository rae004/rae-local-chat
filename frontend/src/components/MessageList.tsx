import { useEffect, useRef } from 'react'

import type { Message } from '../api/types'
import { Markdown } from './Markdown'

interface Props {
  messages: Message[]
  /** In-flight assistant text; rendered as a trailing bubble while streaming. */
  partial?: string
  isStreaming?: boolean
}

export function MessageList({ messages, partial = '', isStreaming = false }: Props) {
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
  return (
    <div className="flex-1 space-y-2 overflow-y-auto p-4">
      {messages.map((m) => (
        <Bubble key={m.id} role={m.role} header={m.model ? `${m.role} · ${m.model}` : m.role}>
          {m.role === 'assistant' ? <Markdown>{m.content}</Markdown> : m.content}
        </Bubble>
      ))}
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
