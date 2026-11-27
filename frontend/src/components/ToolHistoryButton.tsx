import { useToolCallHistory } from '../hooks/useToolCallHistory'

interface Props {
  chatId: string
  open: boolean
  onToggle: () => void
}

/** "History (N)" toggle for the tool call drawer; N = calls in this chat. */
export function ToolHistoryButton({ chatId, open, onToggle }: Props) {
  const history = useToolCallHistory(chatId)
  const count = history.data?.length
  return (
    <button
      type="button"
      className={`btn btn-ghost btn-sm ${open ? 'btn-active' : ''}`}
      aria-pressed={open}
      aria-label="Tool call history"
      title="Every tool call in this chat"
      onClick={onToggle}
    >
      <ClockIcon />
      Tools{count === undefined ? '' : ` (${count})`}
    </button>
  )
}

function ClockIcon() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      className="h-4 w-4"
      aria-hidden="true"
    >
      <circle cx="12" cy="12" r="9" />
      <path d="M12 7v5l3 2" />
    </svg>
  )
}
