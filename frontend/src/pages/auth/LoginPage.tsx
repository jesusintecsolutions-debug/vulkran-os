import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Sparkles, Loader2 } from 'lucide-react'
import { useAuthStore } from '@/stores/auth'
import { Button } from '@/components/ui'

export default function LoginPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const login = useAuthStore((s) => s.login)
  const navigate = useNavigate()

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await login(email, password)
      navigate('/')
    } catch {
      setError('Email o contraseña incorrectos')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4 relative overflow-hidden">
      <div className="pointer-events-none absolute top-1/4 left-1/3 h-96 w-96 rounded-full bg-vulkran/8 blur-[100px]" />
      <div className="pointer-events-none absolute bottom-1/4 right-1/3 h-64 w-64 rounded-full bg-neon-cyan/5 blur-[80px]" />

      <motion.div
        className="w-full max-w-sm glass-strong rounded-2xl p-8 glow-sm"
        initial={{ opacity: 0, y: 20, scale: 0.98 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        transition={{ duration: 0.5 }}
      >
        <div className="mb-8 text-center">
          <motion.div
            className="flex items-center justify-center gap-2 mb-2"
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
          >
            <Sparkles className="h-6 w-6 text-vulkran" />
            <h1 className="text-2xl font-bold tracking-wider text-vulkran text-glow">VULKRAN</h1>
            <span className="text-xs font-semibold text-vulkran-light/50 tracking-widest mt-1">OS</span>
          </motion.div>
          <p className="text-sm text-muted-foreground">Accede a tu panel de control</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="email" className="mb-1.5 block text-xs font-medium text-muted-foreground uppercase tracking-wider">
              Email
            </label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="w-full rounded-lg bg-surface-1 border border-border px-3 py-2.5 text-sm text-foreground outline-none focus:ring-2 focus:ring-vulkran/40 focus:border-vulkran/40 transition-all placeholder:text-muted-foreground"
              placeholder="tu@email.com"
            />
          </div>

          <div>
            <label htmlFor="password" className="mb-1.5 block text-xs font-medium text-muted-foreground uppercase tracking-wider">
              Contraseña
            </label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              className="w-full rounded-lg bg-surface-1 border border-border px-3 py-2.5 text-sm text-foreground outline-none focus:ring-2 focus:ring-vulkran/40 focus:border-vulkran/40 transition-all"
            />
          </div>

          {error && (
            <motion.p className="text-sm text-error" initial={{ opacity: 0, x: -5 }} animate={{ opacity: 1, x: 0 }}>
              {error}
            </motion.p>
          )}

          <Button type="submit" disabled={loading} variant="primary" size="lg" className="w-full">
            {loading ? <><Loader2 className="h-4 w-4 animate-spin" /> Entrando...</> : 'Entrar'}
          </Button>
        </form>

        <p className="text-[10px] text-muted-foreground/40 text-center mt-6">
          VULKRAN OS v0.1.0 — Agentic Business Operating System
        </p>
      </motion.div>
    </div>
  )
}
