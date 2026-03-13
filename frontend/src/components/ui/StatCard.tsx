import { motion } from 'framer-motion'
import { cn } from '@/lib/utils'

interface StatCardProps {
  label: string
  value: string | number
  subtitle?: string
  icon?: React.ReactNode
  trend?: 'up' | 'down' | 'neutral'
  accentColor?: string
  className?: string
  delay?: number
}

export function StatCard({
  label,
  value,
  subtitle,
  icon,
  trend,
  accentColor = 'vulkran',
  className,
  delay = 0,
}: StatCardProps) {
  return (
    <motion.div
      className={cn(
        'glass rounded-xl p-5 relative overflow-hidden group',
        'hover:glow-md transition-all duration-300',
        className,
      )}
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay }}
    >
      {/* Accent line */}
      <div
        className={cn('absolute top-0 left-0 right-0 h-[2px]', {
          'bg-gradient-to-r from-vulkran to-vulkran-light': accentColor === 'vulkran',
          'bg-gradient-to-r from-neon-cyan to-neon-cyan/50': accentColor === 'cyan',
          'bg-gradient-to-r from-neon-green to-neon-green/50': accentColor === 'green',
          'bg-gradient-to-r from-neon-amber to-neon-amber/50': accentColor === 'amber',
        })}
      />

      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs text-muted-foreground uppercase tracking-wider mb-1">{label}</p>
          <p className="text-2xl font-bold text-foreground flex items-center gap-2">
            {value}
            {trend && (
              <span
                className={cn('text-xs font-medium', {
                  'text-success': trend === 'up',
                  'text-error': trend === 'down',
                  'text-muted-foreground': trend === 'neutral',
                })}
              >
                {trend === 'up' ? '↑' : trend === 'down' ? '↓' : '→'}
              </span>
            )}
          </p>
          {subtitle && <p className="text-xs text-muted-foreground mt-1">{subtitle}</p>}
        </div>
        {icon && (
          <div className="text-vulkran-light/40 group-hover:text-vulkran-light/70 transition-colors">
            {icon}
          </div>
        )}
      </div>
    </motion.div>
  )
}
