import { Link } from '@tanstack/react-router'

import { useChats } from '../hooks/useChats'

export function Sidebar() {
  const chats = useChats()

  return (
    <aside className="flex h-full w-72 flex-col border-r border-base-300 bg-base-200">
      <div className="p-3">
        <Link to="/" className="btn btn-primary btn-block">
          + New chat
        </Link>
      </div>
      <ul className="menu flex-1 overflow-y-auto">
        {chats.isPending ? (
          <li className="px-3 py-2 text-sm opacity-60">Loading…</li>
        ) : chats.isError ? (
          <li className="px-3 py-2 text-sm text-error">Couldn't load chats</li>
        ) : chats.data.length === 0 ? (
          <li className="px-3 py-2 text-sm opacity-60">No chats yet</li>
        ) : (
          chats.data.map((c) => (
            <li key={c.id}>
              <Link
                to="/chats/$chatId"
                params={{ chatId: c.id }}
                className="truncate"
                activeProps={{ className: 'menu-active' }}
              >
                {c.title}
              </Link>
            </li>
          ))
        )}
      </ul>
      <div className="border-t border-base-300 p-3 text-xs opacity-60">rae-local-chat</div>
    </aside>
  )
}
