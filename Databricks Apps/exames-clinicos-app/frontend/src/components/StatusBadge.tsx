interface StatusBadgeProps {
  status: string
  size?: 'sm' | 'md'
}

const statusMap: Record<string, string> = {
  normal: 'badge-normal',
  alterado: 'badge-alterado',
  critico: 'badge-critico',
  pendente: 'badge-pendente',
  processando: 'badge-processando',
  concluido: 'badge-concluido',
}

export default function StatusBadge({ status, size = 'sm' }: StatusBadgeProps) {
  const s = (status || '').toLowerCase()
  const cls = statusMap[s] || 'badge-erro'
  const text = size === 'md' ? 'text-sm px-3 py-1' : 'text-xs px-2 py-0.5'
  return <span className={`badge ${cls} ${text}`}>{status || 'N/A'}</span>
}
