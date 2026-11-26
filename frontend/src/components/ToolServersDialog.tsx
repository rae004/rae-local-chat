import { useTools } from '../hooks/useTools'
import { useToolServers } from '../lib/toolServers'

interface Props {
  open: boolean
  onClose: () => void
}

/** Per-server on/off switches. Off = that server's tools aren't sent to the model. */
export function ToolServersDialog({ open, onClose }: Props) {
  const tools = useTools()
  const { isEnabled, setEnabled } = useToolServers()
  const servers = Object.entries(tools.data?.servers ?? {})
  const counts = new Map<string, number>()
  for (const t of tools.data?.tools ?? []) counts.set(t.server, (counts.get(t.server) ?? 0) + 1)

  return (
    <dialog className={`modal ${open ? 'modal-open' : ''}`} aria-label="Tool servers" open={open}>
      <div className="modal-box max-w-md">
        <h3 className="text-lg font-bold">Tool servers</h3>
        <p className="py-2 text-sm opacity-70">
          Switched-off servers are left out of the prompt entirely. Fewer tools, better picks.
        </p>
        {servers.length === 0 ? (
          <p className="text-sm opacity-60">No MCP servers configured.</p>
        ) : (
          <ul className="divide-y divide-base-300">
            {servers.map(([name, status]) => {
              const ok = status === 'ok'
              return (
                <li key={name} className="flex items-center gap-3 py-2">
                  <input
                    type="checkbox"
                    className="toggle toggle-sm toggle-primary"
                    aria-label={`Enable ${name}`}
                    checked={isEnabled(name)}
                    onChange={(e) => setEnabled(name, e.target.checked)}
                  />
                  <span className="flex-1 font-mono text-sm">{name}</span>
                  <span className="text-xs opacity-60">{counts.get(name) ?? 0} tools</span>
                  <span
                    className={`badge badge-xs ${ok ? 'badge-success' : 'badge-error'}`}
                    title={status}
                    aria-label={ok ? `${name} connected` : `${name} ${status}`}
                  />
                </li>
              )
            })}
          </ul>
        )}
        <div className="modal-action">
          <button type="button" className="btn btn-sm" onClick={onClose}>
            Done
          </button>
        </div>
      </div>
      <button type="button" className="modal-backdrop" aria-label="Close" onClick={onClose} />
    </dialog>
  )
}
