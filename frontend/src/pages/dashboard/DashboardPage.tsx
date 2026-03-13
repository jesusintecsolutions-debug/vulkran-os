import { useQuery } from '@tanstack/react-query'
import { api } from '@/api/client'
import { useAuthStore } from '@/stores/auth'
import { motion } from 'framer-motion'
import { Users, Target, FileText, ListTodo } from 'lucide-react'
import { StatCard, GlassCard, Badge } from '@/components/ui'

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

const STAGE_VARIANT: Record<string, 'info' | 'neon' | 'purple' | 'warning' | 'success' | 'error' | 'default'> = {
  new: 'info',
  contacted: 'neon',
  meeting: 'purple',
  proposal: 'warning',
  negotiation: 'warning',
  won: 'success',
  lost: 'error',
}

export default function DashboardPage() {
  const user = useAuthStore((s) => s.user)

  const { data: metrics, isLoading } = useQuery<Metrics>({
    queryKey: ['briefing-metrics'],
    queryFn: async () => (await api.get('/briefing/metrics')).data,
  })

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="h-8 w-8 rounded-full border-2 border-vulkran border-t-transparent animate-spin" />
      </div>
    )
  }

  if (!metrics) return <div className="text-muted-foreground">Sin datos disponibles</div>

  const totalLeads = Object.values(metrics.leads.pipeline).reduce((a, b) => a + b, 0)

  return (
    <div className="space-y-6">
      <motion.div initial={{ opacity: 0, y: -5 }} animate={{ opacity: 1, y: 0 }}>
        <h1 className="text-xl sm:text-2xl font-bold">Hola, {user?.name}</h1>
        <p className="text-muted-foreground">Resumen de tu negocio hoy</p>
      </motion.div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Clientes activos" value={metrics.clients.active} subtitle={`${metrics.clients.mrr}€ MRR`} icon={<Users className="h-6 w-6" />} accentColor="vulkran" delay={0} />
        <StatCard label="Leads en pipeline" value={totalLeads} subtitle={`${metrics.leads.pipeline_value}€ valor`} icon={<Target className="h-6 w-6" />} accentColor="cyan" delay={0.1} />
        <StatCard label="Contenido (24h)" value={metrics.content.items_generated_24h} subtitle={`${metrics.content.in_review} en revisión`} icon={<FileText className="h-6 w-6" />} accentColor="green" delay={0.2} />
        <StatCard label="Tareas pendientes" value={metrics.tasks.pending} icon={<ListTodo className="h-6 w-6" />} accentColor="amber" delay={0.3} />
      </div>

      <GlassCard>
        <h3 className="mb-3 font-semibold text-foreground">Pipeline de ventas</h3>
        <div className="flex flex-wrap gap-2">
          {Object.entries(metrics.leads.pipeline).map(([stage, count]) => (
            <Badge key={stage} variant={STAGE_VARIANT[stage] || 'default'} dot>
              <span className="capitalize">{stage}</span>
              <span className="ml-1 opacity-70">{count}</span>
            </Badge>
          ))}
          {Object.keys(metrics.leads.pipeline).length === 0 && (
            <p className="text-sm text-muted-foreground">Sin leads activos</p>
          )}
        </div>
      </GlassCard>
    </div>
  )
}
