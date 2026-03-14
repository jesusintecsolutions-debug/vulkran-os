import { Plus, X, Image, Palette } from 'lucide-react'

interface SlotDef {
  key: string
  type: string
  label: string
  required: boolean
  default?: unknown
  options?: string[]
  min?: number
  max?: number
  group?: string
  description?: string
}

interface SlotEditorProps {
  slot: SlotDef
  value: unknown
  onChange: (key: string, value: unknown) => void
}

const inputClass =
  'w-full rounded-lg border border-border bg-surface-1 px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:border-vulkran focus:outline-none transition-colors'

function TextSlotEditor({ slot, value, onChange }: SlotEditorProps) {
  return (
    <input
      type="text"
      value={(value as string) || ''}
      onChange={(e) => onChange(slot.key, e.target.value)}
      placeholder={slot.description || slot.label}
      className={inputClass}
    />
  )
}

function TextareaSlotEditor({ slot, value, onChange }: SlotEditorProps) {
  return (
    <textarea
      value={(value as string) || ''}
      onChange={(e) => onChange(slot.key, e.target.value)}
      placeholder={slot.description || slot.label}
      rows={3}
      className={`${inputClass} resize-none`}
    />
  )
}

function NumberSlotEditor({ slot, value, onChange }: SlotEditorProps) {
  return (
    <input
      type="number"
      value={(value as number) ?? slot.default ?? 0}
      onChange={(e) => onChange(slot.key, Number(e.target.value))}
      min={slot.min}
      max={slot.max}
      step={slot.max !== undefined && slot.max <= 1 ? 0.1 : 1}
      className={inputClass}
    />
  )
}

function ColorSlotEditor({ slot, value, onChange }: SlotEditorProps) {
  const color = (value as string) || (slot.default as string) || '#7c3aed'
  return (
    <div className="flex items-center gap-2">
      <div className="relative">
        <input
          type="color"
          value={color}
          onChange={(e) => onChange(slot.key, e.target.value)}
          className="h-9 w-9 cursor-pointer rounded-lg border border-border bg-transparent p-0.5"
        />
      </div>
      <input
        type="text"
        value={color}
        onChange={(e) => onChange(slot.key, e.target.value)}
        className={`${inputClass} flex-1 font-mono text-xs`}
        maxLength={7}
      />
    </div>
  )
}

function SelectSlotEditor({ slot, value, onChange }: SlotEditorProps) {
  return (
    <select
      value={(value as string) || (slot.default as string) || ''}
      onChange={(e) => onChange(slot.key, e.target.value)}
      className={inputClass}
    >
      <option value="">Seleccionar...</option>
      {slot.options?.map((opt) => (
        <option key={opt} value={opt}>
          {opt}
        </option>
      ))}
    </select>
  )
}

function BooleanSlotEditor({ slot, value, onChange }: SlotEditorProps) {
  return (
    <label className="flex items-center gap-2 cursor-pointer">
      <input
        type="checkbox"
        checked={(value as boolean) || false}
        onChange={(e) => onChange(slot.key, e.target.checked)}
        className="accent-vulkran h-4 w-4"
      />
      <span className="text-sm text-foreground">{slot.label}</span>
    </label>
  )
}

function ImageUrlSlotEditor({ slot, value, onChange }: SlotEditorProps) {
  const url = (value as string) || ''
  return (
    <div className="space-y-2">
      <input
        type="url"
        value={url}
        onChange={(e) => onChange(slot.key, e.target.value)}
        placeholder="https://..."
        className={inputClass}
      />
      {url && (
        <div className="relative h-20 w-full overflow-hidden rounded-lg border border-border bg-surface-1">
          <img src={url} alt={slot.label} className="h-full w-full object-cover" />
        </div>
      )}
    </div>
  )
}

function TextArraySlotEditor({ slot, value, onChange }: SlotEditorProps) {
  const items = (value as string[]) || []

  const addItem = () => onChange(slot.key, [...items, ''])
  const removeItem = (idx: number) => onChange(slot.key, items.filter((_, i) => i !== idx))
  const updateItem = (idx: number, text: string) => {
    const updated = [...items]
    updated[idx] = text
    onChange(slot.key, updated)
  }

  return (
    <div className="space-y-2">
      {items.map((item, idx) => (
        <div key={idx} className="flex items-center gap-2">
          <span className="text-xs text-muted-foreground w-5 text-right shrink-0">{idx + 1}.</span>
          <input
            type="text"
            value={item}
            onChange={(e) => updateItem(idx, e.target.value)}
            placeholder={`Item ${idx + 1}`}
            className={`${inputClass} flex-1`}
          />
          <button
            onClick={() => removeItem(idx)}
            className="rounded-lg p-1.5 text-muted-foreground hover:text-error hover:bg-error/10 transition-all shrink-0"
          >
            <X className="h-3.5 w-3.5" />
          </button>
        </div>
      ))}
      <button
        onClick={addItem}
        className="flex items-center gap-1.5 text-xs text-vulkran-light hover:text-vulkran transition-colors"
      >
        <Plus className="h-3.5 w-3.5" />
        Añadir item
      </button>
    </div>
  )
}

const EDITORS: Record<string, React.FC<SlotEditorProps>> = {
  text: TextSlotEditor,
  textarea: TextareaSlotEditor,
  number: NumberSlotEditor,
  color: ColorSlotEditor,
  select: SelectSlotEditor,
  boolean: BooleanSlotEditor,
  image_url: ImageUrlSlotEditor,
  text_array: TextArraySlotEditor,
}

export function SlotEditor({ slot, value, onChange }: SlotEditorProps) {
  const Editor = EDITORS[slot.type] || TextSlotEditor

  if (slot.type === 'boolean') {
    return <Editor slot={slot} value={value} onChange={onChange} />
  }

  return (
    <div>
      <label className="mb-1.5 flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
        {slot.type === 'color' && <Palette className="h-3 w-3" />}
        {slot.type === 'image_url' && <Image className="h-3 w-3" />}
        {slot.label}
        {slot.required && <span className="text-error">*</span>}
      </label>
      <Editor slot={slot} value={value} onChange={onChange} />
    </div>
  )
}

interface SlotGroupProps {
  slots: SlotDef[]
  data: Record<string, unknown>
  onChange: (key: string, value: unknown) => void
}

export function SlotGroup({ slots, data, onChange }: SlotGroupProps) {
  const groups = new Map<string, SlotDef[]>()

  slots.forEach((slot) => {
    const group = slot.group || 'general'
    if (!groups.has(group)) groups.set(group, [])
    groups.get(group)!.push(slot)
  })

  return (
    <div className="space-y-4">
      {Array.from(groups.entries()).map(([groupName, groupSlots]) => (
        <div key={groupName}>
          {groupName !== 'general' && (
            <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              {groupName}
            </p>
          )}
          <div className="space-y-3">
            {groupSlots.map((slot) => (
              <SlotEditor
                key={slot.key}
                slot={slot}
                value={data[slot.key]}
                onChange={onChange}
              />
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}
