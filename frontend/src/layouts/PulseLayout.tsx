import { useState, useRef, useEffect, useCallback, Suspense, lazy } from 'react'
import { Outlet, useNavigate, useLocation } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Send, Loader2, Wrench, Bot, User,
  LayoutDashboard, Users, FileText, Target, Receipt, FolderOpen, Settings, Newspaper,
  ArrowLeft, Search, LogOut,
  type LucideIcon,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { useAuthStore } from '@/stores/auth'
import { HoloBrain, type BrainState } from '@/components/HoloBrain'

const GlassCarousel = lazy(() => import('@/components/ui/GlassCarousel'))
const CommandPalette = lazy(() => import('@/components/ui/CommandPalette'))

const API_BASE = import.meta.env.VITE_API_URL || ''

/* ─── Types ─── */
interface Module {
  id: string
  label: string
  icon: LucideIcon
  path: string
  description: string
  accent?: string
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
  { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard, path: '/dashboard', description: 'Vista general', accent: '#00F0FF' },
  { id: 'clients', label: 'Clientes', icon: Users, path: '/clients', description: 'Gestión de clientes', accent: '#8B5CF6' },
  { id: 'content', label: 'Contenido', icon: FileText, path: '/content', description: 'Motor de contenido', accent: '#00FF94' },
  { id: 'leads', label: 'Leads', icon: Target, path: '/leads', description: 'Pipeline comercial', accent: '#FFB800' },
  { id: 'accounting', label: 'Contabilidad', icon: Receipt, path: '/accounting', description: 'Fiscal y finanzas', accent: '#FF006E' },
  { id: 'briefing', label: 'Briefing', icon: Newspaper, path: '/briefing', description: 'Resumen diario', accent: '#06B6D4' },
  { id: 'files', label: 'Archivos', icon: FolderOpen, path: '/files', description: 'Documentos', accent: '#A78BFA' },
  { id: 'settings', label: 'Ajustes', icon: Settings, path: '/settings', description: 'Configuración', accent: '#64748B' },
]

