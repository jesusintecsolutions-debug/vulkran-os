import { useState, useRef, useEffect, useCallback, Suspense } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Send, Sparkles, Bot, User, Loader2, Wrench } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui'
import { HoloBrain } from '@/components/HoloBrain'

const API_BASE = import.meta.env.VITE_API_URL || ''

type BrainState = 'idle' | 'typing' | 'thinking' | 'responding'

interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  toolCalls?: { name: string; input: Record<string, unknown> }[]
  toolResults?: { name: string; result: unknown }[]
  isStreaming?: boolean
}

export default function ChatPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [conversationId, setConversationId] = useState<string | null>(null)
  const [brainState, setBrainState] = useState<BrainState>('idle')
  const [isStreaming, setIsStreaming] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  const scrollToBottom = useCallback(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [])

  useEffect(() => {
    scrollToBottom()
  }, [messages, scrollToBottom])

  const sendMessage = useCallback(async () => {
    const text = input.trim()
    if (!text || isStreaming) return

    const userMsg: ChatMessage = {
      id: crypto.randomUUID(),
      role: 'user',
      content: text,
    }

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
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          message: text,
          conversation_id: conversationId,
        }),
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
                prev.map((m) =>
                  m.id === assistantId ? { ...m, content: m.content + event.text } : m,
                ),
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
                prev.map((m) =>
                  m.id === assistantId ? { ...m, content: `Error: ${event.message}` } : m,
                ),
              )
            }
          } catch {
            // skip malformed JSON
          }
        }
      }
    } catch (err) {
      setMessages((prev) =>
        prev.map((m) =>
          m.id === assistantId ? { ...m, content: `Error de conexión: ${err}` } : m,
        ),
      )
    } finally {
      setMessages((prev) => prev.map((m) => (m.id === assistantId ? { ...m, isStreaming: false } : m)))
      setIsStreaming(false)
      setBrainState('idle')
      inputRef.current?.focus()
    }
  }, [input, isStreaming, conversationId])

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  return (
    <div className="flex flex-col h-[calc(100vh-3.5rem-5rem)] md:h-[calc(100vh-3.5rem)] -m-4 md:-m-6">
      {/* Messages */}
      <div className="flex-1 overflow-y-auto">
        {messages.length === 0 ? (
          <EmptyState brainState={brainState} />
        ) : (
          <div className="max-w-3xl mx-auto px-4 py-6 space-y-6">
            <AnimatePresence initial={false}>
              {messages.map((msg) => (
                <MessageBubble key={msg.id} message={msg} />
              ))}
            </AnimatePresence>
            <div ref={bottomRef} />
          </div>
        )}
      </div>

      {/* Input */}
      <div className="border-t border-border bg-surface-0/80 backdrop-blur-sm px-4 py-3">
        <div className="max-w-3xl mx-auto">
          <div className="glass rounded-xl flex items-end gap-2 p-2">
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => {
                setInput(e.target.value)
                setBrainState(e.target.value ? 'typing' : 'idle')
              }}
              onKeyDown={handleKeyDown}
              placeholder="Escribe un mensaje a VULKRAN..."
              className="flex-1 resize-none bg-transparent text-foreground text-sm placeholder:text-muted-foreground focus:outline-none min-h-[40px] max-h-32 px-3 py-2"
              rows={1}
              disabled={isStreaming}
            />
            <Button
              variant="primary"
              size="sm"
              onClick={sendMessage}
              disabled={!input.trim() || isStreaming}
              className="shrink-0 h-9 w-9 !p-0"
            >
              {isStreaming ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
            </Button>
          </div>
          <p className="text-[10px] text-muted-foreground/50 text-center mt-1.5">
            VULKRAN OS — Agente AI con 21 herramientas
          </p>
        </div>
      </div>
    </div>
  )
}

/* ─── Empty state ─── */
function EmptyState({ brainState }: { brainState: BrainState }) {
  return (
    <div className="flex flex-col items-center justify-center h-full gap-4">
      <Suspense
        fallback={
          <div className="h-40 w-40 flex items-center justify-center">
            <Sparkles className="h-12 w-12 text-vulkran animate-pulse" />
          </div>
        }
      >
        <HoloBrain state={brainState} size="lg" />
      </Suspense>
      <motion.div
        className="text-center"
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3 }}
      >
        <h2 className="text-xl font-bold text-foreground mb-1">VULKRAN OS</h2>
        <p className="text-sm text-muted-foreground max-w-sm">
          Tu asistente de negocio con IA. Gestiona clientes, genera contenido, investiga mercados,
          envía emails y más.
        </p>
      </motion.div>
      <motion.div
        className="flex flex-wrap justify-center gap-2 mt-2"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.5 }}
      >
        {['Dame el briefing diario', 'Estado del pipeline', 'Genera contenido', 'Resumen financiero'].map(
          (hint) => (
            <button
              key={hint}
              className="text-xs glass rounded-full px-4 py-2 text-muted-foreground hover:text-foreground hover:border-vulkran/30 transition-all cursor-pointer"
            >
              {hint}
            </button>
          ),
        )}
      </motion.div>
    </div>
  )
}

/* ─── Message bubble ─── */
function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === 'user'

  return (
    <motion.div
      className={cn('flex gap-3', isUser ? 'justify-end' : 'justify-start')}
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2 }}
    >
      {!isUser && (
        <div className="flex-shrink-0 h-8 w-8 rounded-lg gradient-vulkran flex items-center justify-center shadow-lg shadow-vulkran/20">
          <Bot className="h-4 w-4 text-white" />
        </div>
      )}

      <div className={cn('max-w-[75%] space-y-2', isUser && 'order-first')}>
        {/* Tool calls */}
        {message.toolCalls && message.toolCalls.length > 0 && (
          <div className="space-y-1">
            {message.toolCalls.map((tc, i) => (
              <div key={i} className="flex items-center gap-2 text-xs text-neon-cyan/70">
                <Wrench className="h-3 w-3" />
                <span className="font-mono">{tc.name}</span>
                {message.toolResults?.[i] && <span className="text-success/70">✓</span>}
              </div>
            ))}
          </div>
        )}

        {/* Content */}
        {(message.content || message.isStreaming) && (
          <div
            className={cn(
              'rounded-xl px-4 py-3 text-sm leading-relaxed',
              isUser ? 'bg-vulkran text-white rounded-br-sm' : 'glass rounded-bl-sm text-foreground',
            )}
          >
            <div className="whitespace-pre-wrap">{message.content}</div>
            {message.isStreaming && !message.content && (
              <div className="flex items-center gap-1.5">
                <span className="h-1.5 w-1.5 rounded-full bg-vulkran-light animate-bounce" style={{ animationDelay: '0ms' }} />
                <span className="h-1.5 w-1.5 rounded-full bg-vulkran-light animate-bounce" style={{ animationDelay: '150ms' }} />
                <span className="h-1.5 w-1.5 rounded-full bg-vulkran-light animate-bounce" style={{ animationDelay: '300ms' }} />
              </div>
            )}
            {message.isStreaming && message.content && (
              <span className="inline-block w-1.5 h-4 bg-vulkran-light ml-0.5 animate-pulse rounded-full" />
            )}
          </div>
        )}
      </div>

      {isUser && (
        <div className="flex-shrink-0 h-8 w-8 rounded-lg bg-surface-2 flex items-center justify-center">
          <User className="h-4 w-4 text-muted-foreground" />
        </div>
      )}
    </motion.div>
  )
}
