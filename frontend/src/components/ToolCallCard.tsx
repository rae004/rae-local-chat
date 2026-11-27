import type { ToolCall, ToolResult } from '../api/types'

export type CardStatus = 'running' | 'done' | 'denied' | 'error' | 'pending' | 'stale'

interface Props {
  call: ToolCall
  result?: ToolResult | null
  /** null = auto-ran; true/false = the user's decision (from the persisted row). */
  approved?: boolean | null
  /** No result yet and the turn is still streaming. */
  running?: boolean
  /** Waiting for the user right now; shows Approve/Deny. */
  pending?: boolean
  /** `always` = approve and never ask for this tool again. */
  onDecide?: (approved: boolean, always?: boolean) => void
}

/** One tool invocation: who/what, arguments, Approve/Deny while pending, and the result. */
export function ToolCallCard({
  call,
  result = null,
  approved = null,
  running = false,
  pending = false,
  onDecide,
}: Props) {
  const status = cardStatus({ result, approved, running, pending })
  const [server, tool] = splitName(call)

  return (
    <details
      className={`collapse collapse-arrow my-1 border bg-base-200 text-sm ${
        status === 'error' ? 'border-error/60' : status === 'pending' ? 'border-warning/60' : 'border-base-300'
      }`}
      open={pending || undefined}
      data-testid="tool-call"
    >
      <summary className="collapse-title flex min-h-0 items-center gap-2 py-2 pr-10">
        <ToolIcon />
        <span className="font-mono">
          <span className="opacity-60">{server} · </span>
          {tool}
        </span>
        <StatusBadge status={status} readOnly={call.read_only} allowed={call.status === 'allowed'} />
      </summary>
      <div className="collapse-content space-y-2">
        <Block label="arguments">{JSON.stringify(call.arguments, null, 2)}</Block>
        {pending ? (
          <div className="flex items-center gap-2">
            <span className="text-xs opacity-70">This tool modifies state. Run it?</span>
            <button
              type="button"
              className="btn btn-success btn-xs"
              onClick={() => onDecide?.(true)}
            >
              Approve
            </button>
            <button type="button" className="btn btn-error btn-xs" onClick={() => onDecide?.(false)}>
              Deny
            </button>
            <button
              type="button"
              className="btn btn-ghost btn-xs"
              title="Run it now and never ask for this tool again (revoke under Tools ⚙)"
              onClick={() => onDecide?.(true, true)}
            >
              Always allow
            </button>
          </div>
        ) : null}
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

function cardStatus({
  result,
  approved,
  running,
  pending,
}: {
  result: ToolResult | null
  approved: boolean | null
  running: boolean
  pending: boolean
}): CardStatus {
  if (pending) return 'pending'
  if (result) {
    if (approved === false) return 'denied'
    return result.is_error ? 'error' : 'done'
  }
  return running ? 'running' : 'stale'
}

function StatusBadge({
  status,
  readOnly,
  allowed,
}: {
  status: CardStatus
  readOnly: boolean
  allowed: boolean
}) {
  switch (status) {
    case 'running':
      return <span className="loading loading-spinner loading-xs" aria-label="running" />
    case 'pending':
      return <span className="badge badge-warning badge-xs">needs approval</span>
    case 'denied':
      return <span className="badge badge-neutral badge-xs">denied</span>
    case 'error':
      return <span className="badge badge-error badge-xs">error</span>
    case 'stale':
      return <span className="badge badge-ghost badge-xs">no result</span>
    case 'done':
      return (
        <span className={`badge badge-xs ${readOnly || allowed ? 'badge-ghost' : 'badge-info'}`}>
          {readOnly ? 'auto · read-only' : allowed ? 'auto · allowed' : 'approved'}
        </span>
      )
  }
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
