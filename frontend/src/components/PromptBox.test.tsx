import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { PromptBox } from './PromptBox'

describe('PromptBox', () => {
  it('submits trimmed content on Enter and clears', async () => {
    const onSubmit = vi.fn()
    render(<PromptBox onSubmit={onSubmit} />)
    const box = screen.getByLabelText('Prompt')
    await userEvent.type(box, '  hello  {Enter}')
    expect(onSubmit).toHaveBeenCalledWith('hello')
    expect(box).toHaveValue('')
  })

  it('inserts a newline on Shift+Enter without submitting', async () => {
    const onSubmit = vi.fn()
    render(<PromptBox onSubmit={onSubmit} />)
    const box = screen.getByLabelText('Prompt')
    await userEvent.type(box, 'a{Shift>}{Enter}{/Shift}b')
    expect(onSubmit).not.toHaveBeenCalled()
    expect(box).toHaveValue('a\nb')
  })

  it('does not submit empty input', async () => {
    const onSubmit = vi.fn()
    render(<PromptBox onSubmit={onSubmit} />)
    await userEvent.type(screen.getByLabelText('Prompt'), '   {Enter}')
    expect(onSubmit).not.toHaveBeenCalled()
    expect(screen.getByRole('button', { name: 'Send' })).toBeDisabled()
  })
})
