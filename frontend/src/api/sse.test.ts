import { describe, expect, it } from 'vitest'

import { parseSSE } from './sse'

function streamOf(chunks: string[]): ReadableStream<Uint8Array> {
  const enc = new TextEncoder()
  return new ReadableStream({
    start(controller) {
      for (const c of chunks) controller.enqueue(enc.encode(c))
      controller.close()
    },
  })
}

async function collect(chunks: string[]) {
  const out = []
  for await (const ev of parseSSE(streamOf(chunks))) out.push(ev)
  return out
}

describe('parseSSE', () => {
  it('parses complete events', async () => {
    const evs = await collect(['event: token\ndata: {"content":"a"}\n\nevent: done\ndata: {}\n\n'])
    expect(evs).toEqual([
      { event: 'token', data: '{"content":"a"}' },
      { event: 'done', data: '{}' },
    ])
  })

  it('reassembles events split across chunks', async () => {
    const evs = await collect(['event: tok', 'en\ndata: {"c', 'ontent":"a"}\n', '\n'])
    expect(evs).toEqual([{ event: 'token', data: '{"content":"a"}' }])
  })

  it('joins multi-line data and defaults the event name', async () => {
    const evs = await collect(['data: one\ndata: two\n\n'])
    expect(evs).toEqual([{ event: 'message', data: 'one\ntwo' }])
  })

  it('flushes a trailing event without a terminator', async () => {
    const evs = await collect(['event: done\ndata: {}'])
    expect(evs).toEqual([{ event: 'done', data: '{}' }])
  })
})
