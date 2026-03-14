import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '@/api/client'
import { GlassCard } from '@/components/ui'
import { X, Sparkles, Video, Mic } from 'lucide-react'
import { motion } from 'framer-motion'

interface Client {
  id: string
  name: string
}

interface Template {
  id: string
  name: string
  slug: string
  description: string | null
  category: string
}

export function NewProjectModal({ onClose }: { onClose: () => void }) {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [title, setTitle] = useState('')
  const [brief, setBrief] = useState('')
  const [clientId, setClientId] = useState('')
  const [templateId, setTemplateId] = useState('')
  const [numMoments, setNumMoments] = useState(5)
  const [tone, setTone] = useState('profesional')
  const [generateVoiceover, setGenerateVoiceover] = useState(false)

  const { data: clients } = useQuery<Client[]>({
    queryKey: ['clients'],
    queryFn: async () => (await api.get('/clients')).data,
  })

  const { data: templates } = useQuery<Template[]>({
    queryKey: ['video-templates'],
    queryFn: async () => (await api.get('/content-engine/templates')).data,
  })

  const createProject = useMutation({
    mutationFn: async () => {
      // 1. Create project
      const { data: project } = await api.post('/content-engine/projects', {
        client_id: clientId,
        title,
        brief,
        template_id: templateId || undefined,
      })
      // 2. Generate moments with AI
      await api.post(`/content-engine/projects/${project.id}/generate-moments`, {
        brief,
        num_moments: numMoments,
        tone,
      })
      return project
    },
    onSuccess: (project) => {
      queryClient.invalidateQueries({ queryKey: ['video-projects'] })
      onClose()
      navigate(`/content/projects/${project.id}`)
    },
  })

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <motion.div
        className="fixed inset-0 bg-black/60 backdrop-blur-sm"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        onClick={onClose}
      />
      <motion.div
        className="relative z-10 w-full max-w-lg"
        initial={{ opacity: 0, scale: 0.95, y: 20 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
      >
        <GlassCard variant="strong" hover={false} className="!p-0 overflow-hidden">
          {/* Header */}
          <div className="flex items-center justify-between border-b border-border px-5 py-4">
            <div className="flex items-center gap-2">
              <Video className="h-5 w-5 text-vulkran-light" />
              <h2 className="text-lg font-semibold">Nuevo Video Project</h2>
            </div>
            <button
              onClick={onClose}
              className="rounded-lg p-1.5 text-muted-foreground hover:text-foreground hover:bg-surface-2 transition-all"
            >
              <X className="h-5 w-5" />
            </button>
          </div>

          {/* Form */}
          <div className="space-y-4 p-5">
            {/* Client */}
            <div>
              <label className="block text-sm font-medium text-foreground mb-1.5">Cliente</label>
              <select
                value={clientId}
                onChange={(e) => setClientId(e.target.value)}
                className="w-full rounded-lg border border-border bg-surface-1 px-3 py-2 text-sm text-foreground focus:border-vulkran focus:outline-none"
              >
                <option value="">Seleccionar cliente...</option>
                {clients?.map((c) => (
                  <option key={c.id} value={c.id}>{c.name}</option>
                ))}
              </select>
            </div>

            {/* Title */}
            <div>
              <label className="block text-sm font-medium text-foreground mb-1.5">Titulo</label>
              <input
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="Ej: Video presentacion Q1 2026"
                className="w-full rounded-lg border border-border bg-surface-1 px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:border-vulkran focus:outline-none"
              />
            </div>

            {/* Brief */}
            <div>
              <label className="block text-sm font-medium text-foreground mb-1.5">Brief creativo</label>
              <textarea
                value={brief}
                onChange={(e) => setBrief(e.target.value)}
                rows={3}
                placeholder="Describe el contenido del video: tema, audiencia, mensaje clave, estilo..."
                className="w-full rounded-lg border border-border bg-surface-1 px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:border-vulkran focus:outline-none resize-none"
              />
            </div>

            {/* Template + Moments row */}
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-sm font-medium text-foreground mb-1.5">Template</label>
                <select
                  value={templateId}
                  onChange={(e) => setTemplateId(e.target.value)}
                  className="w-full rounded-lg border border-border bg-surface-1 px-3 py-2 text-sm text-foreground focus:border-vulkran focus:outline-none"
                >
                  <option value="">Auto-detectar</option>
                  {templates?.map((t) => (
                    <option key={t.id} value={t.id}>{t.name}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-foreground mb-1.5">Momentos</label>
                <input
                  type="number"
                  value={numMoments}
                  onChange={(e) => setNumMoments(Number(e.target.value))}
                  min={2}
                  max={20}
                  className="w-full rounded-lg border border-border bg-surface-1 px-3 py-2 text-sm text-foreground focus:border-vulkran focus:outline-none"
                />
              </div>
            </div>

            {/* Tone + Voiceover row */}
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-sm font-medium text-foreground mb-1.5">Tono</label>
                <select
                  value={tone}
                  onChange={(e) => setTone(e.target.value)}
                  className="w-full rounded-lg border border-border bg-surface-1 px-3 py-2 text-sm text-foreground focus:border-vulkran focus:outline-none"
                >
                  <option value="profesional">Profesional</option>
                  <option value="casual">Casual</option>
                  <option value="energetico">Energetico</option>
                  <option value="inspirador">Inspirador</option>
                </select>
              </div>
              <div className="flex items-end">
                <label className="flex items-center gap-2 cursor-pointer rounded-lg border border-border bg-surface-1 px-3 py-2 w-full">
                  <input
                    type="checkbox"
                    checked={generateVoiceover}
                    onChange={(e) => setGenerateVoiceover(e.target.checked)}
                    className="accent-vulkran"
                  />
                  <Mic className="h-4 w-4 text-muted-foreground" />
                  <span className="text-sm text-foreground">Voiceover</span>
                </label>
              </div>
            </div>
          </div>

          {/* Footer */}
          <div className="flex items-center justify-end gap-3 border-t border-border px-5 py-4">
            <button
              onClick={onClose}
              className="rounded-lg px-4 py-2 text-sm font-medium text-muted-foreground hover:text-foreground transition-all"
            >
              Cancelar
            </button>
            <button
              onClick={() => createProject.mutate()}
              disabled={!clientId || !title || !brief || createProject.isPending}
              className="flex items-center gap-2 rounded-lg bg-vulkran px-4 py-2 text-sm font-medium text-white hover:bg-vulkran/90 transition-all shadow-lg shadow-vulkran/20 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {createProject.isPending ? (
                <div className="h-4 w-4 rounded-full border-2 border-white border-t-transparent animate-spin" />
              ) : (
                <Sparkles className="h-4 w-4" />
              )}
              {createProject.isPending ? 'Generando...' : 'Generar con AI'}
            </button>
          </div>
        </GlassCard>
      </motion.div>
    </div>
  )
}
