import { useState, useRef, useEffect, useCallback, Suspense } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Send, Loader2, Sparkles, Wrench, Bot, User,
  LayoutDashboard, Users, FileText, Target, Receipt, FolderOpen, Settings,
  type LucideIcon,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { useAuthStore } from '@/stores/auth'
import { HoloBrain, type BrainState } from '@/components/HoloBrain'

const API_BASE = import.meta.env.VITE_API_URL || ''

/* ─── Types ─── */
type UIState = 'DORMANT' | 'CHAT_ACTIVE' | 'COMMAND_CENTER' | 'FADE_BACK'

interface Module {
  id: string
  label: string
  icon: LucideIcon
  path: string
  color: string
}

interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  toolCalls?: { name: string; input: Record<string, unknown> }[]
  toolResults?: { name: string; result: unknown }[]
  isStreaming?: boolean
}

/* ─── Module definitions ─── */
const MODULES: Module[] = [
  { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard, path: '/dashboard', color: '#00F0FF' },
  { id: 'clients', label: 'Clientes', icon: Users, path: '/clients', color: '#00D4E0' },
  { id: 'content', label: 'Contenido', icon: FileText, path: '/content', color: '#00B8C8' },
  { id: 'leads', label: 'Leads', icon: Target, path: '/leads', color: '#00F0FF' },
  { id: 'accounting', label: 'Contabilidad', icon: Receipt, path: '/accounting', color: '#00D4E0' },
  { id: 'files', label: 'Archivos', icon: FolderOpen, path: '/files', color: '#00B8C8' },
  { id: 'settings', label: 'Ajustes', icon: Settings, path: '/settings', color: '#00A0B0' },
]

/* ─── Greeting generator ─── */
function getGreeting(name?: string): string {
  const hour = new Date().getHours()
  const displayName = name?.split(' ')[0] || ''

  if (hour < 7) return `Buenas noches, ${displayName}. ¿Trabajando a estas horas?`
  if (hour < 12) return `Buenos días, ${displayName}. ¿En qué te ayudo hoy?`
  if (hour < 14) return `Buenas tardes, ${displayName}. ¿Seguimos avanzando?`
  if (hour < 20) return `Buenas tardes, ${displayName}. ¿Qué necesitas?`
  return `Buenas noches, ${displayName}. ¿En qué puedo ayudarte?`
}

/* ─── Radial module button ─── */
function RadialModule({
  module,
  index,
  total,
  revealed,
  radius,
  onNavigate,
}: {
  module: Module
  index: number
  total: number
  revealed: boolean
  radius: number
  onNavigate: (path: string) => void
}) {
  const angle = (index / total) * Math.PI * 2 - Math.PI / 2
  const x = Math.cos(angle) * radius
  const y = Math.sin(angle) * radius
  const Icon = module.icon

  return (
    <motion.button
      className="absolute flex flex-col items-center gap-1.5 cursor-pointer group"
      style={{ left: `calc(50% + ${x}px)`, top: `calc(50% + ${y}px)`, transform: 'translate(-50%, -50%)' }}
      initial={{ opacity: 0.06, scale: 0.7, filter: 'blur(6px)' }}
      animate={{
        opacity: revealed ? 1 : 0.06,
        scale: revealed ? 1 : 0.7,
        filter: revealed ? 'blur(0px)' : 'blur(6px)',
      }}
      transition={{ duration: 0.4, delay: revealed ? index * 0.08 : 0 }}
      onClick={() => revealed && onNavigate(module.path)}
      whileHover={revealed ? { scale: 1.12 } : {}}
      whileTap={revealed ? { scale: 0.95 } : {}}
    >
      {/* Connection line to center */}
      <svg
        className="absolute pointer-events-none"
        style={{
          left: '50%',
          top: '50%',
          width: `${Math.abs(x) + 4}px`,
          height: `${Math.abs(y) + 4}px`,
          transform: `translate(${x > 0 ? '-100%' : '0'}, ${y > 0 ? '-100%' : '0'})`,
        }}
      >
        <line
          x1={x > 0 ? '100%' : '0'}
          y1={y > 0 ? '100%' : '0'}
          x2={x > 0 ? '0' : '100%'}
          y2={y > 0 ? '0' : '100%'}
          stroke="rgba(0, 240, 255, 0.08)"
          strokeWidth="1"
        />
      </svg>

      {/* Icon container */}
      <div className={cn(
        'relative w-12 h-12 rounded-lg flex items-center justify-center transition-all duration-300',
        'glass group-hover:neon-border group-hover:glow-sm',
      )}>
        <Icon className="h-5 w-5 text-neon-cyan/70 group-hover:text-neon-cyan transition-colors" />
      </div>

      {/* Label (desktop only) */}
      <span className={cn(
        'text-[10px] font-medium tracking-wider uppercase transition-all duration-300 hidden md:block',
        revealed ? 'text-foreground/60 group-hover:text-neon-cyan' : 'text-transparent',
      )}>
        {module.label}
      </span>
    </motion.button>
  )
}

