import { Outlet, NavLink, useLocation } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
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
  Sparkles,
  type LucideIcon,
} from 'lucide-react'
import { cn } from '@/lib/utils'

interface NavItem {
  to: string
  label: string
  icon: LucideIcon
  roles: string[]
  accent?: boolean
}

const NAV_ITEMS: NavItem[] = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard, roles: ['admin', 'partner', 'client'] },
  { to: '/clients', label: 'Clientes', icon: Users, roles: ['admin'] },
  { to: '/content', label: 'Contenido', icon: FileText, roles: ['admin', 'client'] },
  { to: '/leads', label: 'Leads', icon: Target, roles: ['admin'] },
  { to: '/accounting', label: 'Contabilidad', icon: Receipt, roles: ['admin'] },
  { to: '/briefing', label: 'Briefing', icon: Newspaper, roles: ['admin'] },
  { to: '/files', label: 'Archivos', icon: FolderOpen, roles: ['admin', 'client'] },
  { to: '/chat', label: 'Agente AI', icon: MessageSquare, roles: ['admin'], accent: true },
  { to: '/settings', label: 'Ajustes', icon: Settings, roles: ['admin', 'partner', 'client'] },
]

export default function AppLayout() {
  const { user, logout } = useAuthStore()
  const location = useLocation()
  const role = user?.role || 'client'

  const visibleItems = NAV_ITEMS.filter((item) => item.roles.includes(role))
  const currentPage = visibleItems.find((i) => {
    if (i.to === '/') return location.pathname === '/'
    return location.pathname.startsWith(i.to)
  })

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      {/* Sidebar */}
      <aside className="flex w-60 flex-col border-r border-sidebar-border bg-sidebar relative">
        {/* Ambient glow */}
        <div className="pointer-events-none absolute -right-20 top-1/4 h-40 w-40 rounded-full bg-vulkran/5 blur-3xl" />

        {/* Logo */}
        <div className="flex h-14 items-center border-b border-sidebar-border px-4 gap-2">
          <Sparkles className="h-5 w-5 text-vulkran" />
          <span className="text-lg font-bold tracking-wider text-vulkran text-glow">VULKRAN</span>
          <span className="text-[10px] font-semibold text-vulkran-light/50 tracking-widest mt-0.5">OS</span>
        </div>

        {/* Navigation */}
        <nav className="flex-1 overflow-y-auto px-2 py-3">
          <ul className="space-y-0.5">
            {visibleItems.map((item) => {
              const isActive =
                item.to === '/' ? location.pathname === '/' : location.pathname.startsWith(item.to)
              return (
                <li key={item.to}>
                  <NavLink
                    to={item.to}
                    end={item.to === '/'}
                    className={cn(
                      'relative flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all duration-200',
                      isActive
                        ? 'text-foreground bg-sidebar-active'
                        : 'text-sidebar-foreground hover:text-foreground hover:bg-sidebar-active/50',
                      item.accent && !isActive && 'text-vulkran-light',
                    )}
                  >
                    {/* Active indicator */}
                    {isActive && (
                      <motion.div
                        layoutId="nav-active"
                        className="absolute left-0 top-1/2 -translate-y-1/2 h-5 w-[3px] rounded-r-full bg-vulkran"
                        transition={{ type: 'spring', stiffness: 400, damping: 30 }}
                      />
                    )}
                    {(() => {
                      const Icon = item.icon
                      return <Icon className={`h-4 w-4 ${isActive || item.accent ? 'text-vulkran-light' : ''}`} />
                    })()}
                    {item.label}
                    {item.accent && (
                      <span className="ml-auto h-2 w-2 rounded-full bg-vulkran animate-pulse" />
                    )}
                  </NavLink>
                </li>
              )
            })}
          </ul>
        </nav>

        {/* User footer */}
        <div className="border-t border-sidebar-border p-3">
          <div className="flex items-center gap-3">
            <div className="flex h-8 w-8 items-center justify-center rounded-full gradient-vulkran text-xs font-bold text-white shadow-lg shadow-vulkran/20">
              {user?.name?.charAt(0).toUpperCase() || '?'}
            </div>
            <div className="flex-1 truncate">
              <p className="truncate text-sm font-medium text-foreground">{user?.name}</p>
              <p className="truncate text-xs text-muted-foreground capitalize">{user?.role}</p>
            </div>
            <button
              onClick={logout}
              className="rounded-lg p-1.5 text-muted-foreground hover:text-error hover:bg-error/10 transition-all"
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
        <header className="flex h-14 items-center justify-between border-b border-border px-6 bg-surface-0/50 backdrop-blur-sm">
          <h2 className="text-lg font-semibold text-foreground">
            {currentPage?.label || 'VULKRAN OS'}
          </h2>
          <div className="flex items-center gap-3">
            <button className="relative rounded-lg p-2 text-muted-foreground hover:text-foreground hover:bg-surface-2 transition-all">
              <Bell className="h-5 w-5" />
              <span className="absolute top-1.5 right-1.5 h-2 w-2 rounded-full bg-vulkran animate-pulse" />
            </button>
          </div>
        </header>

        {/* Page content with animation */}
        <main className="flex-1 overflow-y-auto p-6">
          <AnimatePresence mode="wait">
            <motion.div
              key={location.pathname}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.2 }}
            >
              <Outlet />
            </motion.div>
          </AnimatePresence>
        </main>
      </div>
    </div>
  )
}
