import { useQuery } from '@tanstack/react-query'
import { api } from '@/api/client'

interface Batch {
  id: string
  title: string
  status: string
  platform: string | null
  item_count: number
  created_at: string
}

const STATUS_COLORS: Record<string, string> = {
  draft: 'bg-gray-100 text-gray-700',
  generating: 'bg-blue-100 text-blue-700',
  review: 'bg-yellow-100 text-yellow-700',
  approved: 'bg-green-100 text-green-700',
  published: 'bg-purple-100 text-purple-700',
  failed: 'bg-red-100 text-red-700',
}

export default function ContentPage() {
  const { data: batches, isLoading } = useQuery<Batch[]>({
    queryKey: ['content-batches'],
    queryFn: async () => (await api.get('/content/batches')).data,
  })

  if (isLoading) return <div className="text-muted-foreground">Cargando...</div>

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Contenido</h1>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {batches?.map((b) => (
          <div key={b.id} className="rounded-lg border bg-card p-4">
            <div className="flex items-start justify-between">
              <h3 className="font-medium">{b.title}</h3>
              <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_COLORS[b.status] || 'bg-gray-100'}`}>
                {b.status}
              </span>
            </div>
            <p className="mt-1 text-sm text-muted-foreground">
              {b.platform || 'General'} · {b.item_count} items
            </p>
            <p className="mt-2 text-xs text-muted-foreground">
              {new Date(b.created_at).toLocaleDateString('es-ES')}
            </p>
          </div>
        ))}
        {batches?.length === 0 && (
          <p className="col-span-full text-muted-foreground">No hay batches de contenido aún</p>
        )}
      </div>
    </div>
  )
}
