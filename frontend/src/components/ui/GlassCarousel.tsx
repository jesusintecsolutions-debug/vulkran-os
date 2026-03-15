import { useRef, useEffect, useState, useCallback } from 'react'
import { motion } from 'framer-motion'
import { type LucideIcon } from 'lucide-react'
import { cn } from '@/lib/utils'

interface Module {
  id: string
  label: string
  icon: LucideIcon
  path: string
  description: string
  accent?: string
}

interface GlassCarouselProps {
  modules: Module[]
  onNavigate: (path: string) => void
  onClose: () => void
}

export default function GlassCarousel({ modules, onNavigate, onClose }: GlassCarouselProps) {
  const scrollRef = useRef<HTMLDivElement>(null)
  const [activeIndex, setActiveIndex] = useState(0)

  // Track scroll position to determine active card
  const handleScroll = useCallback(() => {
    if (!scrollRef.current) return
    const { scrollLeft, clientWidth } = scrollRef.current
    const cardWidth = clientWidth * 0.85
    const gap = clientWidth * 0.04
    const index = Math.round(scrollLeft / (cardWidth + gap))
    setActiveIndex(Math.max(0, Math.min(index, modules.length - 1)))
  }, [modules.length])

  useEffect(() => {
    const el = scrollRef.current
    if (!el) return
    el.addEventListener('scroll', handleScroll, { passive: true })
    return () => el.removeEventListener('scroll', handleScroll)
  }, [handleScroll])

  // Close on swipe down (touch start/end delta)
  const touchStartY = useRef(0)
  const handleTouchStart = useCallback((e: React.TouchEvent) => {
    touchStartY.current = e.touches[0].clientY
  }, [])
  const handleTouchEnd = useCallback((e: React.TouchEvent) => {
    const dy = e.changedTouches[0].clientY - touchStartY.current
    if (dy > 80) onClose()
  }, [onClose])

  return (
    <motion.div
      className="fixed inset-0 z-50 flex flex-col justify-end"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.3 }}
    >
      {/* Backdrop */}
      <motion.div
        className="absolute inset-0 bg-black/70 backdrop-blur-sm"
        onClick={onClose}
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
      />

      {/* Swipe hint */}
      <div className="relative z-10 flex justify-center mb-3">
        <div className="w-10 h-1 rounded-full bg-white/20" />
      </div>

      {/* Carousel */}
      <motion.div
        className="relative z-10 pb-safe-bottom"
        initial={{ y: 200 }}
        animate={{ y: 0 }}
        exit={{ y: 200 }}
        transition={{ type: 'spring', stiffness: 300, damping: 30 }}
        onTouchStart={handleTouchStart}
        onTouchEnd={handleTouchEnd}
      >
        <div
          ref={scrollRef}
          className="flex gap-[4vw] px-[7.5vw] overflow-x-auto snap-x snap-mandatory pb-8 no-scrollbar"
          style={{ scrollPaddingLeft: '7.5vw' }}
        >
          {modules.map((mod, i) => {
            const Icon = mod.icon
            const isActive = i === activeIndex
            return (
              <motion.button
                key={mod.id}
                className={cn(
                  'flex-shrink-0 w-[85vw] snap-center rounded-3xl p-6',
                  'border backdrop-blur-xl transition-all duration-300',
                  'flex flex-col items-start justify-between min-h-[220px]',
                  isActive
                    ? 'bg-white/[0.06] border-white/[0.12] scale-100'
                    : 'bg-white/[0.03] border-white/[0.06] scale-[0.92] opacity-60',
                )}
                onClick={() => onNavigate(mod.path)}
                whileTap={{ scale: 0.97 }}
              >
                <div className="flex items-start justify-between w-full">
                  <div
                    className="h-14 w-14 rounded-2xl flex items-center justify-center border border-white/[0.08]"
                    style={{ backgroundColor: `${mod.accent || '#00F0FF'}10` }}
                  >
                    <Icon
                      className="h-7 w-7"
                      style={{ color: `${mod.accent || '#00F0FF'}AA` }}
                    />
                  </div>
                  <div className="flex items-center gap-1.5">
                    {[0, 1, 2].map((dot) => (
                      <div
                        key={dot}
                        className={cn(
                          'h-1.5 w-1.5 rounded-full transition-colors',
                          isActive && dot === 0 ? 'bg-white/40' : 'bg-white/10',
                        )}
                      />
                    ))}
                  </div>
                </div>

                <div className="mt-auto">
                  <h3 className="text-xl font-semibold text-white/90 text-left">{mod.label}</h3>
                  <p className="text-sm text-white/40 mt-1 text-left">{mod.description}</p>
                </div>

                {/* Corner accents */}
                <div className="absolute top-3 left-3 w-3 h-3 border-t border-l border-white/[0.08] rounded-tl-xl" />
                <div className="absolute bottom-3 right-3 w-3 h-3 border-b border-r border-white/[0.08] rounded-br-xl" />
              </motion.button>
            )
          })}
        </div>

        {/* Dots indicator */}
        <div className="flex justify-center gap-1.5 pb-4">
          {modules.map((_, i) => (
            <div
              key={i}
              className={cn(
                'h-1 rounded-full transition-all duration-300',
                i === activeIndex ? 'w-4 bg-[#00F0FF]/60' : 'w-1 bg-white/15',
              )}
            />
          ))}
        </div>
      </motion.div>
    </motion.div>
  )
}
