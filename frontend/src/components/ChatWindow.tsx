import { useMessages } from '../hooks/useMessages'
import { useSendMessage } from '../hooks/useSendMessage'
import { MessageList } from './MessageList'
import { PromptBox } from './PromptBox'

interface Props {
  chatId: string
}

export function ChatWindow({ chatId }: Props) {
  const messages = useMessages(chatId)
  const send = useSendMessage(chatId)

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
        <MessageList messages={messages.data} />
      )}
      {send.isError ? (
        <div role="alert" className="alert alert-error mx-4">
          Send failed: {send.error.message}
        </div>
      ) : null}
      <PromptBox onSubmit={(c) => send.mutateAsync(c)} disabled={send.isPending} autoFocus />
    </div>
  )
}
