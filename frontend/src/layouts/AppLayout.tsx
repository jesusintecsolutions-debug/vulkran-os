import { Outlet, NavLink, useLocation } from 'react-router-dom'
import { useAuthStore } from '@/stores/auth'
import {
  LayoutDashboard,
  Users,
  FileText,
  Target,
  Receipt,
  Newspaper,
  MessageSquare,
  FolderOpen,
  Settings,
  LogOut,
  Bell,
} from 'lucide-react'
import { cn } from '@/lib/utils'

interface NavItem {
  to: string
  label: string
  icon: React.ElementType
  roles: string[]
}

const NAV_ITEMS: NavItem[] = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard, roles: ['admin', 'partner', 'client'] },
  { to: '/clients', label: 'Clientes', icon: Users, roles: ['admin'] },
  { to: '/content', label: 'Contenido', icon: FileText, roles: ['admin', 'client'] },
  { to: '/leads', label: 'Leads', icon: Target, roles: ['admin'] },
  { to: '/accounting', label: 'Contabilidad', icon: Receipt, roles: ['admin'] },
  { to: '/briefing', label: 'Briefing', icon: Newspaper, roles: ['admin'] },
  { to: '/files', label: 'Archivos', icon: FolderOpen, roles: ['admin', 'client'] },
  { to: '/chat', label: 'Agente AI', icon: MessageSquare, roles: ['admin'] },
  { to: '/settings', label: 'Ajustes', icon: Settings, roles: ['admin', 'partner', 'client'] },
]

export default function AppLayout() {
  const { user, logout } = useAuthStore()
  const location = useLocation()
  const role = user?.role || 'client'

  const visibleItems = NAV_ITEMS.filter((item) => item.roles.includes(role))

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Sidebar */}
      <aside className="flex w-60 flex-col border-r bg-sidebar">
        {/* Logo */}
        <div className="flex h-14 items-center border-b px-4">
          <span className="text-lg font-bold tracking-tight text-vulkran">VULKRAN</span>
          <span className="ml-1 text-xs font-medium text-muted-foreground">OS</span>
        </div>

        {/* Navigation */}
        <nav className="flex-1 overflow-y-auto px-2 py-3">
          <ul className="space-y-0.5">
            {visibleItems.map((item) => (
              <li key={item.to}>
                <NavLink
                  to={item.to}
                  end={item.to === '/'}
                  className={({ isActive }) =>
                    cn(
                      'flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors',
                      isActive
                        ? 'bg-accent text-accent-foreground'
                        : 'text-muted-foreground hover:bg-accent/50 hover:text-foreground',
                    )
                  }
                >
                  <item.icon className="h-4 w-4" />
                  {item.label}
                </NavLink>
              </li>
            ))}
          </ul>
        </nav>

        {/* User footer */}
        <div className="border-t p-3">
          <div className="flex items-center gap-3">
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-vulkran text-xs font-bold text-white">
              {user?.name?.charAt(0).toUpperCase() || '?'}
            </div>
            <div className="flex-1 truncate">
              <p className="truncate text-sm font-medium">{user?.name}</p>
              <p className="truncate text-xs text-muted-foreground">{user?.role}</p>
            </div>
            <button
              onClick={logout}
              className="rounded p-1 text-muted-foreground hover:bg-accent hover:text-foreground"
              title="Cerrar sesión"
            >
              <LogOut className="h-4 w-4" />
            </button>
          </div>
        </div>
      </aside>

      {/* Main content */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Top bar */}
        <header className="flex h-14 items-center justify-between border-b px-6">
          <h2 className="text-lg font-semibold">
            {visibleItems.find((i) => {
              if (i.to === '/') return location.pathname === '/'
              return location.pathname.startsWith(i.to)
            })?.label || 'VULKRAN OS'}
          </h2>
          <div className="flex items-center gap-3">
            <button className="relative rounded-md p-2 text-muted-foreground hover:bg-accent">
              <Bell className="h-5 w-5" />
            </button>
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-y-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
