import { useState, type FormEvent, type KeyboardEvent } from 'react'

interface Props {
  onSubmit: (content: string) => void | Promise<unknown>
  disabled?: boolean
  autoFocus?: boolean
}

export function PromptBox({ onSubmit, disabled = false, autoFocus = false }: Props) {
  const [value, setValue] = useState('')

  const submit = () => {
    const content = value.trim()
    if (!content || disabled) return
    setValue('')
    void onSubmit(content)
  }

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    submit()
  }

  // Enter sends, Shift+Enter inserts a newline.
  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      submit()
    }
  }

  return (
    <form onSubmit={handleSubmit} className="flex items-end gap-2 p-4">
      <textarea
        className="textarea textarea-bordered flex-1 resize-none"
        rows={2}
        placeholder="Send a message…"
        aria-label="Prompt"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={handleKeyDown}
        disabled={disabled}
        autoFocus={autoFocus}
      />
      <button type="submit" className="btn btn-primary" disabled={disabled || !value.trim()}>
        Send
      </button>
    </form>
  )
}
