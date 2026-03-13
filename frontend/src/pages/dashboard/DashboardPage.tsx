import { useQuery } from '@tanstack/react-query'
import { api } from '@/api/client'
import { useAuthStore } from '@/stores/auth'

interface Metrics {
  timestamp: string
  clients: { active: number; mrr: string }
  leads: {
    pipeline: Record<string, number>
    pipeline_value: string
    activities_24h: number
  }
  content: {
    total_batches: number
    in_review: number
    items_generated_24h: number
  }
  tasks: { pending: number }
}

function StatCard({ label, value, sub }: { label: string; value: string | number; sub?: string }) {
  return (
    <div className="rounded-lg border bg-card p-5">
      <p className="text-sm text-muted-foreground">{label}</p>
      <p className="mt-1 text-2xl font-bold">{value}</p>
      {sub && <p className="mt-0.5 text-xs text-muted-foreground">{sub}</p>}
    </div>
  )
}

export default function DashboardPage() {
  const user = useAuthStore((s) => s.user)

  const { data: metrics, isLoading } = useQuery<Metrics>({
    queryKey: ['briefing-metrics'],
    queryFn: async () => (await api.get('/briefing/metrics')).data,
  })

  if (isLoading) {
    return <div className="text-muted-foreground">Cargando métricas...</div>
  }

  if (!metrics) {
    return <div className="text-muted-foreground">Sin datos disponibles</div>
  }

  const totalLeads = Object.values(metrics.leads.pipeline).reduce((a, b) => a + b, 0)

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Hola, {user?.name}</h1>
        <p className="text-muted-foreground">Resumen de tu negocio hoy</p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          label="Clientes activos"
          value={metrics.clients.active}
          sub={`${metrics.clients.mrr}€ MRR`}
        />
        <StatCard
          label="Leads en pipeline"
          value={totalLeads}
          sub={`${metrics.leads.pipeline_value}€ valor`}
        />
        <StatCard
          label="Contenido generado (24h)"
          value={metrics.content.items_generated_24h}
          sub={`${metrics.content.in_review} en revisión`}
        />
        <StatCard
          label="Tareas pendientes"
          value={metrics.tasks.pending}
        />
      </div>

      {/* Pipeline breakdown */}
      <div className="rounded-lg border bg-card p-5">
        <h3 className="mb-3 font-semibold">Pipeline de ventas</h3>
        <div className="flex flex-wrap gap-3">
          {Object.entries(metrics.leads.pipeline).map(([stage, count]) => (
            <div key={stage} className="rounded-md bg-muted px-3 py-1.5 text-sm">
              <span className="font-medium capitalize">{stage}</span>
              <span className="ml-2 text-muted-foreground">{count}</span>
            </div>
          ))}
          {Object.keys(metrics.leads.pipeline).length === 0 && (
            <p className="text-sm text-muted-foreground">Sin leads activos</p>
          )}
        </div>
      </div>
    </div>
  )
}
