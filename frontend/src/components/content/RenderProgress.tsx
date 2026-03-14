import { useQuery } from '@tanstack/react-query'
import { api } from '@/api/client'
import { GlassCard } from '@/components/ui'
import { Loader2, CheckCircle2, AlertCircle, Download } from 'lucide-react'
import { motion } from 'framer-motion'

interface RenderStatus {
  id: string
  status: string
  progress: number
  quality: string
  output_path: string | null
  error_message: string | null
  started_at: string | null
  completed_at: string | null
}

interface RenderProgressProps {
  renderId: string
  onComplete?: () => void
}

export function RenderProgress({ renderId, onComplete }: RenderProgressProps) {
  const { data: render } = useQuery<RenderStatus>({
    queryKey: ['render-status', renderId],
    queryFn: async () => (await api.get(`/content-engine/renders/${renderId}/status`)).data,
    refetchInterval: (query) => {
      const status = query.state.data?.status
      if (status === 'done' || status === 'error') {
        onComplete?.()
        return false
      }
      return 2000
    },
  })

  if (!render) {
    return (
      <GlassCard hover={false} className="flex items-center gap-3 !py-3">
        <Loader2 className="h-4 w-4 animate-spin text-vulkran-light" />
        <span className="text-sm text-muted-foreground">Cargando estado...</span>
      </GlassCard>
    )
  }

  const isRendering = render.status === 'rendering'
  const isDone = render.status === 'done'
  const isError = render.status === 'error'

  return (
    <GlassCard hover={false} className="!p-4 overflow-hidden">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          {isRendering && <Loader2 className="h-4 w-4 animate-spin text-vulkran-light" />}
          {isDone && <CheckCircle2 className="h-4 w-4 text-success" />}
          {isError && <AlertCircle className="h-4 w-4 text-error" />}
          <span className="text-sm font-medium text-foreground">
            {isRendering && 'Renderizando...'}
            {isDone && 'Render completado'}
            {isError && 'Error en render'}
            {render.status === 'queued' && 'En cola...'}
          </span>
        </div>
        <span className="text-xs text-muted-foreground uppercase">{render.quality}</span>
      </div>

      {/* Progress bar */}
      {(isRendering || render.status === 'queued') && (
        <div className="relative h-2 w-full overflow-hidden rounded-full bg-surface-1 border border-border">
          <motion.div
            className="absolute inset-y-0 left-0 rounded-full bg-gradient-to-r from-vulkran to-vulkran-light"
            initial={{ width: 0 }}
            animate={{ width: `${render.progress}%` }}
            transition={{ duration: 0.5, ease: 'easeOut' }}
          />
        </div>
      )}

      {isRendering && (
        <p className="mt-2 text-xs text-muted-foreground text-right font-mono">{render.progress}%</p>
      )}

      {isError && render.error_message && (
        <p className="mt-2 text-xs text-error bg-error/10 rounded-lg px-3 py-2">{render.error_message}</p>
      )}

      {isDone && render.output_path && (
        <a
          href={`/api/content-engine/renders/${renderId}/download`}
          className="mt-3 flex items-center justify-center gap-2 rounded-lg bg-success/10 border border-success/20 px-4 py-2 text-sm font-medium text-success hover:bg-success/20 transition-all"
        >
          <Download className="h-4 w-4" />
          Descargar video
        </a>
      )}
    </GlassCard>
  )
}
