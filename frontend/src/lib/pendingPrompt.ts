import type { StreamOptions } from '../api/client'

/**
 * Hands the first prompt from the "new chat" landing page to the chat route
 * without putting it in the URL. Set before navigating, consumed once on mount.
 */
export interface PendingPrompt extends StreamOptions {
  content: string
}

const pending = new Map<string, PendingPrompt>()

export const pendingPrompt = {
  set(chatId: string, prompt: PendingPrompt) {
    pending.set(chatId, prompt)
  },
  take(chatId: string): PendingPrompt | undefined {
    const v = pending.get(chatId)
    pending.delete(chatId)
    return v
  },
}
