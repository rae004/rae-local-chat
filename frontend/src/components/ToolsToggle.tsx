import { useState } from 'react'

import { useTools } from '../hooks/useTools'
import { toolServers, useToolServers } from '../lib/toolServers'
import { ToolServersDialog } from './ToolServersDialog'

interface Props {
  checked: boolean
  onChange: (on: boolean) => void
  /** The selected model can't call tools; the toggle is shown off and disabled. */
  unsupported?: boolean
}

/** "Tools (N)" switch, N = tools from switched-on servers, plus a gear opening the server list. */
export function ToolsToggle({ checked, onChange, unsupported = false }: Props) {
  const tools = useTools()
  const { isEnabled } = useToolServers()
  const [open, setOpen] = useState(false)
  const count = toolServers.enabledTools(tools.data).length
  const servers = Object.entries(tools.data?.servers ?? {})
  const title = unsupported
    ? 'Selected model does not support tool calling'
    : servers.length
      ? servers
          .map(([name, status]) => `${name}: ${isEnabled(name) ? status : 'off'}`)
          .join('\n')
      : 'No MCP servers configured'

  return (
    <div className="flex items-center gap-1">
      <label className="label cursor-pointer gap-2 text-sm" title={title}>
        <input
          type="checkbox"
          className="toggle toggle-sm toggle-primary"
          aria-label="Tools"
          checked={checked && !unsupported}
          disabled={unsupported || count === 0}
          onChange={(e) => onChange(e.target.checked)}
        />
        <span className={unsupported || count === 0 ? 'opacity-50' : ''}>
          Tools{tools.data ? ` (${count})` : ''}
        </span>
      </label>
      <button
        type="button"
        className="btn btn-ghost btn-xs btn-circle"
        aria-label="Tool servers"
        title="Choose which MCP servers to offer"
        disabled={servers.length === 0}
        onClick={() => setOpen(true)}
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          className="h-4 w-4"
          aria-hidden="true"
        >
          <circle cx="12" cy="12" r="3" />
          <path d="M19.4 15a1.7 1.7 0 00.3 1.8l.1.1a2 2 0 11-2.8 2.8l-.1-.1a1.7 1.7 0 00-1.8-.3 1.7 1.7 0 00-1 1.5V21a2 2 0 11-4 0v-.1a1.7 1.7 0 00-1.1-1.5 1.7 1.7 0 00-1.8.3l-.1.1a2 2 0 11-2.8-2.8l.1-.1a1.7 1.7 0 00.3-1.8 1.7 1.7 0 00-1.5-1H3a2 2 0 110-4h.1a1.7 1.7 0 001.5-1.1 1.7 1.7 0 00-.3-1.8l-.1-.1a2 2 0 112.8-2.8l.1.1a1.7 1.7 0 001.8.3H9a1.7 1.7 0 001-1.5V3a2 2 0 114 0v.1a1.7 1.7 0 001 1.5 1.7 1.7 0 001.8-.3l.1-.1a2 2 0 112.8 2.8l-.1.1a1.7 1.7 0 00-.3 1.8V9a1.7 1.7 0 001.5 1H21a2 2 0 110 4h-.1a1.7 1.7 0 00-1.5 1z" />
        </svg>
      </button>
      <ToolServersDialog open={open} onClose={() => setOpen(false)} />
    </div>
  )
}