/* ─── Connection lines from brain to modules (canvas) ─── */
function ConnectionLines({ revealed, radius, moduleCount }: { revealed: boolean; radius: number; moduleCount: number }) {
  const canvasRef = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const dpr = window.devicePixelRatio || 1
    const rect = canvas.getBoundingClientRect()
    canvas.width = rect.width * dpr
    canvas.height = rect.height * dpr
    ctx.scale(dpr, dpr)

    ctx.clearRect(0, 0, rect.width, rect.height)
    const cx = rect.width / 2
    const cy = rect.height / 2

    ctx.strokeStyle = `rgba(0, 240, 255, ${revealed ? 0.12 : 0.03})`
    ctx.lineWidth = 1

    for (let i = 0; i < moduleCount; i++) {
      const angle = (i / moduleCount) * Math.PI * 2 - Math.PI / 2
      const x = cx + Math.cos(angle) * radius
      const y = cy + Math.sin(angle) * radius

      ctx.beginPath()
      ctx.moveTo(cx, cy)
      ctx.lineTo(x, y)
      ctx.stroke()
    }
  }, [revealed, radius, moduleCount])

  return (
    <canvas
      ref={canvasRef}
      className="absolute inset-0 w-full h-full pointer-events-none"
      style={{ opacity: revealed ? 1 : 0.3, transition: 'opacity 0.5s' }}
    />
  )
}

/* ─── Mobile module ring ─── */
function MobileModuleRing({
  modules,
  revealed,
  onNavigate,
}: {
  modules: Module[]
  revealed: boolean
  onNavigate: (path: string) => void
}) {
  return (
    <motion.div
      className="md:hidden fixed bottom-16 left-0 right-0 z-20 flex justify-center"
      initial={{ opacity: 0, y: 40 }}
      animate={{ opacity: revealed ? 1 : 0, y: revealed ? 0 : 40 }}
      transition={{ duration: 0.3 }}
    >
      <div className="flex gap-3 px-4 py-2 glass-strong rounded-2xl overflow-x-auto max-w-[90vw] scrollbar-hide">
        {modules.map((mod) => {
          const Icon = mod.icon
          return (
            <button
              key={mod.id}
              onClick={() => onNavigate(mod.path)}
              className="flex flex-col items-center gap-1 min-w-[48px] py-1.5 rounded-lg hover:bg-surface-2 transition-all"
            >
              <Icon className="h-5 w-5 text-neon-cyan/70" />
              <span className="text-[9px] text-foreground/50 font-medium">{mod.label}</span>
            </button>
          )
        })}
      </div>
    </motion.div>
  )
}

/* ─── Chat Panel ─── */
function ChatPanel({
  active,
  greeting,
  messages,
  input,
  setInput,
  isStreaming,
  onSend,
  setBrainState,
}: {
  active: boolean
  greeting: string
  messages: ChatMessage[]
  input: string
  setInput: (v: string) => void
  isStreaming: boolean
  onSend: () => void
  setBrainState: (s: BrainState) => void
}) {
  const bottomRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  useEffect(() => {
    if (active) inputRef.current?.focus()
  }, [active])

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      onSend()
    }
  }

  return (
    <motion.div
      className="fixed bottom-0 left-0 right-0 z-30"
      initial={{ y: 100, opacity: 0 }}
      animate={{ y: active ? 0 : 100, opacity: active ? 1 : 0 }}
      transition={{ type: 'spring', stiffness: 300, damping: 30 }}
    >
      {/* Messages area (only when there are messages) */}
      <AnimatePresence>
        {messages.length > 0 && (
          <motion.div
            className="max-w-2xl mx-auto px-4 mb-2 max-h-[50vh] overflow-y-auto"
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
          >
            <div className="glass-strong rounded-xl p-4 space-y-4">
              {messages.map((msg) => (
                <MessageBubble key={msg.id} message={msg} />
              ))}
              <div ref={bottomRef} />
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Greeting */}
      <AnimatePresence>
        {messages.length === 0 && active && (
          <motion.div
            className="text-center mb-3"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ delay: 0.2 }}
          >
            <p className="text-sm text-holo-subtle text-foreground/70">{greeting}</p>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Input bar */}
      <div className="glass-strong safe-area-bottom px-4 py-3">
        <div className="max-w-2xl mx-auto">
          <div className="flex items-end gap-2 glass rounded-xl p-2">
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => {
                setInput(e.target.value)
                setBrainState(e.target.value ? 'typing' : 'idle')
              }}
              onKeyDown={handleKeyDown}
              placeholder={active ? 'Escribe un mensaje a VULKRAN...' : 'Pulsa el cerebro para activar'}
              className="flex-1 resize-none bg-transparent text-foreground text-sm placeholder:text-muted-foreground focus:outline-none min-h-[40px] max-h-32 px-3 py-2"
              rows={1}
              disabled={!active || isStreaming}
            />
            <button
              onClick={onSend}
              disabled={!input.trim() || isStreaming || !active}
              className={cn(
                'shrink-0 h-9 w-9 rounded-lg flex items-center justify-center transition-all',
                input.trim() && active
                  ? 'bg-neon-cyan text-black hover:glow-sm'
                  : 'bg-surface-2 text-muted-foreground',
              )}
            >
              {isStreaming ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
            </button>
          </div>
        </div>
      </div>
    </motion.div>
  )
}

