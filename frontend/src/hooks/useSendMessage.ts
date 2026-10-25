import { useMutation, useQueryClient } from '@tanstack/react-query'

import { api } from '../api/client'
import type { Message } from '../api/types'
import { chatsKey } from './useChats'
import { messagesKey } from './useMessages'

/**
 * Milestone A: non-streaming send. The server returns the persisted user +
 * assistant pair and we splice both into the cached history. Milestone B's
 * `useChatStream` reuses this exact `setQueryData` shape on its `done` event.
 */
export function useSendMessage(chatId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (content: string) => api.sendMessage(chatId, content),
    onSuccess: ({ user, assistant }) => {
      qc.setQueryData<Message[]>(messagesKey(chatId), (old = []) => [...old, user, assistant])
      void qc.invalidateQueries({ queryKey: chatsKey })
    },
  })
}
