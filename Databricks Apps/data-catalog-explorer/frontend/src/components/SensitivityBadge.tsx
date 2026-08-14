import { Lock, Shield, Eye, Globe } from 'lucide-react';
import type { Sensitivity } from '../types';

const config: Partial<Record<Sensitivity, { bg: string; icon: React.ReactNode; label: string; tooltip: string }>> & Record<string, { bg: string; icon: React.ReactNode; label: string; tooltip: string }> = {
  'Publico': {
    bg: 'bg-green-100 text-green-800',
    icon: <Globe className="w-3 h-3" />,
    label: 'Público',
    tooltip: 'Dados públicos, sem restrição de acesso',
  },
  'Público': {
    bg: 'bg-green-100 text-green-800',
    icon: <Globe className="w-3 h-3" />,
    label: 'Público',
    tooltip: 'Dados públicos, sem restrição de acesso',
  },
  'Interno': {
    bg: 'bg-yellow-100 text-yellow-800',
    icon: <Eye className="w-3 h-3" />,
    label: 'Interno',
    tooltip: 'Dados de uso interno da empresa',
  },
  'Confidencial': {
    bg: 'bg-orange-100 text-orange-800',
    icon: <Shield className="w-3 h-3" />,
    label: 'Confidencial',
    tooltip: 'Dados confidenciais, acesso restrito por funcao',
  },
  'PII': {
    bg: 'bg-red-100 text-red-800',
    icon: <Lock className="w-3 h-3" />,
    label: 'PII',
    tooltip: 'Dados pessoais identificaveis, protegidos por LGPD',
  },
};

export default function SensitivityBadge({ sensitivity, showTooltip = true }: { sensitivity: Sensitivity; showTooltip?: boolean }) {
  const c = config[sensitivity] ?? config['Publico']!;
  return (
    <span className={`badge ${c.bg} gap-1 relative group cursor-default`}>
      {c.icon}
      {c.label}
      {showTooltip && (
        <span className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-2 py-1 text-xs bg-gray-900 text-white rounded whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-50">
          {c.tooltip}
        </span>
      )}
    </span>
  );
}
