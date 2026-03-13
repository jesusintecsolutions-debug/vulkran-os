import { useAuthStore } from '@/stores/auth'

export default function SettingsPage() {
  const { user } = useAuthStore()

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Ajustes</h1>

      <div className="rounded-lg border bg-card p-6">
        <h2 className="mb-4 text-lg font-semibold">Perfil</h2>
        <dl className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <dt className="text-muted-foreground">Nombre</dt>
            <dd className="font-medium">{user?.name || '—'}</dd>
          </div>
          <div>
            <dt className="text-muted-foreground">Email</dt>
            <dd className="font-medium">{user?.email || '—'}</dd>
          </div>
          <div>
            <dt className="text-muted-foreground">Rol</dt>
            <dd className="font-medium capitalize">{user?.role || '—'}</dd>
          </div>
        </dl>
      </div>
    </div>
  )
}
