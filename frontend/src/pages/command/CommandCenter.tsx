import { useState, useRef, useEffect, useCallback, Suspense } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Send, Loader2, Wrench, Bot, User,
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
  description: string
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
  { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard, path: '/dashboard', description: 'Vista general' },
  { id: 'clients', label: 'Clientes', icon: Users, path: '/clients', description: 'Gestión de clientes' },
  { id: 'content', label: 'Contenido', icon: FileText, path: '/content', description: 'Motor de contenido' },
  { id: 'leads', label: 'Leads', icon: Target, path: '/leads', description: 'Pipeline comercial' },
  { id: 'accounting', label: 'Contabilidad', icon: Receipt, path: '/accounting', description: 'Fiscal y finanzas' },
  { id: 'files', label: 'Archivos', icon: FolderOpen, path: '/files', description: 'Documentos' },
  { id: 'settings', label: 'Ajustes', icon: Settings, path: '/settings', description: 'Configuración' },
]

/* ─── Greeting ─── */
function getGreeting(name?: string): string {
  const hour = new Date().getHours()
  const n = name?.split(' ')[0] || ''
  if (hour < 7) return `Buenas noches, ${n}. ¿Trabajando a estas horas?`
  if (hour < 12) return `Buenos días, ${n}. ¿En qué te ayudo hoy?`
  if (hour < 14) return `Buenas tardes, ${n}. ¿Seguimos avanzando?`
  if (hour < 20) return `Buenas tardes, ${n}. ¿Qué necesitas?`
  return `Buenas noches, ${n}. ¿En qué puedo ayudarte?`
}

/* ─── Animated connection line (SVG) ─── */
function ConnectionLine({ x, y, revealed, delay }: { x: number; y: number; revealed: boolean; delay: number }) {
  const len = Math.sqrt(x * x + y * y)
  return (
    <motion.line
      x1="50%"
      y1="50%"
      x2={`calc(50% + ${x}px)`}
      y2={`calc(50% + ${y}px)`}
      stroke="url(#line-gradient)"
      strokeWidth="0.5"
      initial={{ pathLength: 0, opacity: 0 }}
      animate={{
        pathLength: revealed ? 1 : 0,
        opacity: revealed ? 0.3 : 0,
      }}
      transition={{ duration: 0.6, delay: revealed ? delay : 0 }}
      strokeDasharray={len}
    />
  )
}

/* ─── Radial module button ─── */
function RadialModule({
  module, index, total, revealed, radius, onNavigate,
}: {
  module: Module; index: number; total: number; revealed: boolean; radius: number; onNavigate: (p: string) => void
}) {
  const angle = (index / total) * Math.PI * 2 - Math.PI / 2
  const x = Math.cos(angle) * radius
  const y = Math.sin(angle) * radius
  const Icon = module.icon

  return (
    <motion.button
      className="absolute flex flex-col items-center gap-2 cursor-pointer group"
      style={{ left: `calc(50% + ${x}px)`, top: `calc(50% + ${y}px)`, transform: 'translate(-50%, -50%)' }}
      initial={{ opacity: 0, scale: 0.5 }}
      animate={{
        opacity: revealed ? 1 : 0,
        scale: revealed ? 1 : 0.5,
      }}
      transition={{ duration: 0.5, delay: revealed ? 0.15 + index * 0.06 : 0, ease: [0.34, 1.56, 0.64, 1] }}
      onClick={() => revealed && onNavigate(module.path)}
      whileHover={revealed ? { scale: 1.1 } : {}}
      whileTap={revealed ? { scale: 0.92 } : {}}
    >
      <div className={cn(
        'relative w-14 h-14 rounded-xl flex items-center justify-center transition-all duration-300',
        'border border-white/[0.06] bg-white/[0.03] backdrop-blur-md',
        'group-hover:border-[#00F0FF]/30 group-hover:bg-[#00F0FF]/[0.06]',
        'group-hover:shadow-[0_0_20px_rgba(0,240,255,0.15)]',
      )}>
        <Icon className="h-5 w-5 text-white/40 group-hover:text-[#00F0FF] transition-colors duration-300" />
        {/* Corner accents */}
        <div className="absolute top-0 left-0 w-2 h-2 border-t border-l border-white/[0.08] rounded-tl-lg group-hover:border-[#00F0FF]/30 transition-colors" />
        <div className="absolute bottom-0 right-0 w-2 h-2 border-b border-r border-white/[0.08] rounded-br-lg group-hover:border-[#00F0FF]/30 transition-colors" />
      </div>
      <div className="flex flex-col items-center gap-0.5">
        <span className="text-[11px] font-semibold tracking-wide text-white/50 group-hover:text-[#00F0FF]/90 transition-colors">
          {module.label}
        </span>
        <span className="text-[9px] text-white/20 group-hover:text-white/40 transition-colors hidden lg:block">
          {module.description}
        </span>
      </div>
    </motion.button>
  )
}

