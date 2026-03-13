import { useQuery } from '@tanstack/react-query'
import { api } from '@/api/client'
import { GlassCard, Badge } from '@/components/ui'

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
      <h1 className="text-2xl font-bold">Pipeline de Leads</h1>

      <GlassCard hover={false} className="overflow-hidden !p-0">
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
