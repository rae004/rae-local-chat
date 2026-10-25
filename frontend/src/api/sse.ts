export interface SSEEvent {
  event: string
  data: string
}

/**
 * Minimal SSE parser over a byte stream. Handles events split across chunks
 * and multi-line `data:` fields. Yields one event per blank-line terminator.
 */
export async function* parseSSE(
  stream: ReadableStream<Uint8Array>,
  signal?: AbortSignal,
): AsyncGenerator<SSEEvent> {
  const reader = stream.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  const abort = () => void reader.cancel()
  signal?.addEventListener('abort', abort, { once: true })
  try {
    for (;;) {
      const { value, done } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      let idx: number
      while ((idx = buffer.indexOf('\n\n')) !== -1) {
        const block = buffer.slice(0, idx)
        buffer = buffer.slice(idx + 2)
        const ev = parseBlock(block)
        if (ev) yield ev
      }
    }
    const tail = parseBlock(buffer)
    if (tail) yield tail
  } finally {
    signal?.removeEventListener('abort', abort)
    reader.releaseLock()
  }
}

function parseBlock(block: string): SSEEvent | null {
  let event = 'message'
  const data: string[] = []
  for (const line of block.split('\n')) {
    if (line.startsWith('event:')) event = line.slice(6).trim()
    else if (line.startsWith('data:')) data.push(line.slice(5).trimStart())
  }
  return data.length ? { event, data: data.join('\n') } : null
}
