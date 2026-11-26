import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useCallback, useState } from 'react'

import { api } from '../api/client'

export const toolsKey = ['tools'] as const
export const allowRulesKey = ['tools', 'allow-rules'] as const
const KEY = 'tools'

/** Tool catalogue + per-server status from the API. */
export function useTools() {
  return useQuery({ queryKey: toolsKey, queryFn: api.listTools, staleTime: 60_000 })
}

/** Tools the user chose to run without asking. */
export function useAllowRules() {
  return useQuery({ queryKey: allowRulesKey, queryFn: api.listAllowRules, staleTime: 60_000 })
}

/** Revoke an allow rule; the tool asks again from its next call. */
export function useRevokeAllowRule() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: api.deleteAllowRule,
    onSuccess: () => qc.invalidateQueries({ queryKey: allowRulesKey }),
  })
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
