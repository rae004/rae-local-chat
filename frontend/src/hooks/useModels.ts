import { useQuery } from '@tanstack/react-query'
import { useCallback, useState } from 'react'

import { api } from '../api/client'

export const modelsKey = ['models'] as const
const KEY = 'model'

export function useModels() {
  return useQuery({ queryKey: modelsKey, queryFn: api.listModels, staleTime: 5 * 60_000 })
}

/** Selected model name, persisted in localStorage. null = server default. */
export function useSelectedModel(): [string | null, (name: string | null) => void] {
  const [model, setModel] = useState<string | null>(() => {
    try {
      return localStorage.getItem(KEY)
    } catch {
      return null
    }
  })
  const select = useCallback((name: string | null) => {
    setModel(name)
    try {
      if (name) localStorage.setItem(KEY, name)
      else localStorage.removeItem(KEY)
    } catch {
      /* storage unavailable */
    }
  }, [])
  return [model, select]
}
