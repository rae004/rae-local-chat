import { beforeEach, describe, expect, it } from 'vitest'

import type { ToolsInfo } from '../api/types'
import { toolServers } from './toolServers'

const info: ToolsInfo = {
  servers: { filesystem: 'ok', github: 'ok', shell: 'ok' },
  tools: [
    { server: 'filesystem', name: 'read', qualified: 'filesystem__read', description: '', read_only: true },
    { server: 'github', name: 'prs', qualified: 'github__prs', description: '', read_only: true },
    { server: 'github', name: 'issue', qualified: 'github__issue', description: '', read_only: false },
    { server: 'shell', name: 'run', qualified: 'shell__run', description: '', read_only: false },
  ],
}

beforeEach(() => toolServers.reset())

describe('toolServers', () => {
  it('starts with everything on except github', () => {
    expect(toolServers.enabled(info)).toEqual(['filesystem', 'shell'])
    expect(toolServers.enabledTools(info).map((t) => t.qualified)).toEqual([
      'filesystem__read',
      'shell__run',
    ])
  })

  it('persists a change and survives a reload of the store', () => {
    toolServers.setEnabled('github', true)
    toolServers.setEnabled('shell', false)
    expect(toolServers.enabled(info)).toEqual(['filesystem', 'github'])
    expect(JSON.parse(localStorage.getItem('toolServers.off') ?? '[]')).toEqual(['shell'])
  })

  it('treats an unknown server as on, so new servers appear enabled', () => {
    expect(toolServers.isEnabled('memory')).toBe(true)
  })
})
