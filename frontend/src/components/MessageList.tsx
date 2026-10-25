import type { Message } from '../api/types'

interface Props {
  messages: Message[]
}

export function MessageList({ messages }: Props) {
  if (messages.length === 0) {
    return (
      <div className="flex flex-1 items-center justify-center text-base-content/60">
        No messages yet.
      </div>
    )
  }
  return (
    <div className="flex-1 space-y-2 overflow-y-auto p-4">
      {messages.map((m) => (
        <div key={m.id} className={`chat ${m.role === 'user' ? 'chat-end' : 'chat-start'}`}>
          <div className="chat-header text-xs opacity-60">
            {m.role}
            {m.model ? ` · ${m.model}` : null}
          </div>
          <div
            className={`chat-bubble whitespace-pre-wrap ${m.role === 'user' ? 'chat-bubble-primary' : ''}`}
          >
            {m.content}
          </div>
        </div>
      ))}
    </div>
  )
}
