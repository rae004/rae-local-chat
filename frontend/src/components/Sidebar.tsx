import { Link, useNavigate, useParams } from '@tanstack/react-router'
import { useState } from 'react'

import type { Chat } from '../api/types'
import { useChats, useDeleteChat, useRenameChat } from '../hooks/useChats'

export function Sidebar() {
  const chats = useChats()

  return (
    <aside className="flex h-full w-72 flex-col border-r border-base-300 bg-base-200">
      <div className="p-3">
        <Link to="/" className="btn btn-primary btn-block">
          + New chat
        </Link>
      </div>
      <ul className="menu flex-1 flex-nowrap overflow-y-auto">
        {chats.isPending ? (
          <li className="px-3 py-2 text-sm opacity-60">Loading…</li>
        ) : chats.isError ? (
          <li className="px-3 py-2 text-sm text-error">Couldn't load chats</li>
        ) : chats.data.length === 0 ? (
          <li className="px-3 py-2 text-sm opacity-60">No chats yet</li>
        ) : (
          chats.data.map((c) => <ChatRow key={c.id} chat={c} />)
        )}
      </ul>
      <div className="border-t border-base-300 p-3 text-xs opacity-60">Rae Bot</div>
    </aside>
  )
}

function ChatRow({ chat }: { chat: Chat }) {
  const navigate = useNavigate()
  const { chatId: activeId } = useParams({ strict: false })
  const rename = useRenameChat()
  const remove = useDeleteChat()
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState(chat.title)

  const commit = () => {
    setEditing(false)
    const title = draft.trim()
    if (title && title !== chat.title) rename.mutate({ chatId: chat.id, title })
    else setDraft(chat.title)
  }

  const onDelete = async () => {
    if (!window.confirm(`Delete "${chat.title}"?`)) return
    await remove.mutateAsync(chat.id)
    if (activeId === chat.id) void navigate({ to: '/' })
  }

  if (editing) {
    return (
      <li>
        <input
          className="input input-sm input-bordered w-full"
          aria-label="Chat title"
          value={draft}
          autoFocus
          onChange={(e) => setDraft(e.target.value)}
          onBlur={commit}
          onKeyDown={(e) => {
            if (e.key === 'Enter') commit()
            if (e.key === 'Escape') {
              setDraft(chat.title)
              setEditing(false)
            }
          }}
        />
      </li>
    )
  }

  return (
    <li className="group">
      <Link
        to="/chats/$chatId"
        params={{ chatId: chat.id }}
        className="flex items-center gap-2 pr-1"
        activeProps={{ className: 'menu-active' }}
        title="Double-click to rename"
        onDoubleClick={(e) => {
          e.preventDefault()
          setDraft(chat.title)
          setEditing(true)
        }}
      >
        <span className="flex-1 truncate">{chat.title}</span>
        <button
          type="button"
          aria-label={`Delete ${chat.title}`}
          className="btn btn-ghost btn-xs opacity-0 group-hover:opacity-100 focus:opacity-100"
          onClick={(e) => {
            e.preventDefault()
            e.stopPropagation()
            void onDelete()
          }}
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
            <path d="M3 6h18M8 6V4h8v2M6 6l1 14h10l1-14M10 11v6M14 11v6" />
          </svg>
        </button>
      </Link>
    </li>
  )
}
