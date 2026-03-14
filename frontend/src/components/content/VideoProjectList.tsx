import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { api } from '@/api/client'
import { GlassCard, Badge } from '@/components/ui'
import { Video, Play, Download, Eye } from 'lucide-react'

interface VideoProject {
  id: string
  client_id: string
  title: string
  description: string | null
  status: string
  render_url: string | null
  thumbnail_url: string | null
  created_at: string
}

const STATUS_VARIANT: Record<string, 'default' | 'info' | 'warning' | 'success' | 'purple' | 'error' | 'neon'> = {
  draft: 'default',
  generating: 'neon',
  review: 'warning',
  rendering: 'info',
  done: 'success',
  error: 'error',
}

const STATUS_LABEL: Record<string, string> = {
  draft: 'Borrador',
  generating: 'Generando...',
  review: 'En revision',
  rendering: 'Renderizando...',
  done: 'Completado',
  error: 'Error',
}

export function VideoProjectList() {
  const navigate = useNavigate()
  const { data: projects, isLoading } = useQuery<VideoProject[]>({
    queryKey: ['video-projects'],
    queryFn: async () => (await api.get('/content-engine/projects')).data,
    refetchInterval: 10000,
  })

  const openProject = (id: string) => navigate(`/content/projects/${id}`)

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="h-8 w-8 rounded-full border-2 border-vulkran border-t-transparent animate-spin" />
      </div>
    )
  }

  if (!projects?.length) {
    return (
      <GlassCard hover={false} className="text-center py-12">
        <Video className="h-12 w-12 text-muted-foreground mx-auto mb-4 opacity-50" />
        <p className="text-muted-foreground">No hay proyectos de video aun</p>
        <p className="text-xs text-muted-foreground mt-1">
          Crea uno nuevo o pidele al agente AI que genere un video
        </p>
      </GlassCard>
    )
  }

  return (
    <div className="space-y-3">
      {/* Mobile: card view */}
      <div className="space-y-3 md:hidden">
        {projects.map((p) => (
          <GlassCard
            key={p.id}
            className="!p-4 overflow-hidden cursor-pointer"
            onClick={() => openProject(p.id)}
          >
            <div className="flex items-start justify-between gap-2 mb-2">
              <div className="min-w-0 flex-1">
                <p className="font-medium text-foreground truncate">{p.title}</p>
                <p className="text-xs text-muted-foreground truncate">{p.description || 'Sin descripcion'}</p>
              </div>
              <Badge variant={STATUS_VARIANT[p.status] || 'default'} dot className="shrink-0">
                {STATUS_LABEL[p.status] || p.status}
              </Badge>
            </div>
            <div className="flex items-center justify-between text-xs text-muted-foreground">
              <span>{new Date(p.created_at).toLocaleDateString('es-ES')}</span>
              <div className="flex gap-2">
                {p.status === 'done' && p.render_url && (
                  <a
                    href={p.render_url}
                    onClick={(e) => e.stopPropagation()}
                    className="text-vulkran-light hover:text-vulkran"
                  >
                    <Download className="h-4 w-4" />
                  </a>
                )}
                {(p.status === 'generating' || p.status === 'rendering') && (
                  <div className="h-4 w-4 rounded-full border-2 border-vulkran border-t-transparent animate-spin" />
                )}
              </div>
            </div>
          </GlassCard>
        ))}
      </div>

      {/* Desktop: table view */}
      <GlassCard hover={false} className="overflow-hidden !p-0 hidden md:block">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border text-left">
              <th className="px-4 py-3 font-medium text-muted-foreground text-xs uppercase tracking-wider">Titulo</th>
              <th className="px-4 py-3 font-medium text-muted-foreground text-xs uppercase tracking-wider">Descripcion</th>
              <th className="px-4 py-3 font-medium text-muted-foreground text-xs uppercase tracking-wider">Estado</th>
              <th className="px-4 py-3 font-medium text-muted-foreground text-xs uppercase tracking-wider">Fecha</th>
              <th className="px-4 py-3 font-medium text-muted-foreground text-xs uppercase tracking-wider text-right">Acciones</th>
            </tr>
          </thead>
          <tbody>
            {projects.map((p) => (
              <tr
                key={p.id}
                className="border-b border-border/50 last:border-0 hover:bg-surface-2/50 transition-colors cursor-pointer"
                onClick={() => openProject(p.id)}
              >
                <td className="px-4 py-3 font-medium text-foreground">{p.title}</td>
                <td className="px-4 py-3 text-muted-foreground truncate max-w-[200px]">{p.description || '—'}</td>
                <td className="px-4 py-3">
                  <Badge variant={STATUS_VARIANT[p.status] || 'default'} dot>
                    {STATUS_LABEL[p.status] || p.status}
                  </Badge>
                </td>
                <td className="px-4 py-3 text-muted-foreground">
                  {new Date(p.created_at).toLocaleDateString('es-ES')}
                </td>
                <td className="px-4 py-3 text-right">
                  <div className="flex gap-2 justify-end">
                    <button
                      onClick={(e) => { e.stopPropagation(); openProject(p.id) }}
                      className="rounded-lg p-1.5 text-muted-foreground hover:text-vulkran-light hover:bg-vulkran/10 transition-all"
                      title="Ver proyecto"
                    >
                      <Eye className="h-4 w-4" />
                    </button>
                    {p.status === 'done' && p.render_url && (
                      <a
                        href={p.render_url}
                        onClick={(e) => e.stopPropagation()}
                        className="rounded-lg p-1.5 text-muted-foreground hover:text-vulkran-light hover:bg-vulkran/10 transition-all"
                        title="Descargar"
                      >
                        <Download className="h-4 w-4" />
                      </a>
                    )}
                    {(p.status === 'generating' || p.status === 'rendering') && (
                      <div className="h-4 w-4 rounded-full border-2 border-vulkran border-t-transparent animate-spin" />
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </GlassCard>
    </div>
  )
}
