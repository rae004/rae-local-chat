import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { api } from '../api/client'
import type { Chat } from '../api/types'
import { messagesKey } from './useMessages'

export const chatsKey = ['chats'] as const

export function useChats() {
  return useQuery({ queryKey: chatsKey, queryFn: api.listChats })
}

export function useCreateChat() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (title?: string) => api.createChat(title),
    onSuccess: () => qc.invalidateQueries({ queryKey: chatsKey }),
  })
}

export function useRenameChat() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ chatId, title }: { chatId: string; title: string }) =>
      api.renameChat(chatId, title),
    onSuccess: (updated) => {
      qc.setQueryData<Chat[]>(chatsKey, (old = []) =>
        old.map((c) => (c.id === updated.id ? updated : c)),
      )
    },
  })
}

export function useDeleteChat() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (chatId: string) => api.deleteChat(chatId),
    onSuccess: (_, chatId) => {
      qc.setQueryData<Chat[]>(chatsKey, (old = []) => old.filter((c) => c.id !== chatId))
      qc.removeQueries({ queryKey: messagesKey(chatId) })
    },
  })
}
