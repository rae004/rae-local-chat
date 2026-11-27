import { useEffect, useState } from 'react'

import { useChatStream } from '../hooks/useChatStream'
import { useMessages } from '../hooks/useMessages'
import { pendingPrompt } from '../lib/pendingPrompt'
import { Composer } from './Composer'
import { MessageList } from './MessageList'
import { ToolHistoryButton } from './ToolHistoryButton'
import { ToolHistoryDrawer } from './ToolHistoryDrawer'

interface Props {
  chatId: string
}

export function ChatWindow({ chatId }: Props) {
  const messages = useMessages(chatId)
  const stream = useChatStream(chatId)
  const [historyOpen, setHistoryOpen] = useState(false)

  // First prompt handed over from the "new chat" landing page. `send` only
  // changes identity with chatId, so this runs once per chat.
  const { send } = stream
  useEffect(() => {
    const first = pendingPrompt.take(chatId)
    if (first) {
      const { content, ...options } = first
      void send(content, options)
    }
  }, [chatId, send])

  return (
    <div className="flex h-full flex-col">
      <div className="flex min-h-0 flex-1">
        <div className="flex min-w-0 flex-1 flex-col">
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
              pendingCalls={stream.pendingCalls}
              onDecide={(id, ok, always) => void stream.decide(id, ok, always)}
            />
          )}
          {stream.error ? (
            <div role="alert" className="alert alert-error mx-4">
              {stream.error}
            </div>
          ) : null}
        </div>
        {historyOpen ? (
          <ToolHistoryDrawer chatId={chatId} onClose={() => setHistoryOpen(false)} />
        ) : null}
      </div>
      <Composer
        onSubmit={stream.send}
        disabled={stream.isStreaming}
        onStop={stream.isStreaming ? stream.stop : undefined}
        extras={
          <ToolHistoryButton
            chatId={chatId}
            open={historyOpen}
            onToggle={() => setHistoryOpen((o) => !o)}
          />
        }
      />
    </div>
  )
}