/* ─── Mobile module bar ─── */
function MobileModuleBar({ modules, revealed, onNavigate }: {
  modules: Module[]; revealed: boolean; onNavigate: (p: string) => void
}) {
  return (
    <motion.div
      className="md:hidden fixed bottom-16 left-0 right-0 z-20 flex justify-center px-4"
      initial={{ opacity: 0, y: 30 }}
      animate={{ opacity: revealed ? 1 : 0, y: revealed ? 0 : 30 }}
      transition={{ duration: 0.4 }}
    >
      <div className="flex gap-1 p-1.5 rounded-2xl border border-white/[0.06] bg-black/60 backdrop-blur-xl overflow-x-auto max-w-[92vw]">
        {modules.map((mod) => {
          const Icon = mod.icon
          return (
            <button
              key={mod.id}
              onClick={() => onNavigate(mod.path)}
              className="flex flex-col items-center gap-0.5 min-w-[52px] py-2 px-1 rounded-xl hover:bg-white/[0.04] active:bg-white/[0.08] transition-all"
            >
              <Icon className="h-5 w-5 text-white/40" />
              <span className="text-[9px] text-white/35 font-medium">{mod.label}</span>
            </button>
          )
        })}
      </div>
    </motion.div>
  )
}

/* ─── Message bubble ─── */
function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === 'user'

  return (
    <div className={cn('flex gap-2.5', isUser ? 'justify-end' : 'justify-start')}>
      {!isUser && (
        <div className="flex-shrink-0 h-6 w-6 rounded-md border border-[#00F0FF]/20 bg-[#00F0FF]/[0.05] flex items-center justify-center mt-0.5">
          <Bot className="h-3 w-3 text-[#00F0FF]/70" />
        </div>
      )}
      <div className={cn('max-w-[85%] space-y-1', isUser && 'order-first')}>
        {message.toolCalls && message.toolCalls.length > 0 && (
          <div className="space-y-0.5 mb-1">
            {message.toolCalls.map((tc, i) => (
              <div key={i} className="flex items-center gap-1.5 text-[10px] text-[#00F0FF]/40 font-mono">
                <Wrench className="h-2.5 w-2.5" />
                <span>{tc.name}</span>
                {message.toolResults?.[i] && <span className="text-emerald-400/60">ok</span>}
              </div>
            ))}
          </div>
        )}
        {(message.content || message.isStreaming) && (
          <div className={cn(
            'rounded-xl px-3.5 py-2.5 text-[13px] leading-relaxed',
            isUser
              ? 'bg-[#00F0FF]/[0.08] border border-[#00F0FF]/[0.12] text-white/90 rounded-br-md'
              : 'bg-white/[0.03] border border-white/[0.04] text-white/80 rounded-bl-md',
          )}>
            <div className="whitespace-pre-wrap">{message.content}</div>
            {message.isStreaming && !message.content && (
              <div className="flex items-center gap-1">
                <span className="h-1 w-1 rounded-full bg-[#00F0FF]/60 animate-bounce" style={{ animationDelay: '0ms' }} />
                <span className="h-1 w-1 rounded-full bg-[#00F0FF]/60 animate-bounce" style={{ animationDelay: '150ms' }} />
                <span className="h-1 w-1 rounded-full bg-[#00F0FF]/60 animate-bounce" style={{ animationDelay: '300ms' }} />
              </div>
            )}
            {message.isStreaming && message.content && (
              <span className="inline-block w-[2px] h-3.5 bg-[#00F0FF]/70 ml-0.5 animate-pulse rounded-full" />
            )}
          </div>
        )}
      </div>
      {isUser && (
        <div className="flex-shrink-0 h-6 w-6 rounded-md bg-white/[0.04] border border-white/[0.06] flex items-center justify-center mt-0.5">
          <User className="h-3 w-3 text-white/40" />
        </div>
      )}
    </div>
  )
}

