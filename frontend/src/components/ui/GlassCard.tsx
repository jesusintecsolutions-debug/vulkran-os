import { motion, type HTMLMotionProps } from 'framer-motion'
import { cn } from '@/lib/utils'

interface GlassCardProps extends HTMLMotionProps<'div'> {
  glow?: boolean
  hover?: boolean
  variant?: 'default' | 'strong' | 'neon'
}

export function GlassCard({
  className,
  glow,
  hover = true,
  variant = 'default',
  children,
  ...props
}: GlassCardProps) {
  const variants = {
    default: 'glass',
    strong: 'glass-strong',
    neon: 'glass neon-border',
  }

  return (
    <motion.div
      className={cn(
        'rounded-xl p-5',
        variants[variant],
        glow && 'glow-sm',
        hover && 'transition-all duration-300 hover:glow-md hover:border-vulkran/25',
        className,
      )}
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      {...props}
    >
      {children}
    </motion.div>
  )
}
