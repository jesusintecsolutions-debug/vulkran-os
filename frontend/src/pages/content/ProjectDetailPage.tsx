import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/api/client'
import { GlassCard, Badge } from '@/components/ui'
import { MomentEditor } from '@/components/content/MomentEditor'
import { RenderProgress } from '@/components/content/RenderProgress'
import {
  ArrowLeft,
  Play,
  Mic,
  Plus,
  Sparkles,
  Loader2,
  Video,
  Clock,
  Layers,
} from 'lucide-react'

interface SlotDef {
  key: string
  type: string
  label: string
  required: boolean
  default?: unknown
  options?: string[]
  min?: number
  max?: number
  group?: string
  description?: string
}

interface Template {
  id: string
  name: string
  slug: string
  description: string | null
  slots_schema: SlotDef[]
  fps: number
  width: number
  height: number
}

interface Moment {
  id: string
  project_id: string
  template_id: string
  sort_order: number
  slots_data: Record<string, unknown>
  duration_frames: number
  transition_type: string
  transition_duration: number
  voiceover_text: string | null
  voiceover_url: string | null
}

interface VideoProject {
  id: string
  client_id: string
  title: string
  brief: string | null
  status: string
  render_url: string | null
  voiceover_url: string | null
  template_id: string | null
  created_at: string
  moments: Moment[]
}