/* ─── Chat Panel ─── */
function ChatPanel({
  active, greeting, messages, input, setInput, isStreaming, onSend, onClose, setBrainState,
}: {
  active: boolean; greeting: string; messages: ChatMessage[]; input: string
  setInput: (v: string) => void; isStreaming: boolean; onSend: () => void
  onClose: () => void; setBrainState: (s: BrainState) => void
}) {
  const bottomRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages])
  useEffect(() => { if (active) inputRef.current?.focus() }, [active])

  // ESC to close chat
  useEffect(() => {
    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && active) {
        e.preventDefault()
        onClose()
      }
    }
    window.addEventListener('keydown', handleEsc)
    return () => window.removeEventListener('keydown', handleEsc)
  }, [active, onClose])

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
      {/* Messages */}
      <AnimatePresence>
        {messages.length > 0 && (
          <motion.div
            className="max-w-2xl mx-auto px-4 mb-3 max-h-[50vh] overflow-y-auto"
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
          >
            <div className="bg-black/40 backdrop-blur-xl border border-white/[0.05] rounded-2xl p-4 space-y-3">
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
          <motion.p
            className="text-center mb-4 text-[13px] text-white/40 font-light tracking-wide"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ delay: 0.2 }}
          >
            {greeting}
          </motion.p>
        )}
      </AnimatePresence>

      {/* Input bar */}
      <div className="bg-black/50 backdrop-blur-xl border-t border-white/[0.04] px-4 py-3 safe-area-bottom">
        <div className="max-w-2xl mx-auto">
          <div className="flex items-end gap-2.5 rounded-xl border border-white/[0.06] bg-white/[0.02] p-1.5">
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => {
                setInput(e.target.value)
                setBrainState(e.target.value ? 'typing' : 'idle')
              }}
              onKeyDown={handleKeyDown}
              placeholder="Habla con VULKRAN..."
              className="flex-1 resize-none bg-transparent text-white/90 text-[13px] placeholder:text-white/20 focus:outline-none min-h-[38px] max-h-32 px-3 py-2"
              rows={1}
              disabled={!active || isStreaming}
            />
            <button
              onClick={onSend}
              disabled={!input.trim() || isStreaming || !active}
              className={cn(
                'shrink-0 h-9 w-9 rounded-lg flex items-center justify-center transition-all duration-200',
                input.trim() && active
                  ? 'bg-[#00F0FF] text-black shadow-[0_0_16px_rgba(0,240,255,0.3)] hover:shadow-[0_0_24px_rgba(0,240,255,0.5)]'
                  : 'bg-white/[0.04] text-white/20',
              )}
            >
              {isStreaming ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
            </button>
          </div>
          {active && (
            <p className="text-center mt-2 text-[10px] text-white/15 tracking-wider hidden md:block">
              ESC para cerrar · ENTER para enviar
            </p>
          )}
        </div>
      </div>
    </motion.div>
  )
}

