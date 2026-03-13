import { GlassCard } from '@/components/ui'
import { FolderOpen } from 'lucide-react'

export default function FilesPage() {
  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <FolderOpen className="h-6 w-6 text-vulkran-light" />
        <h1 className="text-2xl font-bold">Archivos</h1>
      </div>
      <GlassCard className="text-center py-12">
        <FolderOpen className="h-12 w-12 text-muted-foreground/30 mx-auto mb-3" />
        <p className="text-muted-foreground">Gestor de archivos — próximamente.</p>
        <p className="mt-1 text-sm text-muted-foreground/60">Aquí podrás navegar los archivos de cada cliente.</p>
      </GlassCard>
    </div>
  )
}
