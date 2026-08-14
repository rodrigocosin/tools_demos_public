import { X, Filter } from 'lucide-react';
import { useStore } from '../store/useStore';
import { catalogApi } from '../services/catalogApi';
import type { Domain, Sensitivity, ObjectType, ObjectStatus } from '../types';

const DOMAINS: Domain[] = ['Vendas', 'Financeiro', 'Marketing', 'Operacoes', 'RH', 'Data Platform', 'CRM'];
const SENSITIVITIES: Sensitivity[] = ['Publico', 'Interno', 'Confidencial', 'PII'];
const TYPES: ObjectType[] = ['TABLE', 'VIEW'];
const STATUSES: ObjectStatus[] = ['ACTIVE', 'DEPRECATED'];

function typeLabel(t: ObjectType) { return t === 'TABLE' ? 'Tabela' : 'View'; }
function statusLabel(s: ObjectStatus) { return s === 'ACTIVE' ? 'Ativo' : 'Descontinuado'; }

export default function FilterPanel() {
  const { filters, setFilters, clearFilters } = useStore();
  const owners = catalogApi.getAllOwners();

  const activeCount = [
    filters.domain?.length ?? 0,
    filters.owner?.length ?? 0,
    filters.sensitivity?.length ?? 0,
    filters.type?.length ?? 0,
    filters.status?.length ?? 0,
  ].reduce((a, b) => a + b, 0);

  function toggleArrayFilter<T>(key: keyof typeof filters, value: T) {
    const current = (filters[key] as T[] | undefined) || [];
    const next = current.includes(value)
      ? current.filter(v => v !== value)
      : [...current, value];
    setFilters({ ...filters, [key]: next.length ? next : undefined });
  }

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Filter className="w-4 h-4 text-gray-600" />
          <span className="font-semibold text-sm text-gray-800">Filtros</span>
          {activeCount > 0 && (
            <span className="badge bg-indigo-100 text-indigo-700">{activeCount}</span>
          )}
        </div>
        {activeCount > 0 && (
          <button onClick={clearFilters} className="text-xs text-indigo-600 hover:text-indigo-800 flex items-center gap-1">
            <X className="w-3 h-3" /> Limpar
          </button>
        )}
      </div>

      <div className="space-y-4">
        <FilterSection title="Dominio">
          {DOMAINS.map(d => (
            <FilterCheckbox key={d} label={d} checked={filters.domain?.includes(d) ?? false}
              onChange={() => toggleArrayFilter('domain', d)} />
          ))}
        </FilterSection>

        <FilterSection title="Tipo">
          {TYPES.map(t => (
            <FilterCheckbox key={t} label={typeLabel(t)} checked={filters.type?.includes(t) ?? false}
              onChange={() => toggleArrayFilter('type', t)} />
          ))}
        </FilterSection>

        <FilterSection title="Sensibilidade">
          {SENSITIVITIES.map(s => (
            <FilterCheckbox key={s} label={s} checked={filters.sensitivity?.includes(s) ?? false}
              onChange={() => toggleArrayFilter('sensitivity', s)} />
          ))}
        </FilterSection>

        <FilterSection title="Status">
          {STATUSES.map(s => (
            <FilterCheckbox key={s} label={statusLabel(s)} checked={filters.status?.includes(s) ?? false}
              onChange={() => toggleArrayFilter('status', s)} />
          ))}
        </FilterSection>

        <FilterSection title="Responsavel">
          {owners.map(o => (
            <FilterCheckbox key={o} label={o} checked={filters.owner?.includes(o) ?? false}
              onChange={() => toggleArrayFilter('owner', o)} />
          ))}
        </FilterSection>
      </div>
    </div>
  );
}

function FilterSection({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <div className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">{title}</div>
      <div className="space-y-1.5">{children}</div>
    </div>
  );
}

function FilterCheckbox({ label, checked, onChange }: { label: string; checked: boolean; onChange: () => void }) {
  return (
    <label className="flex items-center gap-2 cursor-pointer hover:bg-gray-50 px-1 py-0.5 rounded text-sm">
      <input type="checkbox" checked={checked} onChange={onChange}
        className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500 w-3.5 h-3.5" />
      <span className="text-gray-700">{label}</span>
    </label>
  );
}
