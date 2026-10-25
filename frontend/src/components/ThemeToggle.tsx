import { useEffect, useState } from 'react'

import { DARK, LIGHT, applyTheme, getInitialTheme, type Theme } from '../lib/theme'

export function ThemeToggle() {
  const [theme, setTheme] = useState<Theme>(getInitialTheme)
  useEffect(() => applyTheme(theme), [theme])
  const dark = theme === DARK

  return (
    <label className="swap swap-rotate btn btn-ghost btn-sm btn-circle" title="Toggle theme">
      <input
        type="checkbox"
        aria-label="Dark theme"
        checked={dark}
        onChange={(e) => setTheme(e.target.checked ? DARK : LIGHT)}
      />
      {/* sun (shown when dark is on → click for light) */}
      <svg className="swap-on h-5 w-5 fill-current" viewBox="0 0 24 24" aria-hidden="true">
        <path d="M5.64 17l-.71.71a1 1 0 001.41 1.41l.71-.71A1 1 0 005.64 17zM5 12a1 1 0 00-1-1H3a1 1 0 000 2h1a1 1 0 001-1zm7-7a1 1 0 001-1V3a1 1 0 00-2 0v1a1 1 0 001 1zM5.64 7.05a1 1 0 001.41-1.41l-.71-.71a1 1 0 00-1.41 1.41zm12 .29a1 1 0 00.7-.3l.71-.71a1 1 0 10-1.41-1.41l-.71.71a1 1 0 00.71 1.71zM21 11h-1a1 1 0 000 2h1a1 1 0 000-2zm-9 8a1 1 0 00-1 1v1a1 1 0 002 0v-1a1 1 0 00-1-1zm6.36-2a1 1 0 00-1.41 1.41l.71.71a1 1 0 001.41-1.41zM12 6.5a5.5 5.5 0 105.5 5.5A5.51 5.51 0 0012 6.5z" />
      </svg>
      {/* moon */}
      <svg className="swap-off h-5 w-5 fill-current" viewBox="0 0 24 24" aria-hidden="true">
        <path d="M21.64 13a1 1 0 00-1.05-.14 8.05 8.05 0 01-3.37.73 8.15 8.15 0 01-8.14-8.1 8.59 8.59 0 01.25-2A1 1 0 008 2.36a10.14 10.14 0 1014 11.69 1 1 0 00-.36-1.05z" />
      </svg>
    </label>
  )
}
