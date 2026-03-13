import { useQuery } from '@tanstack/react-query'
import { api } from '@/api/client'

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

  if (isLoading) return <div className="text-muted-foreground">Generando briefing...</div>

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Briefing Diario</h1>
        {data?.generated_at && (
          <span className="text-xs text-muted-foreground">
            {new Date(data.generated_at).toLocaleString('es-ES')}
          </span>
        )}
      </div>

      <div className="rounded-lg border bg-card p-6">
        <div className="prose prose-sm max-w-none whitespace-pre-wrap text-card-foreground">
          {data?.summary || 'Sin datos disponibles.'}
        </div>
      </div>
    </div>
  )
}
