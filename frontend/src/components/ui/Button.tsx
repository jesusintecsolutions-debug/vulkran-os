import { forwardRef, type ButtonHTMLAttributes } from 'react'
import { cn } from '@/lib/utils'

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger' | 'neon'
  size?: 'sm' | 'md' | 'lg'
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = 'primary', size = 'md', disabled, children, ...props }, ref) => {
    const base =
      'inline-flex items-center justify-center gap-2 font-medium rounded-lg transition-all duration-200 cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed'

    const variants = {
      primary: 'bg-vulkran text-white hover:bg-vulkran-light glow-sm hover:glow-md',
      secondary: 'bg-surface-2 text-foreground border border-border hover:bg-surface-3',
      ghost: 'text-muted-foreground hover:text-foreground hover:bg-surface-2',
      danger: 'bg-destructive/10 text-destructive border border-destructive/20 hover:bg-destructive/20',
      neon: 'bg-transparent text-neon-cyan border border-neon-cyan/30 hover:bg-neon-cyan/10 hover:shadow-[0_0_20px_rgba(0,240,255,0.2)]',
    }

    const sizes = {
      sm: 'h-8 px-3 text-xs',
      md: 'h-10 px-4 text-sm',
      lg: 'h-12 px-6 text-base',
    }

    return (
      <button
        ref={ref}
        className={cn(base, variants[variant], sizes[size], className)}
        disabled={disabled}
        {...props}
      >
        {children}
      </button>
    )
  },
)

Button.displayName = 'Button'
