import { useQuery } from '@tanstack/react-query'
import { api } from '@/api/client'
import { GlassCard, Badge } from '@/components/ui'
import { Users } from 'lucide-react'

interface Client {
  id: string
  name: string
  slug: string
  sector: string
  contact_email: string | null
  monthly_fee: string | null
  status: string
}

export default function ClientsPage() {
  const { data: clients, isLoading } = useQuery<Client[]>({
    queryKey: ['clients'],
    queryFn: async () => (await api.get('/clients')).data,
  })

  if (isLoading) return <div className="flex items-center justify-center h-64"><div className="h-8 w-8 rounded-full border-2 border-vulkran border-t-transparent animate-spin" /></div>

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <div className="flex items-center gap-3">
          <Users className="h-6 w-6 text-vulkran-light" />
          <h1 className="text-xl sm:text-2xl font-bold">Clientes</h1>
        </div>
        <Badge variant="purple" dot>{clients?.length || 0} activos</Badge>
      </div>

      {/* Mobile: card view */}
      <div className="space-y-3 md:hidden">
        {clients?.map((c) => (
          <GlassCard key={c.id} className="!p-4">
            <div className="flex items-start justify-between mb-2">
              <div className="min-w-0 flex-1 mr-2">
                <p className="font-medium text-foreground truncate">{c.name}</p>
                <p className="text-xs text-muted-foreground">{c.sector}</p>
              </div>
              <Badge variant="success" dot>{c.status}</Badge>
            </div>
            <div className="flex items-center justify-between text-xs text-muted-foreground">
              <span className="truncate mr-2">{c.contact_email || '—'}</span>
              <span className="font-mono text-foreground font-medium shrink-0">{c.monthly_fee ? `${c.monthly_fee}€/mes` : '—'}</span>
            </div>
          </GlassCard>
        ))}
        {clients?.length === 0 && <p className="text-sm text-muted-foreground text-center py-8">Sin clientes activos</p>}
      </div>

      {/* Desktop: table view */}
      <GlassCard hover={false} className="overflow-hidden !p-0 hidden md:block">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border text-left">
              <th className="px-4 py-3 font-medium text-muted-foreground text-xs uppercase tracking-wider">Nombre</th>
              <th className="px-4 py-3 font-medium text-muted-foreground text-xs uppercase tracking-wider">Sector</th>
              <th className="px-4 py-3 font-medium text-muted-foreground text-xs uppercase tracking-wider">Email</th>
              <th className="px-4 py-3 font-medium text-muted-foreground text-xs uppercase tracking-wider text-right">Cuota/mes</th>
              <th className="px-4 py-3 font-medium text-muted-foreground text-xs uppercase tracking-wider">Estado</th>
            </tr>
          </thead>
          <tbody>
            {clients?.map((c) => (
              <tr key={c.id} className="border-b border-border/50 last:border-0 hover:bg-surface-2/50 transition-colors">
                <td className="px-4 py-3 font-medium text-foreground">{c.name}</td>
                <td className="px-4 py-3 text-muted-foreground">{c.sector}</td>
                <td className="px-4 py-3 text-muted-foreground">{c.contact_email || '—'}</td>
                <td className="px-4 py-3 text-right text-foreground font-mono">{c.monthly_fee ? `${c.monthly_fee}€` : '—'}</td>
                <td className="px-4 py-3"><Badge variant="success" dot>{c.status}</Badge></td>
              </tr>
            ))}
          </tbody>
        </table>
      </GlassCard>
    </div>
  )
}
