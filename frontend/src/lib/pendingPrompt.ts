/**
 * Hands the first prompt from the "new chat" landing page to the chat route
 * without putting it in the URL. Set before navigating, consumed once on mount.
 */
const pending = new Map<string, string>()

export const pendingPrompt = {
  set(chatId: string, content: string) {
    pending.set(chatId, content)
  },
  take(chatId: string): string | undefined {
    const v = pending.get(chatId)
    pending.delete(chatId)
    return v
  },
}
