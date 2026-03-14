import { useState } from 'react'
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
  Menu,
  X,
  type LucideIcon,
} from 'lucide-react'
import { cn } from '@/lib/utils'

interface NavItem {
  to: string
  label: string
  icon: LucideIcon
  roles: string[]
  accent?: boolean
  mobileNav?: boolean // show in mobile bottom nav
}

const NAV_ITEMS: NavItem[] = [
  { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard, roles: ['admin', 'partner', 'client'], mobileNav: true },
  { to: '/clients', label: 'Clientes', icon: Users, roles: ['admin'] },
  { to: '/content', label: 'Contenido', icon: FileText, roles: ['admin', 'client'], mobileNav: true },
  { to: '/leads', label: 'Leads', icon: Target, roles: ['admin'], mobileNav: true },
  { to: '/accounting', label: 'Contabilidad', icon: Receipt, roles: ['admin'] },
  { to: '/briefing', label: 'Briefing', icon: Newspaper, roles: ['admin'] },
  { to: '/files', label: 'Archivos', icon: FolderOpen, roles: ['admin', 'client'] },
  { to: '/chat', label: 'AI', icon: MessageSquare, roles: ['admin'], accent: true, mobileNav: true },
  { to: '/settings', label: 'Ajustes', icon: Settings, roles: ['admin', 'partner', 'client'], mobileNav: true },
]

export default function AppLayout() {
  const { user, logout } = useAuthStore()
  const location = useLocation()
  const role = user?.role || 'client'
  const [sidebarOpen, setSidebarOpen] = useState(false)

  const visibleItems = NAV_ITEMS.filter((item) => item.roles.includes(role))
  const mobileItems = visibleItems.filter((item) => item.mobileNav)
  const currentPage = visibleItems.find((i) => location.pathname.startsWith(i.to))

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      {/* Mobile overlay */}
      <AnimatePresence>
        {sidebarOpen && (
          <motion.div
            className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm md:hidden"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setSidebarOpen(false)}
          />
        )}
      </AnimatePresence>

      {/* Sidebar — hidden on mobile, collapsible on tablet */}
      <aside
        className={cn(
          'fixed md:static md:relative z-50 flex w-60 flex-col border-r border-sidebar-border bg-sidebar h-full transition-transform duration-300',
          sidebarOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0',
        )}
      >
        {/* Ambient glow */}
        <div className="pointer-events-none absolute -right-20 top-1/4 h-40 w-40 rounded-full bg-vulkran/5 blur-3xl" />

        {/* Logo + close button (mobile) */}
        <div className="flex h-14 items-center border-b border-sidebar-border px-4 gap-2 justify-between">
          <div className="flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-vulkran" />
            <span className="text-lg font-bold tracking-wider text-vulkran text-glow">VULKRAN</span>
            <span className="text-[10px] font-semibold text-vulkran-light/50 tracking-widest mt-0.5">OS</span>
          </div>
          <button
            className="md:hidden rounded-lg p-1 text-muted-foreground hover:text-foreground"
            onClick={() => setSidebarOpen(false)}
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 overflow-y-auto px-2 py-3">
          <ul className="space-y-0.5">
            {visibleItems.map((item) => {
              const isActive = location.pathname.startsWith(item.to)
              const Icon = item.icon
              return (
                <li key={item.to}>
                  <NavLink
                    to={item.to}
                    onClick={() => setSidebarOpen(false)}
                    className={cn(
                      'relative flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all duration-200',
                      isActive
                        ? 'text-foreground bg-sidebar-active'
                        : 'text-sidebar-foreground hover:text-foreground hover:bg-sidebar-active/50',
                      item.accent && !isActive && 'text-vulkran-light',
                    )}
                  >
                    {isActive && (
                      <motion.div
                        layoutId="nav-active"
                        className="absolute left-0 top-1/2 -translate-y-1/2 h-5 w-[3px] rounded-r-full bg-vulkran"
                        transition={{ type: 'spring', stiffness: 400, damping: 30 }}
                      />
                    )}
                    <Icon className={`h-4 w-4 ${isActive || item.accent ? 'text-vulkran-light' : ''}`} />
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
        <header className="flex h-14 items-center justify-between border-b border-border px-4 md:px-6 bg-surface-0/50 backdrop-blur-sm">
          <div className="flex items-center gap-3">
            {/* Hamburger for mobile */}
            <button
              className="md:hidden rounded-lg p-1.5 text-muted-foreground hover:text-foreground hover:bg-surface-2 transition-all"
              onClick={() => setSidebarOpen(true)}
            >
              <Menu className="h-5 w-5" />
            </button>
            <h2 className="text-lg font-semibold text-foreground">
              {currentPage?.label || 'VULKRAN OS'}
            </h2>
          </div>
          <div className="flex items-center gap-3">
            <button className="relative rounded-lg p-2 text-muted-foreground hover:text-foreground hover:bg-surface-2 transition-all">
              <Bell className="h-5 w-5" />
              <span className="absolute top-1.5 right-1.5 h-2 w-2 rounded-full bg-vulkran animate-pulse" />
            </button>
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-y-auto overflow-x-hidden p-4 md:p-6 pb-20 md:pb-6">
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

      {/* Mobile bottom nav */}
      <nav className="fixed bottom-0 left-0 right-0 z-30 md:hidden glass-strong border-t border-border safe-area-bottom">
        <div className="flex items-center justify-around h-14 px-2">
          {mobileItems.map((item) => {
            const isActive = location.pathname.startsWith(item.to)
            const Icon = item.icon
            return (
              <NavLink
                key={item.to}
                to={item.to}
                className={cn(
                  'flex flex-col items-center justify-center gap-0.5 px-3 py-1 rounded-lg transition-all min-w-[48px]',
                  isActive
                    ? 'text-vulkran-light'
                    : 'text-muted-foreground',
                )}
              >
                <Icon className="h-5 w-5" />
                <span className="text-[10px] font-medium">{item.label}</span>
                {item.accent && isActive && (
                  <motion.div
                    layoutId="mobile-active"
                    className="absolute -top-px left-1/2 -translate-x-1/2 h-[2px] w-8 rounded-full bg-vulkran"
                  />
                )}
              </NavLink>
            )
          })}
        </div>
      </nav>
    </div>
  )
}
