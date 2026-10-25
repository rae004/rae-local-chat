import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { Markdown } from './Markdown'

describe('Markdown', () => {
  it('renders GFM with highlighted code blocks', () => {
    render(
      <Markdown>
        {'# Title\n\n- item\n\n```python\nprint("hi")\n```\n\n| a | b |\n|---|---|\n| 1 | 2 |'}
      </Markdown>,
    )
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Title')
    expect(screen.getByRole('listitem')).toHaveTextContent('item')
    expect(document.querySelector('code.hljs.language-python')).not.toBeNull()
    expect(screen.getByRole('table')).toBeInTheDocument()
  })

  it('does not render raw HTML', () => {
    render(<Markdown>{'<img src=x onerror=alert(1)> text'}</Markdown>)
    expect(document.querySelector('img')).toBeNull()
    expect(screen.getByText(/text/)).toBeInTheDocument()
  })
})
