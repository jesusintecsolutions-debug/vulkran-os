import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/api/client'
import { GlassCard } from '@/components/ui'
import { SlotGroup } from './SlotEditors'
import {
  GripVertical,
  Trash2,
  ChevronDown,
  ChevronUp,
  Mic,
  Clock,
  Layers,
  Save,
  Loader2,
} from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'

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

interface MomentEditorProps {
  moment: Moment
  index: number
  templateSlots: SlotDef[]
  projectId: string
  onDelete?: () => void
}

const TRANSITION_TYPES = [
  { value: 'fade', label: 'Fade' },
  { value: 'slide', label: 'Slide' },
  { value: 'wipe', label: 'Wipe' },
  { value: 'flip', label: 'Flip' },
  { value: 'none', label: 'Sin transicion' },
]

const inputClass =
  'w-full rounded-lg border border-border bg-surface-1 px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:border-vulkran focus:outline-none transition-colors'

type Tab = 'content' | 'timing' | 'voiceover'

export function MomentEditor({ moment, index, templateSlots, projectId, onDelete }: MomentEditorProps) {
  const queryClient = useQueryClient()
  const [expanded, setExpanded] = useState(index === 0)
  const [activeTab, setActiveTab] = useState<Tab>('content')
  const [slotsData, setSlotsData] = useState<Record<string, unknown>>(moment.slots_data || {})
  const [durationFrames, setDurationFrames] = useState(moment.duration_frames)
  const [transitionType, setTransitionType] = useState(moment.transition_type || 'fade')
  const [transitionDuration, setTransitionDuration] = useState(moment.transition_duration || 15)
  const [voiceoverText, setVoiceoverText] = useState(moment.voiceover_text || '')
  const [isDirty, setDirty] = useState(false)

  const updateMoment = useMutation({
    mutationFn: async () => {
      await api.patch(`/content-engine/moments/${moment.id}`, {
        slots_data: slotsData,
        duration_frames: durationFrames,
        transition_type: transitionType,
        transition_duration: transitionDuration,
        voiceover_text: voiceoverText || null,
      })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['video-project', projectId] })
      setDirty(false)
    },
  })

  const deleteMoment = useMutation({
    mutationFn: async () => {
      await api.delete(`/content-engine/moments/${moment.id}`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['video-project', projectId] })
      onDelete?.()
    },
  })

  const handleSlotChange = (key: string, value: unknown) => {
    setSlotsData((prev) => ({ ...prev, [key]: value }))
    setDirty(true)
  }

  const handleSave = () => updateMoment.mutate()

  const durationSeconds = (durationFrames / 30).toFixed(1)
  const headline = (slotsData.headline as string) || (slotsData.title as string) || `Momento ${index + 1}`

  return (
    <GlassCard hover={false} className="!p-0 overflow-hidden">
      {/* Header — always visible */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex w-full items-center gap-3 px-4 py-3 text-left hover:bg-surface-2/30 transition-colors"
      >
        <GripVertical className="h-4 w-4 text-muted-foreground shrink-0 cursor-grab" />
        <span className="text-xs font-mono text-muted-foreground w-6 shrink-0">#{index + 1}</span>
        <span className="flex-1 truncate text-sm font-medium text-foreground">{headline}</span>
        <span className="text-xs text-muted-foreground shrink-0">{durationSeconds}s</span>
        <span className="text-xs text-muted-foreground shrink-0 capitalize">{transitionType}</span>
        {isDirty && <span className="h-2 w-2 rounded-full bg-warning shrink-0" />}
        {expanded ? (
          <ChevronUp className="h-4 w-4 text-muted-foreground shrink-0" />
        ) : (
          <ChevronDown className="h-4 w-4 text-muted-foreground shrink-0" />
        )}
      </button>

      {/* Expanded editor */}
      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="border-t border-border">
              {/* Tabs */}
              <div className="flex border-b border-border">
                {([
                  { key: 'content', label: 'Contenido', icon: Layers },
                  { key: 'timing', label: 'Timing', icon: Clock },
                  { key: 'voiceover', label: 'Voiceover', icon: Mic },
                ] as const).map((t) => (
                  <button
                    key={t.key}
                    onClick={() => setActiveTab(t.key)}
                    className={`flex items-center gap-1.5 px-4 py-2.5 text-xs font-medium transition-all border-b-2 ${
                      activeTab === t.key
                        ? 'border-vulkran text-foreground'
                        : 'border-transparent text-muted-foreground hover:text-foreground'
                    }`}
                  >
                    <t.icon className="h-3.5 w-3.5" />
                    {t.label}
                  </button>
                ))}
              </div>

              {/* Tab content */}
              <div className="p-4">
                {activeTab === 'content' && (
                  <SlotGroup slots={templateSlots} data={slotsData} onChange={handleSlotChange} />
                )}

                {activeTab === 'timing' && (
                  <div className="space-y-4">
                    <div>
                      <label className="mb-1.5 block text-xs font-medium text-muted-foreground">
                        Duracion (frames @ 30fps)
                      </label>
                      <div className="flex items-center gap-3">
                        <input
                          type="range"
                          min={30}
                          max={600}
                          step={15}
                          value={durationFrames}
                          onChange={(e) => {
                            setDurationFrames(Number(e.target.value))
                            setDirty(true)
                          }}
                          className="flex-1 accent-vulkran"
                        />
                        <span className="text-sm font-mono text-foreground w-16 text-right">
                          {durationFrames}f / {(durationFrames / 30).toFixed(1)}s
                        </span>
                      </div>
                    </div>

                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className="mb-1.5 block text-xs font-medium text-muted-foreground">
                          Transicion
                        </label>
                        <select
                          value={transitionType}
                          onChange={(e) => {
                            setTransitionType(e.target.value)
                            setDirty(true)
                          }}
                          className={inputClass}
                        >
                          {TRANSITION_TYPES.map((t) => (
                            <option key={t.value} value={t.value}>{t.label}</option>
                          ))}
                        </select>
                      </div>
                      <div>
                        <label className="mb-1.5 block text-xs font-medium text-muted-foreground">
                          Duracion transicion (frames)
                        </label>
                        <input
                          type="number"
                          value={transitionDuration}
                          onChange={(e) => {
                            setTransitionDuration(Number(e.target.value))
                            setDirty(true)
                          }}
                          min={0}
                          max={60}
                          className={inputClass}
                        />
                      </div>
                    </div>
                  </div>
                )}

                {activeTab === 'voiceover' && (
                  <div className="space-y-3">
                    <div>
                      <label className="mb-1.5 block text-xs font-medium text-muted-foreground">
                        Texto del voiceover
                      </label>
                      <textarea
                        value={voiceoverText}
                        onChange={(e) => {
                          setVoiceoverText(e.target.value)
                          setDirty(true)
                        }}
                        rows={3}
                        placeholder="Texto que se leera como voiceover para este momento..."
                        className={`${inputClass} resize-none`}
                      />
                    </div>
                    {moment.voiceover_url && (
                      <div className="flex items-center gap-2 rounded-lg bg-surface-1 border border-border p-3">
                        <Mic className="h-4 w-4 text-vulkran-light shrink-0" />
                        <span className="text-xs text-muted-foreground flex-1">Audio generado</span>
                        <audio controls src={moment.voiceover_url} className="h-8" />
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* Actions footer */}
              <div className="flex items-center justify-between border-t border-border px-4 py-3">
                <button
                  onClick={() => deleteMoment.mutate()}
                  disabled={deleteMoment.isPending}
                  className="flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium text-error hover:bg-error/10 transition-all disabled:opacity-50"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                  Eliminar
                </button>
                <button
                  onClick={handleSave}
                  disabled={!isDirty || updateMoment.isPending}
                  className="flex items-center gap-1.5 rounded-lg bg-vulkran px-4 py-1.5 text-xs font-medium text-white hover:bg-vulkran/90 transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-lg shadow-vulkran/20"
                >
                  {updateMoment.isPending ? (
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  ) : (
                    <Save className="h-3.5 w-3.5" />
                  )}
                  Guardar
                </button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </GlassCard>
  )
}
