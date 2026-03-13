import { useQuery } from '@tanstack/react-query'
import { api } from '@/api/client'
import { GlassCard, Badge } from '@/components/ui'

interface Batch {
  id: string
  title: string
  status: string
  platform: string | null
  item_count: number
  created_at: string
}

const STATUS_VARIANT: Record<string, 'default' | 'info' | 'warning' | 'success' | 'purple' | 'error'> = {
  draft: 'default',
  generating: 'info',
  review: 'warning',
  approved: 'success',
  published: 'purple',
  failed: 'error',
}

export default function ContentPage() {
  const { data: batches, isLoading } = useQuery<Batch[]>({
    queryKey: ['content-batches'],
    queryFn: async () => (await api.get('/content/batches')).data,
  })

  if (isLoading) return <div className="flex items-center justify-center h-64"><div className="h-8 w-8 rounded-full border-2 border-vulkran border-t-transparent animate-spin" /></div>

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">Contenido</h1>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {batches?.map((b) => (
          <GlassCard key={b.id}>
            <div className="flex items-start justify-between">
              <h3 className="font-medium text-foreground">{b.title}</h3>
              <Badge variant={STATUS_VARIANT[b.status] || 'default'} dot>{b.status}</Badge>
            </div>
            <p className="mt-2 text-sm text-muted-foreground">
              {b.platform || 'General'} · {b.item_count} items
            </p>
            <p className="mt-2 text-xs text-muted-foreground">
              {new Date(b.created_at).toLocaleDateString('es-ES')}
            </p>
          </GlassCard>
        ))}
        {batches?.length === 0 && (
          <p className="col-span-full text-muted-foreground">No hay batches de contenido aún</p>
        )}
      </div>
    </div>
  )
}
