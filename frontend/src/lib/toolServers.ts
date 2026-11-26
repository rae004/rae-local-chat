import { useCallback, useSyncExternalStore } from 'react'

import type { ToolsInfo } from '../api/types'

/**
 * Which MCP servers' tools are offered to the model. Stored as the *disabled*
 * set so a newly connected server is on by default. GitHub starts off: its 46
 * tools are most of the catalogue and small models pick worse the longer the
 * list gets.
 */
const KEY = 'toolServers.off'
const DEFAULT_OFF = ['github']

let off: ReadonlySet<string> = load()
const listeners = new Set<() => void>()

function load(): ReadonlySet<string> {
  try {
    const raw = localStorage.getItem(KEY)
    if (raw === null) return new Set(DEFAULT_OFF)
    const parsed: unknown = JSON.parse(raw)
    return new Set(Array.isArray(parsed) ? parsed.filter((x) => typeof x === 'string') : [])
  } catch {
    return new Set(DEFAULT_OFF)
  }
}

function save(next: ReadonlySet<string>) {
  off = next
  try {
    localStorage.setItem(KEY, JSON.stringify([...next]))
  } catch {
    /* storage unavailable */
  }
  for (const l of listeners) l()
}

export const toolServers = {
  isEnabled: (server: string) => !off.has(server),
  setEnabled(server: string, on: boolean) {
    const next = new Set(off)
    if (on) next.delete(server)
    else next.add(server)
    save(next)
  },
  /** Names of the connected servers that are switched on. */
  enabled: (info: ToolsInfo | undefined) =>
    Object.keys(info?.servers ?? {}).filter((s) => !off.has(s)),
  /** Tools the model would be offered, given the catalogue. */
  enabledTools: (info: ToolsInfo | undefined) =>
    (info?.tools ?? []).filter((t) => !off.has(t.server)),
  /** Test hook: forget stored choices. */
  reset() {
    try {
      localStorage.removeItem(KEY)
    } catch {
      /* ignore */
    }
    save(load())
  },
}

const subscribe = (l: () => void) => {
  listeners.add(l)
  return () => listeners.delete(l)
}

/** Reactive view of the disabled set; re-renders on any change, from any component. */
export function useToolServers() {
  const current = useSyncExternalStore(subscribe, () => off)
  const setEnabled = useCallback((server: string, on: boolean) => toolServers.setEnabled(server, on), [])
  return { off: current, isEnabled: (s: string) => !current.has(s), setEnabled }
}
