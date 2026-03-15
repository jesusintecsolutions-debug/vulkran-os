import { useState, useRef, useEffect, useMemo } from 'react'
import { motion } from 'framer-motion'
import { Search, type LucideIcon } from 'lucide-react'
import { cn } from '@/lib/utils'

interface Module {
  id: string
  label: string
  icon: LucideIcon
  path: string
  description: string
}

interface CommandPaletteProps {
  modules: Module[]
  onNavigate: (path: string) => void
  onClose: () => void
}

export default function CommandPalette({ modules, onNavigate, onClose }: CommandPaletteProps) {
  const [query, setQuery] = useState('')
  const [selectedIndex, setSelectedIndex] = useState(0)
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => { inputRef.current?.focus() }, [])

  const filtered = useMemo(() => {
    if (!query.trim()) return modules
    const q = query.toLowerCase()
    return modules.filter(
      (m) => m.label.toLowerCase().includes(q) || m.description.toLowerCase().includes(q),
    )
  }, [query, modules])

  useEffect(() => { setSelectedIndex(0) }, [filtered])

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setSelectedIndex((i) => Math.min(i + 1, filtered.length - 1))
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setSelectedIndex((i) => Math.max(i - 1, 0))
    } else if (e.key === 'Enter' && filtered[selectedIndex]) {
      onNavigate(filtered[selectedIndex].path)
    } else if (e.key === 'Escape') {
      onClose()
    }
  }

  return (
    <motion.div
      className="fixed inset-0 z-50 flex items-start justify-center pt-[20vh]"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.15 }}
    >
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />

      <motion.div
        className="relative w-full max-w-lg mx-4 rounded-2xl border border-white/[0.08] bg-black/80 backdrop-blur-xl overflow-hidden shadow-2xl"
        initial={{ scale: 0.95, y: -10 }}
        animate={{ scale: 1, y: 0 }}
        transition={{ type: 'spring', stiffness: 400, damping: 30 }}
      >
        {/* Search input */}
        <div className="flex items-center gap-3 px-4 py-3 border-b border-white/[0.06]">
          <Search className="h-4 w-4 text-white/25 flex-shrink-0" />
          <input
            ref={inputRef}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Buscar sección..."
            className="flex-1 bg-transparent text-white/90 text-sm placeholder:text-white/20 focus:outline-none"
          />
          <kbd className="text-[9px] px-1.5 py-0.5 rounded border border-white/[0.08] bg-white/[0.03] text-white/20">ESC</kbd>
        </div>

        {/* Results */}
        <div className="max-h-[300px] overflow-y-auto py-2">
          {filtered.map((mod, i) => {
            const Icon = mod.icon
            return (
              <button
                key={mod.id}
                onClick={() => onNavigate(mod.path)}
                onMouseEnter={() => setSelectedIndex(i)}
                className={cn(
                  'w-full flex items-center gap-3 px-4 py-2.5 text-left transition-colors',
                  i === selectedIndex ? 'bg-[#00F0FF]/[0.06]' : 'hover:bg-white/[0.03]',
                )}
              >
                <div className={cn(
                  'h-8 w-8 rounded-lg flex items-center justify-center border transition-colors',
                  i === selectedIndex ? 'border-[#00F0FF]/30 bg-[#00F0FF]/[0.08]' : 'border-white/[0.06] bg-white/[0.02]',
                )}>
                  <Icon className={cn(
                    'h-4 w-4 transition-colors',
                    i === selectedIndex ? 'text-[#00F0FF]' : 'text-white/40',
                  )} />
                </div>
                <div>
                  <p className={cn(
                    'text-sm font-medium transition-colors',
                    i === selectedIndex ? 'text-white/90' : 'text-white/60',
                  )}>{mod.label}</p>
                  <p className="text-[11px] text-white/25">{mod.description}</p>
                </div>
                {i === selectedIndex && (
                  <span className="ml-auto text-[10px] text-white/20">↵</span>
                )}
              </button>
            )
          })}
          {filtered.length === 0 && (
            <p className="px-4 py-6 text-center text-sm text-white/20">Sin resultados</p>
          )}
        </div>
      </motion.div>
    </motion.div>
  )
}
