import { createFileRoute } from '@tanstack/react-router'

import { ChatWindow } from '../components/ChatWindow'

export const Route = createFileRoute('/chats/$chatId')({
  component: ChatPage,
})

function ChatPage() {
  const { chatId } = Route.useParams()
  return <ChatWindow chatId={chatId} />
}
