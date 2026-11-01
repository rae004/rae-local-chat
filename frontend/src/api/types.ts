export type Role = 'user' | 'assistant' | 'tool'

export interface Chat {
  id: string
  title: string
  created_at: string
  updated_at: string
}

/** A tool invocation the model requested; stored on the assistant row and sent as SSE `tool_call`. */
export interface ToolCall {
  id: string
  name: string
  server: string
  arguments: Record<string, unknown>
  read_only: boolean
}

/** SSE `tool_result`: what the tool returned for `id`. */
export interface ToolResult {
  id: string
  name: string
  content: string
  is_error: boolean
}

export interface Message {
  id: string
  chat_id: string
  role: Role
  content: string
  model: string | null
  created_at: string
  /** assistant rows that requested tools */
  tool_calls?: ToolCall[] | null
  /** tool rows */
  tool_call_id?: string | null
  tool_name?: string | null
  tool_is_error?: boolean | null
}

export interface ModelInfo {
  name: string
  size: number
  parameter_size: string | null
  family: string | null
  tools: boolean
}

export interface ToolInfo {
  server: string
  name: string
  qualified: string
  description: string
  read_only: boolean
}

export interface ToolsInfo {
  /** server name -> "ok" | "error: …" */
  servers: Record<string, string>
  tools: ToolInfo[]
}
