import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/api/client'
import { GlassCard, Badge } from '@/components/ui'
import { FileText, Video, Plus } from 'lucide-react'
import { VideoProjectList } from '@/components/content/VideoProjectList'
import { NewProjectModal } from '@/components/content/NewProjectModal'

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

type Tab = 'batches' | 'videos'

export default function ContentPage() {
  const [tab, setTab] = useState<Tab>('videos')
  const [showNewProject, setShowNewProject] = useState(false)

  const { data: batches, isLoading: batchesLoading } = useQuery<Batch[]>({
    queryKey: ['content-batches'],
    queryFn: async () => (await api.get('/content/batches')).data,
  })

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <div className="flex items-center gap-3">
          <FileText className="h-6 w-6 text-vulkran-light shrink-0" />
          <h1 className="text-xl sm:text-2xl font-bold">Content Engine</h1>
        </div>
        <button
          onClick={() => setShowNewProject(true)}
          className="flex items-center gap-2 rounded-lg bg-vulkran px-4 py-2 text-sm font-medium text-white hover:bg-vulkran/90 transition-all shadow-lg shadow-vulkran/20"
        >
          <Plus className="h-4 w-4" />
          <span className="hidden sm:inline">Nuevo Proyecto</span>
        </button>
      </div>

      {/* Tab switcher */}
      <div className="flex gap-1 rounded-lg bg-surface-1 p-1 w-fit">
        <button
          onClick={() => setTab('videos')}
          className={`flex items-center gap-2 rounded-md px-4 py-2 text-sm font-medium transition-all ${
            tab === 'videos'
              ? 'bg-surface-2 text-foreground shadow-sm'
              : 'text-muted-foreground hover:text-foreground'
          }`}
        >
          <Video className="h-4 w-4" />
          Video Projects
        </button>
        <button
          onClick={() => setTab('batches')}
          className={`flex items-center gap-2 rounded-md px-4 py-2 text-sm font-medium transition-all ${
            tab === 'batches'
              ? 'bg-surface-2 text-foreground shadow-sm'
              : 'text-muted-foreground hover:text-foreground'
          }`}
        >
          <FileText className="h-4 w-4" />
          Content Batches
        </button>
      </div>

      {/* Video Projects tab */}
      {tab === 'videos' && <VideoProjectList />}

      {/* Content Batches tab */}
      {tab === 'batches' && (
        <>
          {batchesLoading ? (
            <div className="flex items-center justify-center h-64">
              <div className="h-8 w-8 rounded-full border-2 border-vulkran border-t-transparent animate-spin" />
            </div>
          ) : (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {batches?.map((b) => (
                <GlassCard key={b.id}>
                  <div className="flex items-start justify-between gap-2">
                    <h3 className="font-medium text-foreground truncate">{b.title}</h3>
                    <Badge variant={STATUS_VARIANT[b.status] || 'default'} dot className="shrink-0">
                      {b.status}
                    </Badge>
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
                <p className="col-span-full text-muted-foreground text-center py-8">
                  No hay batches de contenido aun
                </p>
              )}
            </div>
          )}
        </>
      )}

      {/* New Project Modal */}
      {showNewProject && <NewProjectModal onClose={() => setShowNewProject(false)} />}
    </div>
  )
}