/* ─── Greeting ─── */
function getGreeting(name?: string): string {
  const hour = new Date().getHours()
  const n = name?.split(' ')[0] || ''
  if (hour < 7) return `Buenas noches, ${n}`
  if (hour < 12) return `Buenos días, ${n}`
  if (hour < 20) return `Buenas tardes, ${n}`
  return `Buenas noches, ${n}`
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

/* ─── Chat Panel (slides up from bottom) ─── */
function ChatPanel({
  active, messages, input, setInput, isStreaming, onSend, onClose, setBrainState, greeting,
}: {
  active: boolean; messages: ChatMessage[]; input: string; greeting: string
  setInput: (v: string) => void; isStreaming: boolean; onSend: () => void
  onClose: () => void; setBrainState: (s: BrainState) => void
}) {
  const bottomRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages])
  useEffect(() => { if (active) setTimeout(() => inputRef.current?.focus(), 300) }, [active])

  useEffect(() => {
    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && active) { e.preventDefault(); onClose() }
    }
    window.addEventListener('keydown', handleEsc)
    return () => window.removeEventListener('keydown', handleEsc)
  }, [active, onClose])

  return (
    <AnimatePresence>
      {active && (
        <motion.div
          className="fixed bottom-0 left-0 right-0 z-40"
          initial={{ y: 100, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          exit={{ y: 100, opacity: 0 }}
          transition={{ type: 'spring', stiffness: 300, damping: 30 }}
        >
          {messages.length > 0 && (
            <div className="max-w-2xl mx-auto px-4 mb-3 max-h-[50vh] overflow-y-auto">
              <div className="bg-black/40 backdrop-blur-xl border border-white/[0.05] rounded-2xl p-4 space-y-3">
                {messages.map((msg) => <MessageBubble key={msg.id} message={msg} />)}
                <div ref={bottomRef} />
              </div>
            </div>
          )}

          {messages.length === 0 && (
            <motion.p
              className="text-center mb-4 text-[13px] text-white/40 font-light tracking-wide"
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
            >
              {greeting}
            </motion.p>
          )}

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
                  onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); onSend() } }}
                  placeholder="Habla con VULKRAN..."
                  className="flex-1 resize-none bg-transparent text-white/90 text-[13px] placeholder:text-white/20 focus:outline-none min-h-[38px] max-h-32 px-3 py-2"
                  rows={1}
                  disabled={isStreaming}
                />
                <button
                  onClick={onSend}
                  disabled={!input.trim() || isStreaming}
                  className={cn(
                    'shrink-0 h-9 w-9 rounded-lg flex items-center justify-center transition-all duration-200',
                    input.trim()
                      ? 'bg-[#00F0FF] text-black shadow-[0_0_16px_rgba(0,240,255,0.3)]'
                      : 'bg-white/[0.04] text-white/20',
                  )}
                >
                  {isStreaming ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
                </button>
              </div>
              <p className="text-center mt-2 text-[10px] text-white/15 tracking-wider hidden md:block">
                ESC cerrar · ENTER enviar · ⌘K buscar
              </p>
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}

/* ─── Module card (desktop arc) ─── */
function ModuleCard({
  module, index, total, visible, onNavigate, activePath,
}: {
  module: Module; index: number; total: number; visible: boolean
  onNavigate: (p: string) => void; activePath: string
}) {
  const angle = (index / total) * Math.PI * 2 - Math.PI / 2
  const radius = Math.min(280, typeof window !== 'undefined' ? window.innerWidth * 0.22 : 280)
  const x = Math.cos(angle) * radius
  const y = Math.sin(angle) * radius
  const Icon = module.icon
  const isActive = activePath.startsWith(module.path)

  return (
    <motion.button
      className="absolute flex flex-col items-center gap-2 cursor-pointer group"
      style={{ left: `calc(50% + ${x}px)`, top: `calc(50% + ${y}px)`, transform: 'translate(-50%, -50%)' }}
      initial={{ opacity: 0, scale: 0.3 }}
      animate={{ opacity: visible ? 1 : 0, scale: visible ? 1 : 0.3 }}
      transition={{ duration: 0.5, delay: visible ? 0.1 + index * 0.05 : 0, ease: [0.34, 1.56, 0.64, 1] }}
      onClick={() => visible && onNavigate(module.path)}
      whileHover={visible ? { scale: 1.12 } : {}}
      whileTap={visible ? { scale: 0.92 } : {}}
    >
      <div className={cn(
        'relative w-14 h-14 rounded-xl flex items-center justify-center transition-all duration-300',
        'border bg-white/[0.03] backdrop-blur-md',
        isActive
          ? 'border-[#00F0FF]/40 bg-[#00F0FF]/[0.08] shadow-[0_0_24px_rgba(0,240,255,0.2)]'
          : 'border-white/[0.06] group-hover:border-[#00F0FF]/30 group-hover:bg-[#00F0FF]/[0.06] group-hover:shadow-[0_0_20px_rgba(0,240,255,0.15)]',
      )}>
        <Icon className={cn(
          'h-5 w-5 transition-colors duration-300',
          isActive ? 'text-[#00F0FF]' : 'text-white/40 group-hover:text-[#00F0FF]',
        )} />
        <div className="absolute top-0 left-0 w-2 h-2 border-t border-l border-white/[0.08] rounded-tl-lg group-hover:border-[#00F0FF]/30 transition-colors" />
        <div className="absolute bottom-0 right-0 w-2 h-2 border-b border-r border-white/[0.08] rounded-br-lg group-hover:border-[#00F0FF]/30 transition-colors" />
      </div>
      <span className={cn(
        'text-[11px] font-semibold tracking-wide transition-colors',
        isActive ? 'text-[#00F0FF]/90' : 'text-white/50 group-hover:text-[#00F0FF]/90',
      )}>
        {module.label}
      </span>
    </motion.button>
  )
}

/* ─── Brain Mini (shown when section is active) ─── */
function BrainMini({ state, onClick }: { state: BrainState; onClick: () => void }) {
  return (
    <motion.div
      className="fixed top-4 left-4 z-30 cursor-pointer group"
      initial={{ opacity: 0, scale: 0.5, x: -40 }}
      animate={{ opacity: 1, scale: 1, x: 0 }}
      exit={{ opacity: 0, scale: 0.5, x: -40 }}
      transition={{ type: 'spring', stiffness: 300, damping: 25 }}
      onClick={onClick}
    >
      <div className="w-16 h-16 rounded-2xl border border-white/[0.06] bg-black/60 backdrop-blur-xl overflow-hidden group-hover:border-[#00F0FF]/30 group-hover:shadow-[0_0_20px_rgba(0,240,255,0.15)] transition-all duration-300">
        <HoloBrain state={state} size="sm" className="scale-[1.8] translate-y-1" />
      </div>
      <div className="absolute -bottom-1 left-1/2 -translate-x-1/2">
        <div className={cn(
          'h-1.5 w-1.5 rounded-full transition-colors',
          state === 'idle' ? 'bg-[#00F0FF]/30' : 'bg-[#00F0FF] shadow-[0_0_6px_rgba(0,240,255,0.5)]',
        )} />
      </div>
    </motion.div>
  )
}

/* ─── HUD status ─── */
function HUDStatus({ state }: { state: BrainState }) {
  return (
    <div className="flex items-center gap-2 pointer-events-none">
      <div className={cn(
        'h-1.5 w-1.5 rounded-full transition-colors duration-500',
        state === 'idle' ? 'bg-[#00F0FF]/30' : 'bg-[#00F0FF] shadow-[0_0_8px_rgba(0,240,255,0.5)]',
      )} />
      <span className="text-[10px] text-white/20 font-mono tracking-wider uppercase">
        {state === 'idle' ? 'standby' : state === 'thinking' ? 'processing' : state === 'responding' ? 'transmitting' : state}
      </span>
    </div>
  )
}

/* ═══════════════════════════════════════════════════════
   PulseLayout — Unified brain-centric layout
   ═══════════════════════════════════════════════════════ */
export default function PulseLayout() {
  const navigate = useNavigate()
  const location = useLocation()
  const { user, logout } = useAuthStore()

  const isHome = location.pathname === '/'
  const activeModule = MODULES.find((m) => location.pathname.startsWith(m.path))

  // Brain & chat state
  const [brainState, setBrainState] = useState<BrainState>('idle')
  const [chatOpen, setChatOpen] = useState(false)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [conversationId, setConversationId] = useState<string | null>(null)
  const [isStreaming, setIsStreaming] = useState(false)
  const [greeting, setGreeting] = useState('')
  const [modulesVisible, setModulesVisible] = useState(false)
  const [cmdPaletteOpen, setCmdPaletteOpen] = useState(false)
  const [mobileCarouselOpen, setMobileCarouselOpen] = useState(false)

  // Show modules on home after brain click
  const handleBrainClick = useCallback(() => {
    if (isHome) {
      if (!modulesVisible) {
        setModulesVisible(true)
        setChatOpen(true)
        setGreeting(getGreeting(user?.name))
        setBrainState('activating')
        setTimeout(() => setBrainState('idle'), 800)
      } else {
        setChatOpen((c) => !c)
      }
    }
  }, [isHome, modulesVisible, user?.name])

  // Brain mini click → go home
  const handleBrainMiniClick = useCallback(() => {
    navigate('/')
    setChatOpen(false)
  }, [navigate])

  // Mobile brain tap → carousel
  const handleMobileBrainClick = useCallback(() => {
    if (isHome) {
      setMobileCarouselOpen(true)
      setGreeting(getGreeting(user?.name))
    }
  }, [isHome, user?.name])

  // Navigate to module
  const handleNavigate = useCallback((path: string) => {
    navigate(path)
    setModulesVisible(false)
    setMobileCarouselOpen(false)
    setChatOpen(false)
  }, [navigate])

  // Close chat
  const handleCloseChat = useCallback(() => {
    if (isStreaming) return
    setChatOpen(false)
    setBrainState('idle')
  }, [isStreaming])

  // ESC → close section or chat, go home
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        if (chatOpen) {
          handleCloseChat()
        } else if (!isHome) {
          navigate('/')
        }
      }
      // Cmd+K or Ctrl+K → command palette
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault()
        setCmdPaletteOpen((v) => !v)
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [chatOpen, isHome, navigate, handleCloseChat])

  // Reset modules visibility when leaving home
  useEffect(() => {
    if (isHome) {
      setModulesVisible(false)
    }
  }, [isHome])

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

  return (
    <div className="fixed inset-0 bg-black overflow-hidden">
      {/* ─── Background ─── */}
      <div className="absolute inset-0 pointer-events-none">
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] rounded-full bg-[#00F0FF]/[0.015] blur-[120px]" />
        <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-white/[0.04] to-transparent" />
        <div
          className="absolute inset-0 opacity-[0.012]"
          style={{
            backgroundImage: `
              linear-gradient(rgba(0,240,255,0.3) 1px, transparent 1px),
              linear-gradient(90deg, rgba(0,240,255,0.3) 1px, transparent 1px)
            `,
            backgroundSize: '60px 60px',
          }}
        />
      </div>

      {/* ═══ HOME STATE ═══ */}
      {isHome && (
        <>
          {/* Top bar */}
          <header className="relative z-10 flex items-center justify-between px-6 py-5">
            <div className="flex items-center gap-2.5">
              <div className="h-2 w-2 rounded-full bg-[#00F0FF]/40 shadow-[0_0_8px_rgba(0,240,255,0.3)]" />
              <span className="text-[13px] font-semibold tracking-[0.25em] text-white/50">VULKRAN</span>
              <span className="text-[9px] font-medium text-white/15 tracking-[0.3em] mt-px">OS</span>
            </div>
            <div className="flex items-center gap-4">
              <button
                onClick={() => setCmdPaletteOpen(true)}
                className="hidden md:flex items-center gap-2 px-3 py-1.5 rounded-lg border border-white/[0.06] bg-white/[0.02] text-[11px] text-white/25 hover:text-white/40 hover:border-white/[0.1] transition-all"
              >
                <Search className="h-3 w-3" />
                <span>Buscar</span>
                <kbd className="text-[9px] px-1 py-0.5 rounded border border-white/[0.08] bg-white/[0.03]">⌘K</kbd>
              </button>
              <span className="text-[11px] text-white/20 font-mono hidden md:block">{user?.name}</span>
              <button
                onClick={logout}
                className="text-[10px] text-white/15 hover:text-white/40 transition-colors tracking-[0.15em] uppercase font-medium"
              >
                Salir
              </button>
            </div>
          </header>

          {/* Brain — center */}
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-[55%] z-0">
            {/* Desktop brain */}
            <div className="hidden md:block">
              <Suspense fallback={<div className="h-[22rem] w-[22rem]" />}>
                <HoloBrain
                  state={brainState}
                  size="xl"
                  onClick={handleBrainClick}
                  className={cn(
                    'transition-all duration-700',
                    !modulesVisible && 'opacity-80 hover:opacity-100',
                    brainState === 'activating' && 'scale-105',
                  )}
                />
              </Suspense>
            </div>
            {/* Mobile brain */}
            <div className="md:hidden">
              <Suspense fallback={<div className="h-48 w-48" />}>
                <HoloBrain
                  state={brainState}
                  size="lg"
                  onClick={handleMobileBrainClick}
                  className="opacity-90"
                />
              </Suspense>
            </div>

            {/* Dormant hint */}
            <AnimatePresence>
              {!modulesVisible && !mobileCarouselOpen && (
                <motion.div
                  className="absolute -bottom-10 left-1/2 -translate-x-1/2 flex items-center gap-3"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  transition={{ delay: 1.5, duration: 0.8 }}
                >
                  <div className="h-px w-8 bg-gradient-to-r from-transparent to-white/10" />
                  <span className="text-[10px] text-white/20 tracking-[0.3em] font-light">
                    TOCA PARA ACTIVAR
                  </span>
                  <div className="h-px w-8 bg-gradient-to-l from-transparent to-white/10" />
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {/* Desktop radial modules */}
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-[55%] hidden md:block pointer-events-none z-20">
            <div className="pointer-events-auto">
              {MODULES.map((mod, i) => (
                <ModuleCard
                  key={mod.id}
                  module={mod}
                  index={i}
                  total={MODULES.length}
                  visible={modulesVisible}
                  onNavigate={handleNavigate}
                  activePath={location.pathname}
                />
              ))}
            </div>
          </div>

          {/* HUD status */}
          <AnimatePresence>
            {(chatOpen || modulesVisible) && (
              <motion.div
                className="absolute bottom-8 left-1/2 -translate-x-1/2 z-10"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
              >
                <HUDStatus state={brainState} />
              </motion.div>
            )}
          </AnimatePresence>

          {/* Mobile carousel */}
          <AnimatePresence>
            {mobileCarouselOpen && (
              <Suspense fallback={null}>
                <GlassCarousel
                  modules={MODULES}
                  onNavigate={handleNavigate}
                  onClose={() => setMobileCarouselOpen(false)}
                />
              </Suspense>
            )}
          </AnimatePresence>

          {/* Chat panel (home) */}
          <ChatPanel
            active={chatOpen}
            greeting={greeting}
            messages={messages}
            input={input}
            setInput={setInput}
            isStreaming={isStreaming}
            onSend={sendMessage}
            onClose={handleCloseChat}
            setBrainState={setBrainState}
          />
        </>
      )}

      {/* ═══ SECTION STATE ═══ */}
      {!isHome && (
        <>
          {/* Brain mini — top left */}
          <AnimatePresence>
            <BrainMini state={brainState} onClick={handleBrainMiniClick} />
          </AnimatePresence>

          {/* Section header */}
          <header className="fixed top-0 left-0 right-0 z-20 flex items-center justify-between px-4 py-3 md:pl-24">
            <div className="flex items-center gap-3 pl-16 md:pl-0">
              <button
                onClick={() => navigate('/')}
                className="flex items-center gap-2 text-white/30 hover:text-white/60 transition-colors group"
              >
                <ArrowLeft className="h-4 w-4 group-hover:-translate-x-0.5 transition-transform" />
                <span className="text-[11px] tracking-wider uppercase hidden md:inline">Inicio</span>
              </button>
              {activeModule && (
                <div className="flex items-center gap-2">
                  <div className="h-4 w-px bg-white/[0.06]" />
                  <activeModule.icon className="h-4 w-4 text-[#00F0FF]/70" />
                  <span className="text-sm font-medium text-white/70">{activeModule.label}</span>
                </div>
              )}
            </div>
            <div className="flex items-center gap-3">
              <button
                onClick={() => setCmdPaletteOpen(true)}
                className="hidden md:flex items-center gap-1.5 px-2.5 py-1 rounded-lg border border-white/[0.06] bg-white/[0.02] text-[10px] text-white/20 hover:text-white/40 transition-all"
              >
                <Search className="h-3 w-3" />
                <kbd className="text-[9px] px-1 rounded border border-white/[0.06]">⌘K</kbd>
              </button>
              <button
                onClick={() => { setChatOpen(true); setGreeting(getGreeting(user?.name)) }}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-[#00F0FF]/20 bg-[#00F0FF]/[0.05] text-[11px] text-[#00F0FF]/70 hover:bg-[#00F0FF]/[0.1] transition-all"
              >
                <Bot className="h-3.5 w-3.5" />
                <span className="hidden md:inline">AI</span>
              </button>
              <button
                onClick={logout}
                className="p-1.5 text-white/15 hover:text-white/40 transition-colors"
                title="Cerrar sesión"
              >
                <LogOut className="h-4 w-4" />
              </button>
            </div>
          </header>

          {/* Section content */}
          <main className="absolute inset-0 pt-14 overflow-y-auto overflow-x-hidden">
            <div className="p-4 md:p-6 md:pl-24 pb-20">
              <motion.div
                key={location.pathname}
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.25 }}
              >
                <Outlet />
              </motion.div>
            </div>
          </main>

          {/* Mobile bottom nav — quick section switcher */}
          <nav className="fixed bottom-0 left-0 right-0 z-30 md:hidden glass-strong border-t border-white/[0.04] safe-area-bottom">
            <div className="flex items-center justify-around h-14 px-1">
              {MODULES.slice(0, 5).map((mod) => {
                const Icon = mod.icon
                const isActive = location.pathname.startsWith(mod.path)
                return (
                  <button
                    key={mod.id}
                    onClick={() => navigate(mod.path)}
                    className={cn(
                      'flex flex-col items-center justify-center gap-0.5 px-2 py-1 rounded-lg transition-all min-w-[48px]',
                      isActive ? 'text-[#00F0FF]' : 'text-white/30',
                    )}
                  >
                    <Icon className="h-5 w-5" />
                    <span className="text-[9px] font-medium">{mod.label}</span>
                  </button>
                )
              })}
              <button
                onClick={() => navigate('/')}
                className="flex flex-col items-center justify-center gap-0.5 px-2 py-1 rounded-lg text-white/30"
              >
                <div className="h-5 w-5 rounded-full border border-[#00F0FF]/30 flex items-center justify-center">
                  <div className="h-2 w-2 rounded-full bg-[#00F0FF]/40" />
                </div>
                <span className="text-[9px] font-medium">Hub</span>
              </button>
            </div>
          </nav>

          {/* Chat panel (section) */}
          <ChatPanel
            active={chatOpen}
            greeting={greeting}
            messages={messages}
            input={input}
            setInput={setInput}
            isStreaming={isStreaming}
            onSend={sendMessage}
            onClose={handleCloseChat}
            setBrainState={setBrainState}
          />
        </>
      )}

      {/* ─── Command Palette (always available) ─── */}
      <Suspense fallback={null}>
        {cmdPaletteOpen && (
          <CommandPalette
            modules={MODULES}
            onNavigate={(path) => { handleNavigate(path); setCmdPaletteOpen(false) }}
            onClose={() => setCmdPaletteOpen(false)}
          />
        )}
      </Suspense>
    </div>
  )
}
