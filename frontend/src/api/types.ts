export type Role = 'user' | 'assistant'

export interface Chat {
  id: string
  title: string
  created_at: string
  updated_at: string
}

export interface Message {
  id: string
  chat_id: string
  role: Role
  content: string
  model: string | null
  created_at: string
}