const STATUS_VARIANT: Record<string, 'default' | 'info' | 'warning' | 'success' | 'error' | 'neon'> = {
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

export default function ProjectDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [activeRenderId, setActiveRenderId] = useState<string | null>(null)

  const { data: project, isLoading } = useQuery<VideoProject>({
    queryKey: ['video-project', id],
    queryFn: async () => (await api.get(`/content-engine/projects/${id}`)).data,
    enabled: !!id,
  })

  const { data: templates } = useQuery<Template[]>({
    queryKey: ['video-templates'],
    queryFn: async () => (await api.get('/content-engine/templates')).data,
  })

  const startRender = useMutation({
    mutationFn: async () => {
      const { data } = await api.post(`/content-engine/projects/${id}/render`, { quality: 'medium' })
      return data
    },
    onSuccess: (data) => {
      setActiveRenderId(data.render_id)
      queryClient.invalidateQueries({ queryKey: ['video-project', id] })
    },
  })

  const generateVoiceover = useMutation({
    mutationFn: async () => {
      const { data } = await api.post(`/content-engine/projects/${id}/voiceover`, {
        voice_name: 'es-ES-Wavenet-B',
        language_code: 'es-ES',
      })
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['video-project', id] })
    },
  })

  const addMoment = useMutation({
    mutationFn: async () => {
      const templateId = project?.template_id || templates?.[0]?.id
      await api.post(`/content-engine/projects/${id}/moments`, {
        template_id: templateId,
        slots_data: {},
        duration_frames: 120,
        transition_type: 'fade',
        transition_duration: 15,
      })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['video-project', id] })
    },
  })

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="h-8 w-8 rounded-full border-2 border-vulkran border-t-transparent animate-spin" />
      </div>
    )
  }

  if (!project) {
    return (
      <div className="text-center py-16">
        <p className="text-muted-foreground">Proyecto no encontrado</p>
      </div>
    )
  }

  // Find template for the project's moments to get slot definitions
  const getTemplateSlotsForMoment = (moment: Moment): SlotDef[] => {
    const template = templates?.find((t) => t.id === moment.template_id)
    return template?.slots_schema || []
  }

  const sortedMoments = [...(project.moments || [])].sort((a, b) => a.sort_order - b.sort_order)
  const totalDuration = sortedMoments.reduce((acc, m) => acc + m.duration_frames, 0)
  const canRender = project.status === 'review' && sortedMoments.length > 0
  const canVoiceover = project.status === 'review' && sortedMoments.some((m) => m.voiceover_text)

  return (
    <div className="space-y-4 max-w-4xl mx-auto">
      {/* Header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div className="flex items-start gap-3">
          <button
            onClick={() => navigate('/content')}
            className="mt-1 rounded-lg p-1.5 text-muted-foreground hover:text-foreground hover:bg-surface-2 transition-all shrink-0"
          >
            <ArrowLeft className="h-5 w-5" />
          </button>
          <div>
            <h1 className="text-xl sm:text-2xl font-bold text-foreground">{project.title}</h1>
            {project.brief && (
              <p className="mt-1 text-sm text-muted-foreground line-clamp-2">{project.brief}</p>
            )}
          </div>
        </div>
        <Badge variant={STATUS_VARIANT[project.status] || 'default'} dot>
          {STATUS_LABEL[project.status] || project.status}
        </Badge>
      </div>

      {/* Stats bar */}
      <div className="flex items-center gap-4 text-xs text-muted-foreground flex-wrap">
        <span className="flex items-center gap-1.5">
          <Layers className="h-3.5 w-3.5" />
          {sortedMoments.length} momentos
        </span>
        <span className="flex items-center gap-1.5">
          <Clock className="h-3.5 w-3.5" />
          {(totalDuration / 30).toFixed(1)}s total
        </span>
        <span className="flex items-center gap-1.5">
          <Video className="h-3.5 w-3.5" />
          {project.template_id ? 'Template asignado' : 'Sin template'}
        </span>
      </div>

      {/* Action buttons */}
      {project.status === 'review' && (
        <div className="flex items-center gap-3 flex-wrap">
          <button
            onClick={() => startRender.mutate()}
            disabled={!canRender || startRender.isPending}
            className="flex items-center gap-2 rounded-lg bg-vulkran px-4 py-2 text-sm font-medium text-white hover:bg-vulkran/90 transition-all shadow-lg shadow-vulkran/20 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {startRender.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Play className="h-4 w-4" />
            )}
            Renderizar
          </button>
          <button
            onClick={() => generateVoiceover.mutate()}
            disabled={!canVoiceover || generateVoiceover.isPending}
            className="flex items-center gap-2 rounded-lg border border-border bg-surface-1 px-4 py-2 text-sm font-medium text-foreground hover:bg-surface-2 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {generateVoiceover.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Mic className="h-4 w-4" />
            )}
            Generar Voiceover
          </button>
          <button
            onClick={() => addMoment.mutate()}
            disabled={addMoment.isPending}
            className="flex items-center gap-2 rounded-lg border border-border bg-surface-1 px-4 py-2 text-sm font-medium text-foreground hover:bg-surface-2 transition-all disabled:opacity-50"
          >
            <Plus className="h-4 w-4" />
            Añadir momento
          </button>
        </div>
      )}

      {/* Render progress */}
      {activeRenderId && (
        <RenderProgress
          renderId={activeRenderId}
          onComplete={() => {
            queryClient.invalidateQueries({ queryKey: ['video-project', id] })
          }}
        />
      )}

      {/* Generating indicator */}
      {project.status === 'generating' && (
        <GlassCard variant="neon" hover={false} className="flex items-center gap-3 !py-4">
          <Sparkles className="h-5 w-5 text-vulkran-light animate-pulse" />
          <div>
            <p className="text-sm font-medium text-foreground">Generando momentos con AI...</p>
            <p className="text-xs text-muted-foreground">Claude esta creando el contenido del video</p>
          </div>
        </GlassCard>
      )}

      {/* Moments list */}
      {sortedMoments.length > 0 ? (
        <div className="space-y-3">
          <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">
            Momentos
          </h2>
          {sortedMoments.map((moment, idx) => (
            <MomentEditor
              key={moment.id}
              moment={moment}
              index={idx}
              templateSlots={getTemplateSlotsForMoment(moment)}
              projectId={project.id}
            />
          ))}
        </div>
      ) : (
        project.status !== 'generating' && (
          <GlassCard hover={false} className="text-center py-12">
            <Layers className="h-12 w-12 text-muted-foreground mx-auto mb-4 opacity-50" />
            <p className="text-muted-foreground">No hay momentos aun</p>
            <p className="text-xs text-muted-foreground mt-1">
              Añade momentos manualmente o genera con AI
            </p>
          </GlassCard>
        )
      )}
    </div>
  )
}
