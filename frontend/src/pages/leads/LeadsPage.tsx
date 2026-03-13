import { useQuery } from '@tanstack/react-query'
import { api } from '@/api/client'
import { GlassCard, Badge } from '@/components/ui'
import { Target } from 'lucide-react'

interface Lead {
  id: string
  name: string
  company: string | null
  email: string | null
  stage: string
  source: string | null
  estimated_value: string | null
  created_at: string
}

const STAGE_VARIANT: Record<string, 'info' | 'neon' | 'purple' | 'warning' | 'success' | 'error' | 'default'> = {
  new: 'info',
  contacted: 'neon',
  meeting: 'purple',
  proposal: 'warning',
  negotiation: 'warning',
  won: 'success',
  lost: 'error',
}

export default function LeadsPage() {
  const { data: leads, isLoading } = useQuery<Lead[]>({
    queryKey: ['leads'],
    queryFn: async () => (await api.get('/leads')).data,
  })

  if (isLoading) return <div className="flex items-center justify-center h-64"><div className="h-8 w-8 rounded-full border-2 border-vulkran border-t-transparent animate-spin" /></div>

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <Target className="h-6 w-6 text-vulkran-light" />
        <h1 className="text-xl sm:text-2xl font-bold">Pipeline de Leads</h1>
      </div>

      {/* Mobile: card view */}
      <div className="space-y-3 md:hidden">
        {leads?.map((l) => (
          <GlassCard key={l.id} className="!p-4 overflow-hidden">
            <div className="flex items-start justify-between gap-2 mb-2">
              <div className="min-w-0 flex-1">
                <p className="font-medium text-foreground truncate">{l.name}</p>
                <p className="text-xs text-muted-foreground truncate">{l.company || 'Sin empresa'}</p>
              </div>
              <Badge variant={STAGE_VARIANT[l.stage] || 'default'} dot className="shrink-0">{l.stage}</Badge>
            </div>
            <div className="flex items-center justify-between text-xs text-muted-foreground">
              <span className="capitalize truncate mr-2">{l.source || '—'}</span>
              <span className="font-mono text-foreground font-medium shrink-0">{l.estimated_value ? `${l.estimated_value}€` : '—'}</span>
            </div>
          </GlassCard>
        ))}
        {leads?.length === 0 && <p className="text-sm text-muted-foreground text-center py-8">Sin leads activos</p>}
      </div>

      {/* Desktop: table view */}
      <GlassCard hover={false} className="overflow-hidden !p-0 hidden md:block">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border text-left">
              <th className="px-4 py-3 font-medium text-muted-foreground text-xs uppercase tracking-wider">Nombre</th>
              <th className="px-4 py-3 font-medium text-muted-foreground text-xs uppercase tracking-wider">Empresa</th>
              <th className="px-4 py-3 font-medium text-muted-foreground text-xs uppercase tracking-wider">Origen</th>
              <th className="px-4 py-3 font-medium text-muted-foreground text-xs uppercase tracking-wider">Etapa</th>
              <th className="px-4 py-3 font-medium text-muted-foreground text-xs uppercase tracking-wider text-right">Valor est.</th>
            </tr>
          </thead>
          <tbody>
            {leads?.map((l) => (
              <tr key={l.id} className="border-b border-border/50 last:border-0 hover:bg-surface-2/50 transition-colors">
                <td className="px-4 py-3 font-medium text-foreground">{l.name}</td>
                <td className="px-4 py-3 text-muted-foreground">{l.company || '—'}</td>
                <td className="px-4 py-3 text-muted-foreground capitalize">{l.source || '—'}</td>
                <td className="px-4 py-3"><Badge variant={STAGE_VARIANT[l.stage] || 'default'} dot>{l.stage}</Badge></td>
                <td className="px-4 py-3 text-right font-mono text-foreground">{l.estimated_value ? `${l.estimated_value}€` : '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </GlassCard>
    </div>
  )
}
