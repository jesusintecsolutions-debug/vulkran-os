import { cn } from '@/lib/utils'

type BadgeVariant = 'default' | 'success' | 'warning' | 'error' | 'info' | 'neon' | 'purple'

interface BadgeProps {
  children: React.ReactNode
  variant?: BadgeVariant
  dot?: boolean
  className?: string
}

const variantStyles: Record<BadgeVariant, string> = {
  default: 'bg-surface-2 text-muted-foreground border-border',
  success: 'bg-success/10 text-success border-success/20',
  warning: 'bg-warning/10 text-warning border-warning/20',
  error: 'bg-error/10 text-error border-error/20',
  info: 'bg-info/10 text-info border-info/20',
  neon: 'bg-neon-cyan/10 text-neon-cyan border-neon-cyan/20',
  purple: 'bg-vulkran/10 text-vulkran-light border-vulkran/20',
}

export function Badge({ children, variant = 'default', dot, className }: BadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium',
        variantStyles[variant],
        className,
      )}
    >
      {dot && (
        <span
          className={cn('h-1.5 w-1.5 rounded-full', {
            'bg-muted-foreground': variant === 'default',
            'bg-success': variant === 'success',
            'bg-warning': variant === 'warning',
            'bg-error': variant === 'error',
            'bg-info': variant === 'info',
            'bg-neon-cyan': variant === 'neon',
            'bg-vulkran-light': variant === 'purple',
          })}
        />
      )}
      {children}
    </span>
  )
}
