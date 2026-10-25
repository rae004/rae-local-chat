export type Theme = 'cyberpunk' | 'dracula'

export const LIGHT: Theme = 'cyberpunk'
export const DARK: Theme = 'dracula'
const KEY = 'theme'

export function getInitialTheme(): Theme {
  try {
    const saved = localStorage.getItem(KEY)
    if (saved === LIGHT || saved === DARK) return saved
  } catch {
    /* storage unavailable */
  }
  return window.matchMedia?.('(prefers-color-scheme: dark)').matches ? DARK : LIGHT
}

export function applyTheme(theme: Theme) {
  document.documentElement.dataset.theme = theme
  try {
    localStorage.setItem(KEY, theme)
  } catch {
    /* storage unavailable */
  }
}
