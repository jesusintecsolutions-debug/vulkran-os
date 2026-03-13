import { useQuery } from '@tanstack/react-query'
import { api } from '@/api/client'
import { GlassCard, Badge } from '@/components/ui'
import { Newspaper } from 'lucide-react'

interface Briefing {
  metrics: Record<string, unknown>
  summary: string
  generated_at: string
}

export default function BriefingPage() {
  const { data, isLoading } = useQuery<Briefing>({
    queryKey: ['briefing'],
    queryFn: async () => (await api.get('/briefing')).data,
  })

  if (isLoading) return (
    <div className="flex flex-col items-center justify-center h-64 gap-3">
      <div className="h-8 w-8 rounded-full border-2 border-vulkran border-t-transparent animate-spin" />
      <p className="text-sm text-muted-foreground">Generando briefing con IA...</p>
    </div>
  )

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Newspaper className="h-6 w-6 text-vulkran-light" />
          <h1 className="text-2xl font-bold">Briefing Diario</h1>
        </div>
        {data?.generated_at && (
          <Badge variant="purple">{new Date(data.generated_at).toLocaleString('es-ES')}</Badge>
        )}
      </div>

      <GlassCard variant="strong" className="max-w-3xl">
        <div className="whitespace-pre-wrap text-sm leading-relaxed text-foreground/90">
          {data?.summary || 'Sin datos disponibles.'}
        </div>
      </GlassCard>
    </div>
  )
}
