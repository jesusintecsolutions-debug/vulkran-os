import { useAuthStore } from '@/stores/auth'
import { GlassCard } from '@/components/ui'
import { Settings } from 'lucide-react'

export default function SettingsPage() {
  const { user } = useAuthStore()

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Settings className="h-6 w-6 text-vulkran-light" />
        <h1 className="text-2xl font-bold">Ajustes</h1>
      </div>

      <GlassCard className="max-w-lg">
        <h2 className="mb-4 text-lg font-semibold text-foreground">Perfil</h2>
        <dl className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <dt className="text-xs text-muted-foreground uppercase tracking-wider mb-1">Nombre</dt>
            <dd className="font-medium text-foreground">{user?.name || '—'}</dd>
          </div>
          <div>
            <dt className="text-xs text-muted-foreground uppercase tracking-wider mb-1">Email</dt>
            <dd className="font-medium text-foreground">{user?.email || '—'}</dd>
          </div>
          <div>
            <dt className="text-xs text-muted-foreground uppercase tracking-wider mb-1">Rol</dt>
            <dd className="font-medium capitalize text-foreground">{user?.role || '—'}</dd>
          </div>
        </dl>
      </GlassCard>
    </div>
  )
}
