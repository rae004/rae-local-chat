import { useSelectedModel } from '../hooks/useModels'
import { ModelSelector } from './ModelSelector'
import { PromptBox } from './PromptBox'

interface Props {
  onSubmit: (content: string, model: string | null) => void | Promise<unknown>
  disabled?: boolean
  onStop?: () => void
}

/** Model selector + prompt box (+ Stop while streaming). Shared by both routes. */
export function Composer({ onSubmit, disabled = false, onStop }: Props) {
  const [model, setModel] = useSelectedModel()

  return (
    <div className="border-t border-base-300">
      <div className="flex items-center gap-2 px-4 pt-3">
        <ModelSelector value={model} onChange={setModel} />
        {onStop ? (
          <button type="button" className="btn btn-outline btn-sm ml-auto" onClick={onStop}>
            Stop
          </button>
        ) : null}
      </div>
      <PromptBox onSubmit={(c) => onSubmit(c, model)} disabled={disabled} autoFocus />
    </div>
  )
}
