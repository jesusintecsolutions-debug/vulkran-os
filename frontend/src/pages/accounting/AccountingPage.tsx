import { useQuery } from '@tanstack/react-query'
import { api } from '@/api/client'
import { GlassCard, Badge } from '@/components/ui'
import { Receipt } from 'lucide-react'

interface Invoice {
  id: string
  invoice_number: string
  client_id: string
  status: string
  total: string
  issue_date: string
  due_date: string
}

const STATUS_VARIANT: Record<string, 'default' | 'info' | 'success' | 'error'> = {
  draft: 'default',
  sent: 'info',
  paid: 'success',
  overdue: 'error',
  cancelled: 'default',
}

export default function AccountingPage() {
  const { data: invoices, isLoading } = useQuery<Invoice[]>({
    queryKey: ['invoices'],
    queryFn: async () => (await api.get('/accounting/invoices')).data,
  })

  if (isLoading) return <div className="flex items-center justify-center h-64"><div className="h-8 w-8 rounded-full border-2 border-vulkran border-t-transparent animate-spin" /></div>

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <Receipt className="h-6 w-6 text-vulkran-light" />
        <h1 className="text-xl sm:text-2xl font-bold">Contabilidad</h1>
      </div>

      {/* Mobile: card view */}
      <div className="space-y-3 md:hidden">
        {invoices?.map((inv) => (
          <GlassCard key={inv.id} className="!p-4 overflow-hidden">
            <div className="flex items-start justify-between gap-2 mb-2">
              <div className="min-w-0 flex-1">
                <p className="font-medium font-mono text-foreground truncate">{inv.invoice_number}</p>
                <p className="text-xs text-muted-foreground">{inv.issue_date}</p>
              </div>
              <Badge variant={STATUS_VARIANT[inv.status] || 'default'} dot className="shrink-0">{inv.status}</Badge>
            </div>
            <div className="flex items-center justify-between text-xs text-muted-foreground">
              <span>Vence: {inv.due_date}</span>
              <span className="font-mono text-foreground font-medium text-sm">{inv.total}€</span>
            </div>
          </GlassCard>
        ))}
        {invoices?.length === 0 && <p className="text-sm text-muted-foreground text-center py-8">Sin facturas</p>}
      </div>

      {/* Desktop: table view */}
      <GlassCard hover={false} className="overflow-hidden !p-0 hidden md:block">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border text-left">
              <th className="px-4 py-3 font-medium text-muted-foreground text-xs uppercase tracking-wider">Nº Factura</th>
              <th className="px-4 py-3 font-medium text-muted-foreground text-xs uppercase tracking-wider">Fecha</th>
              <th className="px-4 py-3 font-medium text-muted-foreground text-xs uppercase tracking-wider">Vencimiento</th>
              <th className="px-4 py-3 font-medium text-muted-foreground text-xs uppercase tracking-wider">Estado</th>
              <th className="px-4 py-3 font-medium text-muted-foreground text-xs uppercase tracking-wider text-right">Total</th>
            </tr>
          </thead>
          <tbody>
            {invoices?.map((inv) => (
              <tr key={inv.id} className="border-b border-border/50 last:border-0 hover:bg-surface-2/50 transition-colors">
                <td className="px-4 py-3 font-medium font-mono text-foreground">{inv.invoice_number}</td>
                <td className="px-4 py-3 text-muted-foreground">{inv.issue_date}</td>
                <td className="px-4 py-3 text-muted-foreground">{inv.due_date}</td>
                <td className="px-4 py-3"><Badge variant={STATUS_VARIANT[inv.status] || 'default'} dot>{inv.status}</Badge></td>
                <td className="px-4 py-3 text-right font-medium font-mono text-foreground">{inv.total}€</td>
              </tr>
            ))}
          </tbody>
        </table>
      </GlassCard>
    </div>
  )
}
