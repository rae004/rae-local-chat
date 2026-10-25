import { useQuery } from '@tanstack/react-query'

import { api } from '../api/client'

export const messagesKey = (chatId: string) => ['messages', chatId] as const

export function useMessages(chatId: string) {
  return useQuery({ queryKey: messagesKey(chatId), queryFn: () => api.listMessages(chatId) })
}
