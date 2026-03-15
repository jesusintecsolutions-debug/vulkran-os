import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Suspense, lazy, useEffect } from 'react'
import { useAuthStore } from '@/stores/auth'

import PulseLayout from '@/layouts/PulseLayout'
import LoginPage from '@/pages/auth/LoginPage'
import DashboardPage from '@/pages/dashboard/DashboardPage'

// Lazy-loaded pages (code-split chunks)
const ClientsPage = lazy(() => import('@/pages/clients/ClientsPage'))
const ContentPage = lazy(() => import('@/pages/content/ContentPage'))
const ProjectDetailPage = lazy(() => import('@/pages/content/ProjectDetailPage'))
const LeadsPage = lazy(() => import('@/pages/leads/LeadsPage'))
const AccountingPage = lazy(() => import('@/pages/accounting/AccountingPage'))
const BriefingPage = lazy(() => import('@/pages/briefing/BriefingPage'))
const ChatPage = lazy(() => import('@/pages/chat/ChatPage'))
const FilesPage = lazy(() => import('@/pages/files/FilesPage'))
const SettingsPage = lazy(() => import('@/pages/settings/SettingsPage'))

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: 1, refetchOnWindowFocus: false },
  },
})

function PageLoader() {
  return (
    <div className="flex items-center justify-center h-64">
      <div className="h-8 w-8 rounded-full border-2 border-vulkran border-t-transparent animate-spin" />
    </div>
  )
}

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useAuthStore()

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center bg-black">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-vulkran border-t-transparent" />
      </div>
    )
  }

  if (!isAuthenticated) return <Navigate to="/login" replace />
  return <>{children}</>
}

function AppInit({ children }: { children: React.ReactNode }) {
  const loadUser = useAuthStore((s) => s.loadUser)

  useEffect(() => {
    loadUser()
  }, [loadUser])

  return <>{children}</>
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AppInit>
          <Routes>
            <Route path="/login" element={<LoginPage />} />

            {/* PulseLayout — unified brain-centric layout for ALL pages */}
            <Route
              element={
                <ProtectedRoute>
                  <PulseLayout />
                </ProtectedRoute>
              }
            >
              {/* Home — brain centered, modules radial */}
              <Route index element={null} />

              {/* Section pages — brain mini, content fills screen */}
              <Route path="dashboard" element={<DashboardPage />} />
              <Route path="clients" element={<Suspense fallback={<PageLoader />}><ClientsPage /></Suspense>} />
              <Route path="content" element={<Suspense fallback={<PageLoader />}><ContentPage /></Suspense>} />
              <Route path="content/projects/:id" element={<Suspense fallback={<PageLoader />}><ProjectDetailPage /></Suspense>} />
              <Route path="leads" element={<Suspense fallback={<PageLoader />}><LeadsPage /></Suspense>} />
              <Route path="accounting" element={<Suspense fallback={<PageLoader />}><AccountingPage /></Suspense>} />
              <Route path="briefing" element={<Suspense fallback={<PageLoader />}><BriefingPage /></Suspense>} />
              <Route path="chat" element={<Suspense fallback={<PageLoader />}><ChatPage /></Suspense>} />
              <Route path="files" element={<Suspense fallback={<PageLoader />}><FilesPage /></Suspense>} />
              <Route path="settings" element={<Suspense fallback={<PageLoader />}><SettingsPage /></Suspense>} />
            </Route>

            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </AppInit>
      </BrowserRouter>
    </QueryClientProvider>
  )
}
