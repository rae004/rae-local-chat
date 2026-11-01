import { useEffect } from 'react'

import { useChatStream } from '../hooks/useChatStream'
import { useMessages } from '../hooks/useMessages'
import { pendingPrompt } from '../lib/pendingPrompt'
import { Composer } from './Composer'
import { MessageList } from './MessageList'

interface Props {
  chatId: string
}

export function ChatWindow({ chatId }: Props) {
  const messages = useMessages(chatId)
  const stream = useChatStream(chatId)

  // First prompt handed over from the "new chat" landing page. `send` only
  // changes identity with chatId, so this runs once per chat.
  const { send } = stream
  useEffect(() => {
    const first = pendingPrompt.take(chatId)
    if (first) void send(first.content, { model: first.model, tools: first.tools })
  }, [chatId, send])

  return (
    <div className="flex h-full flex-col">
      {messages.isPending ? (
        <div className="flex flex-1 items-center justify-center">
          <span className="loading loading-dots loading-lg" />
        </div>
      ) : messages.isError ? (
        <div role="alert" className="alert alert-error m-4">
          Failed to load messages: {messages.error.message}
        </div>
      ) : (
        <MessageList
          messages={messages.data}
          partial={stream.partial}
          isStreaming={stream.isStreaming}
          toolResults={stream.toolResults}
        />
      )}
      {stream.error ? (
        <div role="alert" className="alert alert-error mx-4">
          {stream.error}
        </div>
      ) : null}
      <Composer
        onSubmit={stream.send}
        disabled={stream.isStreaming}
        onStop={stream.isStreaming ? stream.stop : undefined}
      />
    </div>
  )
}
