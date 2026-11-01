import { useTools } from '../hooks/useTools'

interface Props {
  checked: boolean
  onChange: (on: boolean) => void
  /** The selected model can't call tools; the toggle is shown off and disabled. */
  unsupported?: boolean
}

/** "Tools" switch with a tooltip listing the connected MCP servers. */
export function ToolsToggle({ checked, onChange, unsupported = false }: Props) {
  const tools = useTools()
  const count = tools.data?.tools.length ?? 0
  const servers = Object.entries(tools.data?.servers ?? {})
  const title = unsupported
    ? 'Selected model does not support tool calling'
    : servers.length
      ? servers.map(([name, status]) => `${name}: ${status}`).join('\n')
      : 'No MCP servers configured'

  return (
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
  )
}
