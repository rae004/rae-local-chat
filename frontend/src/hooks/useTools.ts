import { useQuery } from '@tanstack/react-query'
import { useCallback, useState } from 'react'

import { api } from '../api/client'

export const toolsKey = ['tools'] as const
const KEY = 'tools'

/** Tool catalogue + per-server status from the API. */
export function useTools() {
  return useQuery({ queryKey: toolsKey, queryFn: api.listTools, staleTime: 60_000 })
}

/** Whether to offer tools to the model; persisted in localStorage, default on. */
export function useToolsEnabled(): [boolean, (on: boolean) => void] {
  const [enabled, setEnabled] = useState<boolean>(() => {
    try {
      return localStorage.getItem(KEY) !== 'off'
    } catch {
      return true
    }
  })
  const set = useCallback((on: boolean) => {
    setEnabled(on)
    try {
      localStorage.setItem(KEY, on ? 'on' : 'off')
    } catch {
      /* storage unavailable */
    }
  }, [])
  return [enabled, set]
}
