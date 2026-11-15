export type Role = 'user' | 'assistant' | 'tool'

export interface Chat {
  id: string
  title: string
  created_at: string
  updated_at: string
}

/** A tool invocation the model requested; stored on the assistant row and sent as SSE `tool_call`. */
export type ToolCallStatus = 'auto' | 'pending'

export interface ToolCall {
  id: string
  name: string
  server: string
  arguments: Record<string, unknown>
  read_only: boolean
  /** auto = ran without asking; pending = waiting for the user's decision */
  status?: ToolCallStatus
}

/** SSE `tool_decision`: how a pending call was resolved. */
export interface ToolDecision {
  id: string
  approved: boolean
  by: 'user' | 'timeout'
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
  /** null = ran without asking; true/false = the user's decision */
  tool_approved?: boolean | null
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
