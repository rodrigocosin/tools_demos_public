import { useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowUpDown, AlertTriangle, ChevronLeft, ChevronRight } from 'lucide-react';
import type { DataObject } from '../types';
import SensitivityBadge from './SensitivityBadge';

interface Props {
  objects: DataObject[];
  pageSize?: number;
}

type SortKey = 'friendlyName' | 'type' | 'domain' | 'owner' | 'sensitivity' | 'lastUpdated' | 'popularityScore';

function relativeTime(dateStr: string): string {
  const now = new Date('2026-03-09T09:00:00Z');
  const date = new Date(dateStr);
  const diffMs = now.getTime() - date.getTime();
  const diffMin = Math.floor(diffMs / 60000);
  if (diffMin < 60) return `ha ${diffMin} min`;
  const diffH = Math.floor(diffMin / 60);
  if (diffH < 24) return `ha ${diffH}h`;
  const diffD = Math.floor(diffH / 24);
  if (diffD < 30) return `ha ${diffD}d`;
  const diffM = Math.floor(diffD / 30);
  return `ha ${diffM} mes${diffM > 1 ? 'es' : ''}`;
}

export default function ObjectTable({ objects, pageSize = 10 }: Props) {
  const navigate = useNavigate();
  const [sortKey, setSortKey] = useState<SortKey>('popularityScore');
  const [sortAsc, setSortAsc] = useState(false);
  const [page, setPage] = useState(0);

  const sorted = useMemo(() => {
    const arr = [...objects];
    arr.sort((a, b) => {
      let cmp = 0;
      if (sortKey === 'popularityScore') cmp = a.popularityScore - b.popularityScore;
      else if (sortKey === 'lastUpdated') cmp = new Date(a.lastUpdated).getTime() - new Date(b.lastUpdated).getTime();
      else {
        const av = a[sortKey] as string;
        const bv = b[sortKey] as string;
        cmp = av.localeCompare(bv);
      }
      return sortAsc ? cmp : -cmp;
    });
    return arr;
  }, [objects, sortKey, sortAsc]);

  const totalPages = Math.ceil(sorted.length / pageSize);
  const pageItems = sorted.slice(page * pageSize, (page + 1) * pageSize);

  function toggleSort(key: SortKey) {
    if (sortKey === key) setSortAsc(!sortAsc);
    else { setSortKey(key); setSortAsc(true); }
  }

  function SortHeader({ label, sKey }: { label: string; sKey: SortKey }) {
    return (
      <th className="px-3 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider cursor-pointer hover:text-gray-700 select-none"
        onClick={() => toggleSort(sKey)}>
        <span className="flex items-center gap-1">
          {label}
          <ArrowUpDown className={`w-3 h-3 ${sortKey === sKey ? 'text-indigo-600' : 'text-gray-400'}`} />
        </span>
      </th>
    );
  }

  if (objects.length === 0) {
    return (
      <div className="text-center py-12 text-gray-500">
        <p className="text-lg font-medium">Nenhum resultado encontrado</p>
        <p className="text-sm mt-1">Tente ajustar os filtros ou a busca</p>
      </div>
    );
  }

  return (
    <div>
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              <SortHeader label="Nome" sKey="friendlyName" />
              <SortHeader label="Tipo" sKey="type" />
              <SortHeader label="Dominio" sKey="domain" />
              <SortHeader label="Responsavel" sKey="owner" />
              <SortHeader label="Sensibilidade" sKey="sensitivity" />
              <SortHeader label="Atualizacao" sKey="lastUpdated" />
              <SortHeader label="Popularidade" sKey="popularityScore" />
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {pageItems.map(obj => (
              <tr key={obj.id}
                onClick={() => navigate(`/catalogo/${obj.catalogId}/${obj.schemaId}/${obj.id}`)}
                className="hover:bg-indigo-50/50 cursor-pointer transition-colors">
                <td className="px-3 py-3">
                  <div className={`font-medium text-sm ${obj.status === 'DEPRECATED' ? 'line-through text-gray-400' : 'text-gray-800'}`}>
                    {obj.friendlyName}
                  </div>
                  <div className="text-xs text-gray-400 font-mono">{obj.name}</div>
                  {obj.status === 'DEPRECATED' && (
                    <span className="inline-flex items-center gap-1 text-xs text-amber-600 mt-0.5">
                      <AlertTriangle className="w-3 h-3" /> Descontinuada
                    </span>
                  )}
                </td>
                <td className="px-3 py-3">
                  <span className={`badge ${obj.type === 'TABLE' ? 'bg-blue-100 text-blue-800' : 'bg-violet-100 text-violet-800'}`}>
                    {obj.type === 'TABLE' ? 'Tabela' : 'View'}
                  </span>
                </td>
                <td className="px-3 py-3 text-sm text-gray-700">{obj.domain}</td>
                <td className="px-3 py-3 text-sm text-gray-700">{obj.owner}</td>
                <td className="px-3 py-3"><SensitivityBadge sensitivity={obj.sensitivity} /></td>
                <td className="px-3 py-3 text-sm text-gray-500">{relativeTime(obj.lastUpdated)}</td>
                <td className="px-3 py-3">
                  <div className="flex items-center gap-2">
                    <div className="w-16 bg-gray-200 rounded-full h-1.5">
                      <div className="h-1.5 rounded-full bg-indigo-500" style={{ width: `${obj.popularityScore}%` }} />
                    </div>
                    <span className="text-xs text-gray-500 w-7">{obj.popularityScore}</span>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {totalPages > 1 && (
        <div className="flex items-center justify-between mt-4 pt-4 border-t border-gray-100">
          <span className="text-sm text-gray-500">
            {page * pageSize + 1}-{Math.min((page + 1) * pageSize, sorted.length)} de {sorted.length} resultados
          </span>
          <div className="flex items-center gap-2">
            <button onClick={() => setPage(Math.max(0, page - 1))} disabled={page === 0}
              className="p-1.5 rounded hover:bg-gray-100 disabled:opacity-30 disabled:cursor-not-allowed">
              <ChevronLeft className="w-4 h-4" />
            </button>
            {Array.from({ length: totalPages }, (_, i) => (
              <button key={i} onClick={() => setPage(i)}
                className={`px-2.5 py-1 text-sm rounded ${page === i ? 'bg-indigo-600 text-white' : 'hover:bg-gray-100 text-gray-600'}`}>
                {i + 1}
              </button>
            ))}
            <button onClick={() => setPage(Math.min(totalPages - 1, page + 1))} disabled={page === totalPages - 1}
              className="p-1.5 rounded hover:bg-gray-100 disabled:opacity-30 disabled:cursor-not-allowed">
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
