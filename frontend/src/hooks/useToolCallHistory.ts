import { useQuery } from '@tanstack/react-query'

import { api } from '../api/client'

export const toolCallsKey = (chatId: string) => ['tool-calls', chatId] as const

/** Every tool call in a chat with its outcome, newest first. Refetched when a turn ends. */
export function useToolCallHistory(chatId: string, enabled = true) {
  return useQuery({
    queryKey: toolCallsKey(chatId),
    queryFn: () => api.listToolCalls(chatId),
    enabled,
  })
}
