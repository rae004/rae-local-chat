import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { api } from '../api/client'

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
