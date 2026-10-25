import type { Chat, Message } from './types'

export const API_URL: string = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export class ApiError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...init?.headers },
  })
  if (!res.ok) throw new ApiError(res.status, await res.text())
  return res.json() as Promise<T>
}

export const api = {
  listChats: () => request<Chat[]>('/chats'),
  createChat: (title?: string) =>
    request<Chat>('/chats', { method: 'POST', body: JSON.stringify(title ? { title } : {}) }),
  renameChat: (chatId: string, title: string) =>
    request<Chat>(`/chats/${chatId}`, { method: 'PATCH', body: JSON.stringify({ title }) }),
  deleteChat: async (chatId: string): Promise<void> => {
    const res = await fetch(`${API_URL}/chats/${chatId}`, { method: 'DELETE' })
    if (!res.ok) throw new ApiError(res.status, await res.text())
  },
  listMessages: (chatId: string) => request<Message[]>(`/chats/${chatId}/messages`),

  /** Opens the SSE stream; the caller consumes `res.body` with `parseSSE`. */
  streamMessage: async (
    chatId: string,
    content: string,
    signal: AbortSignal,
  ): Promise<ReadableStream<Uint8Array>> => {
    const res = await fetch(`${API_URL}/chats/${chatId}/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'text/event-stream' },
      body: JSON.stringify({ content }),
      signal,
    })
    if (!res.ok) throw new ApiError(res.status, await res.text())
    if (!res.body) throw new ApiError(res.status, 'Empty response body')
    return res.body
  },
}
