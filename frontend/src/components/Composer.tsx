import type { StreamOptions } from '../api/client'
import { useModels, useSelectedModel } from '../hooks/useModels'
import { useToolsEnabled } from '../hooks/useTools'
import { ModelSelector } from './ModelSelector'
import { PromptBox } from './PromptBox'
import { ToolsToggle } from './ToolsToggle'

interface Props {
  onSubmit: (content: string, options: StreamOptions) => void | Promise<unknown>
  disabled?: boolean
  onStop?: () => void
}

/** Model selector + tools toggle + prompt box (+ Stop while streaming). Shared by both routes. */
export function Composer({ onSubmit, disabled = false, onStop }: Props) {
  const [model, setModel] = useSelectedModel()
  const [toolsOn, setToolsOn] = useToolsEnabled()
  const models = useModels()

  // Unknown (default model, or list not loaded yet) counts as supported.
  const supportsTools = model ? (models.data?.find((m) => m.name === model)?.tools ?? true) : true
  const tools = toolsOn && supportsTools

  return (
    <div className="border-t border-base-300">
      <div className="flex items-center gap-3 px-4 pt-3">
        <ModelSelector value={model} onChange={setModel} />
        <ToolsToggle checked={toolsOn} onChange={setToolsOn} unsupported={!supportsTools} />
        {onStop ? (
          <button type="button" className="btn btn-outline btn-sm ml-auto" onClick={onStop}>
            Stop
          </button>
        ) : null}
      </div>
      <PromptBox onSubmit={(c) => onSubmit(c, { model, tools })} disabled={disabled} autoFocus />
    </div>
  )
}