/* ─── Message bubble ─── */
function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === 'user'

  return (
    <div className={cn('flex gap-3', isUser ? 'justify-end' : 'justify-start')}>
      {!isUser && (
        <div className="flex-shrink-0 h-7 w-7 rounded-md neon-border flex items-center justify-center">
          <Bot className="h-3.5 w-3.5 text-neon-cyan" />
        </div>
      )}
      <div className={cn('max-w-[80%] space-y-1.5', isUser && 'order-first')}>
        {message.toolCalls && message.toolCalls.length > 0 && (
          <div className="space-y-0.5">
            {message.toolCalls.map((tc, i) => (
              <div key={i} className="flex items-center gap-1.5 text-[11px] text-neon-cyan/50">
                <Wrench className="h-3 w-3" />
                <span className="font-mono">{tc.name}</span>
                {message.toolResults?.[i] && <span className="text-success/70">✓</span>}
              </div>
            ))}
          </div>
        )}
        {(message.content || message.isStreaming) && (
          <div className={cn(
            'rounded-lg px-3 py-2 text-sm leading-relaxed',
            isUser
              ? 'bg-neon-cyan/10 border border-neon-cyan/20 text-foreground rounded-br-sm'
              : 'glass rounded-bl-sm text-foreground',
          )}>
            <div className="whitespace-pre-wrap">{message.content}</div>
            {message.isStreaming && !message.content && (
              <div className="flex items-center gap-1.5">
                <span className="h-1.5 w-1.5 rounded-full bg-neon-cyan animate-bounce" style={{ animationDelay: '0ms' }} />
                <span className="h-1.5 w-1.5 rounded-full bg-neon-cyan animate-bounce" style={{ animationDelay: '150ms' }} />
                <span className="h-1.5 w-1.5 rounded-full bg-neon-cyan animate-bounce" style={{ animationDelay: '300ms' }} />
              </div>
            )}
            {message.isStreaming && message.content && (
              <span className="inline-block w-1.5 h-4 bg-neon-cyan ml-0.5 animate-pulse rounded-full" />
            )}
          </div>
        )}
      </div>
      {isUser && (
        <div className="flex-shrink-0 h-7 w-7 rounded-md bg-surface-2 flex items-center justify-center">
          <User className="h-3.5 w-3.5 text-muted-foreground" />
        </div>
      )}
    </div>
  )
}

