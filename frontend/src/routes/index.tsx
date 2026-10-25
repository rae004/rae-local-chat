import { useQueryClient } from '@tanstack/react-query'
import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { useState } from 'react'

import { api } from '../api/client'
import { PromptBox } from '../components/PromptBox'
import { chatsKey } from '../hooks/useChats'
import { pendingPrompt } from '../lib/pendingPrompt'

export const Route = createFileRoute('/')({
  component: NewChat,
})

function NewChat() {
  const navigate = useNavigate()
  const qc = useQueryClient()
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  // Create the chat, stash the prompt, and let ChatWindow open the stream.
  const start = async (content: string) => {
    setBusy(true)
    setError(null)
    try {
      const chat = await api.createChat()
      pendingPrompt.set(chat.id, content)
      void qc.invalidateQueries({ queryKey: chatsKey })
      await navigate({ to: '/chats/$chatId', params: { chatId: chat.id } })
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
      setBusy(false)
    }
  }

  return (
    <div className="flex h-full flex-col">
      <div className="flex flex-1 flex-col items-center justify-center gap-2 p-8 text-center">
        <h1 className="text-3xl font-bold">rae-local-chat</h1>
        <p className="opacity-60">Start a conversation below.</p>
        {error ? (
          <div role="alert" className="alert alert-error mt-4">
            {error}
          </div>
        ) : null}
      </div>
      <PromptBox onSubmit={start} disabled={busy} autoFocus />
    </div>
  )
}
