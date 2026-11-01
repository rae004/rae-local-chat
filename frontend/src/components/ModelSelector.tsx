import { useModels } from '../hooks/useModels'

interface Props {
  value: string | null
  onChange: (name: string | null) => void
  disabled?: boolean
}

export function ModelSelector({ value, onChange, disabled }: Props) {
  const models = useModels()

  if (models.isError) {
    return (
      <span className="text-xs text-error" title={models.error.message}>
        Ollama unreachable
      </span>
    )
  }
  const list = models.data ?? []
  // A remembered model that's no longer installed falls back to the default.
  const current = value && list.some((m) => m.name === value) ? value : ''

  return (
    <select
      className="select select-sm select-bordered w-auto max-w-xs"
      aria-label="Model"
      value={current}
      disabled={disabled || models.isPending}
      onChange={(e) => onChange(e.target.value || null)}
    >
      <option value="">{models.isPending ? 'Loading models…' : 'Default model'}</option>
      {list.map((m) => (
        <option key={m.name} value={m.name}>
          {m.name}
          {m.parameter_size ? ` · ${m.parameter_size}` : ''}
          {m.tools ? '' : ' · no tools'}
        </option>
      ))}
    </select>
  )
}
