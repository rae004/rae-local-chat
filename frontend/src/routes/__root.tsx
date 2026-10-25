import { Outlet, createRootRoute } from '@tanstack/react-router'

import { Sidebar } from '../components/Sidebar'

export const Route = createRootRoute({
  component: RootLayout,
})

function RootLayout() {
  return (
    <div className="flex h-screen bg-base-100 text-base-content">
      <Sidebar />
      <main className="flex min-w-0 flex-1 flex-col">
        <Outlet />
      </main>
    </div>
  )
}
