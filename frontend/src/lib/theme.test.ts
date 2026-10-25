import { beforeEach, describe, expect, it } from 'vitest'

import { DARK, LIGHT, applyTheme, getInitialTheme } from './theme'

describe('theme', () => {
  beforeEach(() => {
    localStorage.clear()
    delete document.documentElement.dataset.theme
  })

  it('falls back to the OS preference when nothing is saved', () => {
    expect([LIGHT, DARK]).toContain(getInitialTheme())
  })

  it('applies to <html data-theme> and persists', () => {
    applyTheme(DARK)
    expect(document.documentElement.dataset.theme).toBe('dracula')
    expect(getInitialTheme()).toBe(DARK)
    applyTheme(LIGHT)
    expect(getInitialTheme()).toBe('cyberpunk')
  })

  it('ignores garbage in storage', () => {
    localStorage.setItem('theme', 'solarized')
    expect([LIGHT, DARK]).toContain(getInitialTheme())
  })
})
