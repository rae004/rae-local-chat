import { useAllowRules, useRevokeAllowRule, useTools } from '../hooks/useTools'
import { useToolServers } from '../lib/toolServers'

interface Props {
  open: boolean
  onClose: () => void
}

/** Per-server on/off switches. Off = that server's tools aren't sent to the model. */
export function ToolServersDialog({ open, onClose }: Props) {
  const tools = useTools()
  const rules = useAllowRules()
  const revoke = useRevokeAllowRule()
  const { isEnabled, setEnabled } = useToolServers()
  const servers = Object.entries(tools.data?.servers ?? {})
  const counts = new Map<string, number>()
  for (const t of tools.data?.tools ?? []) counts.set(t.server, (counts.get(t.server) ?? 0) + 1)

  return (
    <dialog className={`modal ${open ? 'modal-open' : ''}`} aria-label="Tool settings" open={open}>
      <div className="modal-box max-w-md">
        <h3 className="text-lg font-bold">Tools</h3>
        <h4 className="mt-2 font-semibold">Servers</h4>
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
        <h4 className="mt-4 font-semibold">Always allowed</h4>
        <p className="py-2 text-sm opacity-70">
          These run without asking. Add one with <em>Always allow</em> on a tool card.
        </p>
        {!rules.data?.length ? (
          <p className="text-sm opacity-60">None. Every tool that modifies state asks first.</p>
        ) : (
          <ul className="divide-y divide-base-300">
            {rules.data.map((r) => (
              <li key={r.tool} className="flex items-center gap-3 py-2">
                <span className="flex-1 font-mono text-sm">{r.tool}</span>
                <button
                  type="button"
                  className="btn btn-outline btn-xs"
                  disabled={revoke.isPending}
                  onClick={() => revoke.mutate(r.tool)}
                >
                  Revoke
                </button>
              </li>
            ))}
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