/* ─── HUD status indicators ─── */
function HUDIndicators({ state }: { state: BrainState }) {
  return (
    <div className="absolute bottom-8 left-1/2 -translate-x-1/2 flex items-center gap-6 pointer-events-none">
      <div className="flex items-center gap-2">
        <div className={cn(
          'h-1.5 w-1.5 rounded-full transition-colors duration-500',
          state === 'idle' ? 'bg-[#00F0FF]/30' : 'bg-[#00F0FF] shadow-[0_0_8px_rgba(0,240,255,0.5)]',
        )} />
        <span className="text-[10px] text-white/20 font-mono tracking-wider uppercase">
          {state === 'idle' ? 'standby' : state === 'thinking' ? 'processing' : state === 'responding' ? 'transmitting' : state}
        </span>
      </div>
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

  const fadeTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const longPressTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const isLongPressing = useRef(false)

  const modulesRevealed = uiState === 'COMMAND_CENTER'
  const chatActive = uiState === 'CHAT_ACTIVE' || uiState === 'COMMAND_CENTER'

  // Responsive radius
  const [radius, setRadius] = useState(180)
  useEffect(() => {
    const update = () => setRadius(window.innerWidth < 768 ? 0 : Math.min(300, window.innerWidth * 0.24))
    update()
    window.addEventListener('resize', update)
    return () => window.removeEventListener('resize', update)
  }, [])

  // Fade-back timer
  const startFadeTimer = useCallback(() => {
    if (fadeTimerRef.current) clearTimeout(fadeTimerRef.current)
    fadeTimerRef.current = setTimeout(() => {
      if (!isStreaming) setUIState('FADE_BACK')
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

  // Close chat (ESC)
  const handleCloseChat = useCallback(() => {
    if (isStreaming) return
    setBrainState('idle')
    setUIState('DORMANT')
  }, [isStreaming])

  // Long-press to reveal modules
  const handlePointerDown = useCallback((e: React.PointerEvent) => {
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

  // Wheel rotates modules
  useEffect(() => {
    if (!modulesRevealed) return
    const handleWheel = (e: WheelEvent) => startFadeTimer()
    window.addEventListener('wheel', handleWheel, { passive: true })
    return () => window.removeEventListener('wheel', handleWheel)
  }, [modulesRevealed, startFadeTimer])

  const handleNavigate = useCallback((path: string) => navigate(path), [navigate])

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
          } catch { /* skip malformed */ }
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

  useEffect(() => {
    return () => {
      if (fadeTimerRef.current) clearTimeout(fadeTimerRef.current)
      if (longPressTimerRef.current) clearTimeout(longPressTimerRef.current)
    }
  }, [])

  return (
    <div
      className="fixed inset-0 bg-black overflow-hidden select-none"
      onPointerDown={handlePointerDown}
      onPointerUp={handlePointerUp}
      onPointerCancel={handlePointerUp}
    >
      {/* Subtle radial gradient background */}
      <div className="absolute inset-0 pointer-events-none">
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] rounded-full bg-[#00F0FF]/[0.015] blur-[120px]" />
        <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-white/[0.04] to-transparent" />
      </div>

      {/* Grid overlay — very subtle */}
      <div
        className="absolute inset-0 pointer-events-none opacity-[0.015]"
        style={{
          backgroundImage: `
            linear-gradient(rgba(0,240,255,0.3) 1px, transparent 1px),
            linear-gradient(90deg, rgba(0,240,255,0.3) 1px, transparent 1px)
          `,
          backgroundSize: '60px 60px',
        }}
      />

      {/* Top bar */}
      <header className="relative z-10 flex items-center justify-between px-6 py-5">
        <div className="flex items-center gap-2.5">
          <div className="h-2 w-2 rounded-full bg-[#00F0FF]/40 shadow-[0_0_8px_rgba(0,240,255,0.3)]" />
          <span className="text-[13px] font-semibold tracking-[0.25em] text-white/50">VULKRAN</span>
          <span className="text-[9px] font-medium text-white/15 tracking-[0.3em] mt-px">OS</span>
        </div>
        <div className="flex items-center gap-4">
          <span className="text-[11px] text-white/20 font-mono hidden md:block">{user?.name}</span>
          <button
            onClick={logout}
            className="text-[10px] text-white/15 hover:text-white/40 transition-colors tracking-[0.15em] uppercase font-medium"
          >
            Salir
          </button>
        </div>
      </header>

      {/* Connection lines SVG (desktop) */}
      <svg className="absolute inset-0 w-full h-full pointer-events-none hidden md:block" style={{ top: '-5%' }}>
        <defs>
          <linearGradient id="line-gradient" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#00F0FF" stopOpacity="0.05" />
            <stop offset="50%" stopColor="#00F0FF" stopOpacity="0.15" />
            <stop offset="100%" stopColor="#00F0FF" stopOpacity="0.05" />
          </linearGradient>
        </defs>
        {MODULES.map((_, i) => {
          const angle = (i / MODULES.length) * Math.PI * 2 - Math.PI / 2
          return (
            <ConnectionLine
              key={i}
              x={Math.cos(angle) * radius}
              y={Math.sin(angle) * radius}
              revealed={modulesRevealed}
              delay={i * 0.05}
            />
          )
        })}
      </svg>

      {/* Brain — center (z-0 so modules can be above) */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-[55%] z-0" data-brain>
        <Suspense
          fallback={
            <div className="h-[22rem] w-[22rem] md:h-[26rem] md:w-[26rem] flex items-center justify-center">
              <div className="h-16 w-16 rounded-full border border-[#00F0FF]/20 flex items-center justify-center animate-pulse">
                <div className="h-8 w-8 rounded-full border border-[#00F0FF]/10 animate-ping" />
              </div>
            </div>
          }
        >
          <HoloBrain
            state={brainState}
            size="xl"
            onClick={handleBrainClick}
            className={cn(
              'transition-all duration-700',
              uiState === 'DORMANT' && 'opacity-80 hover:opacity-100',
              brainState === 'activating' && 'scale-105',
            )}
          />
        </Suspense>

        {/* Dormant hint */}
        <AnimatePresence>
          {uiState === 'DORMANT' && (
            <motion.div
              className="absolute -bottom-10 left-1/2 -translate-x-1/2 flex flex-col items-center gap-2"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ delay: 1.5, duration: 0.8 }}
            >
              <div className="flex items-center gap-3">
                <div className="h-px w-8 bg-gradient-to-r from-transparent to-white/10" />
                <span className="text-[10px] text-white/20 tracking-[0.3em] font-light">
                  TOCA PARA ACTIVAR
                </span>
                <div className="h-px w-8 bg-gradient-to-l from-transparent to-white/10" />
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Radial modules (desktop) — z-20 to stay above brain canvas */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-[55%] hidden md:block pointer-events-none z-20">
        <div className="pointer-events-auto">
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
      </div>

      {/* Mobile module bar */}
      <MobileModuleBar modules={MODULES} revealed={modulesRevealed} onNavigate={handleNavigate} />

      {/* HUD indicators */}
      <AnimatePresence>
        {chatActive && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          >
            <HUDIndicators state={brainState} />
          </motion.div>
        )}
      </AnimatePresence>

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
          onClose={handleCloseChat}
          setBrainState={setBrainState}
        />
      </div>

      {/* Long-press hint */}
      <AnimatePresence>
        {chatActive && !modulesRevealed && messages.length === 0 && (
          <motion.p
            className="fixed bottom-24 left-1/2 -translate-x-1/2 text-[9px] text-white/10 tracking-[0.2em] z-10 hidden md:block"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ delay: 4 }}
          >
            MANTÉN PULSADO PARA REVELAR MÓDULOS
          </motion.p>
        )}
      </AnimatePresence>
    </div>
  )
}