/* ─── Main CommandCenter ─── */
export default function CommandCenter() {
  const navigate = useNavigate()
  const { user, logout } = useAuthStore()

  const [uiState, setUIState] = useState<UIState>('DORMANT')
  const [brainState, setBrainState] = useState<BrainState>('idle')
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [conversationId, setConversationId] = useState<string | null>(null)
  const [isStreaming, setIsStreaming] = useState(false)
  const [greeting, setGreeting] = useState('')
  const [moduleRotation, setModuleRotation] = useState(0)

  const fadeTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const longPressTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const isLongPressing = useRef(false)

  const modulesRevealed = uiState === 'COMMAND_CENTER'
  const chatActive = uiState === 'CHAT_ACTIVE' || uiState === 'COMMAND_CENTER'

  // Responsive radius
  const [radius, setRadius] = useState(180)
  useEffect(() => {
    const update = () => setRadius(window.innerWidth < 768 ? 0 : Math.min(220, window.innerWidth * 0.18))
    update()
    window.addEventListener('resize', update)
    return () => window.removeEventListener('resize', update)
  }, [])

  // Fade-back timer
  const startFadeTimer = useCallback(() => {
    if (fadeTimerRef.current) clearTimeout(fadeTimerRef.current)
    fadeTimerRef.current = setTimeout(() => {
      if (!isStreaming) setUIState('FADE_BACK')
      // After fade, go back to dormant
      setTimeout(() => setUIState((s) => s === 'FADE_BACK' ? 'DORMANT' : s), 1000)
    }, 8000)
  }, [isStreaming])

  // Brain click → activate chat
  const handleBrainClick = useCallback(() => {
    if (uiState === 'DORMANT') {
      setGreeting(getGreeting(user?.name))
      setBrainState('activating')
      setUIState('CHAT_ACTIVE')
      setTimeout(() => setBrainState('idle'), 800)
    }
  }, [uiState, user?.name])

  // Long-press to reveal modules
  const handlePointerDown = useCallback((e: React.PointerEvent) => {
    // Ignore if clicking on brain, chat, or interactive elements
    const target = e.target as HTMLElement
    if (target.closest('[data-brain]') || target.closest('[data-chat]') || target.closest('button') || target.closest('textarea')) return

    isLongPressing.current = true
    longPressTimerRef.current = setTimeout(() => {
      if (isLongPressing.current) {
        setUIState('COMMAND_CENTER')
        startFadeTimer()
      }
    }, 600)
  }, [startFadeTimer])

  const handlePointerUp = useCallback(() => {
    isLongPressing.current = false
    if (longPressTimerRef.current) clearTimeout(longPressTimerRef.current)
  }, [])

  // Mouse wheel rotates modules (desktop only)
  useEffect(() => {
    if (!modulesRevealed) return
    const handleWheel = (e: WheelEvent) => {
      setModuleRotation((prev) => prev + e.deltaY * 0.05)
      // Reset fade timer on interaction
      startFadeTimer()
    }
    window.addEventListener('wheel', handleWheel, { passive: true })
    return () => window.removeEventListener('wheel', handleWheel)
  }, [modulesRevealed, startFadeTimer])

  // Navigate to module
  const handleNavigate = useCallback((path: string) => {
    navigate(path)
  }, [navigate])

  // Send message (SSE streaming)
  const sendMessage = useCallback(async () => {
    const text = input.trim()
    if (!text || isStreaming) return

    const userMsg: ChatMessage = { id: crypto.randomUUID(), role: 'user', content: text }
    setMessages((prev) => [...prev, userMsg])
    setInput('')
    setIsStreaming(true)
    setBrainState('thinking')

    const assistantId = crypto.randomUUID()
    setMessages((prev) => [
      ...prev,
      { id: assistantId, role: 'assistant', content: '', isStreaming: true, toolCalls: [], toolResults: [] },
    ])

    try {
      const token = localStorage.getItem('access_token')
      const response = await fetch(`${API_BASE}/api/agent/chat/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ message: text, conversation_id: conversationId }),
      })

      if (!response.ok) throw new Error(`HTTP ${response.status}`)
      if (!response.body) throw new Error('No response body')

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          try {
            const event = JSON.parse(line.slice(6))
            if (event.type === 'text_delta') {
              setBrainState('responding')
              setMessages((prev) =>
                prev.map((m) => m.id === assistantId ? { ...m, content: m.content + event.text } : m),
              )
            } else if (event.type === 'tool_call') {
              setBrainState('thinking')
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === assistantId
                    ? { ...m, toolCalls: [...(m.toolCalls || []), { name: event.name, input: event.input }] }
                    : m,
                ),
              )
            } else if (event.type === 'tool_result') {
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === assistantId
                    ? { ...m, toolResults: [...(m.toolResults || []), { name: event.name, result: event.result }] }
                    : m,
                ),
              )
            } else if (event.type === 'done') {
              setConversationId(event.conversation_id)
            } else if (event.type === 'error') {
              setMessages((prev) =>
                prev.map((m) => m.id === assistantId ? { ...m, content: `Error: ${event.message}` } : m),
              )
            }
          } catch { /* skip malformed JSON */ }
        }
      }
    } catch (err) {
      setMessages((prev) =>
        prev.map((m) => m.id === assistantId ? { ...m, content: `Error de conexión: ${err}` } : m),
      )
    } finally {
      setMessages((prev) => prev.map((m) => m.id === assistantId ? { ...m, isStreaming: false } : m))
      setIsStreaming(false)
      setBrainState('idle')
    }
  }, [input, isStreaming, conversationId])

  // Cleanup timers
  useEffect(() => {
    return () => {
      if (fadeTimerRef.current) clearTimeout(fadeTimerRef.current)
      if (longPressTimerRef.current) clearTimeout(longPressTimerRef.current)
    }
  }, [])

  return (
    <div
      className="fixed inset-0 bg-background overflow-hidden select-none"
      onPointerDown={handlePointerDown}
      onPointerUp={handlePointerUp}
      onPointerCancel={handlePointerUp}
    >
      {/* Ambient background effects */}
      <div className="absolute inset-0 pointer-events-none">
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] rounded-full bg-neon-cyan/[0.02] blur-3xl" />
        <div className="absolute top-1/4 right-1/4 w-96 h-96 rounded-full bg-vulkran/[0.015] blur-3xl" />
      </div>

      {/* Top bar — minimal */}
      <header className="relative z-10 flex items-center justify-between px-6 py-4">
        <div className="flex items-center gap-2">
          <Sparkles className="h-4 w-4 text-neon-cyan/60" />
          <span className="text-sm font-bold tracking-[0.2em] text-holo text-foreground/70">VULKRAN</span>
          <span className="text-[9px] font-semibold text-neon-cyan/30 tracking-widest mt-0.5">OS</span>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-xs text-muted-foreground hidden md:block">{user?.name}</span>
          <button
            onClick={logout}
            className="text-[11px] text-muted-foreground/50 hover:text-foreground/70 transition-colors tracking-wider uppercase"
          >
            Salir
          </button>
        </div>
      </header>

      {/* Connection lines */}
      <div className="absolute inset-0 hidden md:block">
        <ConnectionLines revealed={modulesRevealed} radius={radius} moduleCount={MODULES.length} />
      </div>

      {/* Brain — center */}
      <div
        className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-[55%] z-10"
        data-brain
      >
        <Suspense
          fallback={
            <div className="h-72 w-72 md:h-80 md:w-80 flex items-center justify-center">
              <Sparkles className="h-12 w-12 text-neon-cyan animate-pulse" />
            </div>
          }
        >
          <HoloBrain
            state={brainState}
            size="xl"
            onClick={handleBrainClick}
            className={cn(
              'transition-all duration-500',
              uiState === 'DORMANT' && 'opacity-80 hover:opacity-100',
              brainState === 'activating' && 'scale-110',
            )}
          />
        </Suspense>

        {/* Dormant hint */}
        <AnimatePresence>
          {uiState === 'DORMANT' && (
            <motion.p
              className="absolute -bottom-8 left-1/2 -translate-x-1/2 text-[11px] text-muted-foreground/40 whitespace-nowrap tracking-wider"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ delay: 1 }}
            >
              PULSA PARA ACTIVAR
            </motion.p>
          )}
        </AnimatePresence>
      </div>

      {/* Radial modules (desktop) */}
      <div
        className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-[55%] hidden md:block"
        style={{ transform: `translate(-50%, -55%) rotate(${moduleRotation}deg)` }}
      >
        {MODULES.map((mod, i) => (
          <RadialModule
            key={mod.id}
            module={mod}
            index={i}
            total={MODULES.length}
            revealed={modulesRevealed}
            radius={radius}
            onNavigate={handleNavigate}
          />
        ))}
      </div>

      {/* Mobile module ring */}
      <MobileModuleRing
        modules={MODULES}
        revealed={modulesRevealed}
        onNavigate={handleNavigate}
      />

      {/* Chat panel */}
      <div data-chat>
        <ChatPanel
          active={chatActive}
          greeting={greeting}
          messages={messages}
          input={input}
          setInput={setInput}
          isStreaming={isStreaming}
          onSend={sendMessage}
          setBrainState={setBrainState}
        />
      </div>

      {/* Long-press hint */}
      <AnimatePresence>
        {chatActive && !modulesRevealed && (
          <motion.p
            className="fixed bottom-20 left-1/2 -translate-x-1/2 text-[10px] text-muted-foreground/30 tracking-wider z-10"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ delay: 3 }}
          >
            MANTÉN PULSADO PARA REVELAR MÓDULOS
          </motion.p>
        )}
      </AnimatePresence>
    </div>
  )
}
