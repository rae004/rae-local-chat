import type { ToolCall, ToolResult } from '../api/types'

export type ToolCallStatus = 'running' | 'done' | 'error' | 'pending'

interface Props {
  call: ToolCall
  result?: ToolResult | null
  /** No result yet and the turn is still streaming. */
  running?: boolean
}

/** One tool invocation: who/what, arguments, and the (collapsible) result. */
export function ToolCallCard({ call, result = null, running = false }: Props) {
  const status: ToolCallStatus = result ? (result.is_error ? 'error' : 'done') : running ? 'running' : 'pending'
  const [server, tool] = splitName(call)

  return (
    <details
      className={`collapse collapse-arrow my-1 border bg-base-200 text-sm ${
        status === 'error' ? 'border-error/60' : 'border-base-300'
      }`}
      data-testid="tool-call"
    >
      <summary className="collapse-title flex min-h-0 items-center gap-2 py-2 pr-10">
        <ToolIcon />
        <span className="font-mono">
          <span className="opacity-60">{server} · </span>
          {tool}
        </span>
        <StatusBadge status={status} readOnly={call.read_only} />
      </summary>
      <div className="collapse-content space-y-2">
        <Block label="arguments">{JSON.stringify(call.arguments, null, 2)}</Block>
        {result ? (
          <Block label={result.is_error ? 'error' : 'result'} error={result.is_error}>
            {result.content || '(empty)'}
          </Block>
        ) : null}
      </div>
    </details>
  )
}

function splitName(call: ToolCall): [string, string] {
  if (call.server && call.name.startsWith(`${call.server}__`)) {
    return [call.server, call.name.slice(call.server.length + 2)]
  }
  return [call.server || '?', call.name]
}

function StatusBadge({ status, readOnly }: { status: ToolCallStatus; readOnly: boolean }) {
  if (status === 'running') {
    return <span className="loading loading-spinner loading-xs" aria-label="running" />
  }
  if (status === 'error') return <span className="badge badge-error badge-xs">error</span>
  if (status === 'pending') return <span className="badge badge-warning badge-xs">pending</span>
  return (
    <span className={`badge badge-xs ${readOnly ? 'badge-ghost' : 'badge-info'}`}>
      {readOnly ? 'auto · read-only' : 'done'}
    </span>
  )
}

function Block({
  label,
  error = false,
  children,
}: {
  label: string
  error?: boolean
  children: string
}) {
  return (
    <div>
      <div className={`mb-1 text-xs uppercase opacity-60 ${error ? 'text-error' : ''}`}>
        {label}
      </div>
      <pre className="max-h-64 overflow-auto rounded bg-base-300 p-2 text-xs whitespace-pre-wrap">
        {children}
      </pre>
    </div>
  )
}

function ToolIcon() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      className="h-4 w-4 shrink-0 opacity-70"
      aria-hidden="true"
    >
      <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z" />
    </svg>
  )
}
