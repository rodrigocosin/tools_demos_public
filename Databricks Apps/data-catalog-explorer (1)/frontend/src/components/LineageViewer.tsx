import { useNavigate } from 'react-router-dom';
import { ArrowRight } from 'lucide-react';
import type { LineageEdge, DataObject } from '../types';
import { catalogApi } from '../services/catalogApi';

interface Props {
  objectId: string;
  objectName: string;
  upstream: LineageEdge[];
  downstream: LineageEdge[];
}

function TableBox({ id, isCurrent, onClick }: { id: string; isCurrent?: boolean; onClick?: () => void }) {
  const obj = catalogApi.getObjectById(id);
  if (!obj) return null;
  return (
    <button
      onClick={onClick}
      className={`px-4 py-3 rounded-lg border-2 text-left min-w-[180px] transition-all ${
        isCurrent
          ? 'border-indigo-500 bg-indigo-50 shadow-md'
          : 'border-gray-300 bg-white hover:border-indigo-300 hover:shadow-sm cursor-pointer'
      }`}
    >
      <div className={`font-medium text-sm ${isCurrent ? 'text-indigo-700' : 'text-gray-800'}`}>
        {obj.friendlyName}
      </div>
      <div className="text-xs text-gray-500 font-mono mt-0.5">{obj.name}</div>
      <div className="flex items-center gap-1.5 mt-1.5">
        <span className={`badge text-xs ${obj.type === 'TABLE' ? 'bg-blue-100 text-blue-700' : 'bg-violet-100 text-violet-700'}`}>
          {obj.type === 'TABLE' ? 'Tabela' : 'View'}
        </span>
        <span className="text-xs text-gray-400">{obj.domain}</span>
      </div>
    </button>
  );
}

export default function LineageViewer({ objectId, objectName, upstream, downstream }: Props) {
  const navigate = useNavigate();

  const goTo = (obj: DataObject | undefined) => {
    if (obj) navigate(`/catalogo/${obj.catalogId}/${obj.schemaId}/${obj.id}`);
  };

  if (upstream.length === 0 && downstream.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">
        <p>Nenhuma linhagem mapeada para este dataset.</p>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <div className="flex items-start gap-6 min-w-[600px] py-4">
        {/* Upstream column */}
        {upstream.length > 0 && (
          <>
            <div className="flex flex-col gap-3">
              <div className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1">Fontes (Upstream)</div>
              {upstream.map((edge, i) => (
                <div key={i} className="flex items-center gap-3">
                  <TableBox id={edge.fromTableId} onClick={() => goTo(catalogApi.getObjectById(edge.fromTableId))} />
                  <div className="flex flex-col items-center">
                    <ArrowRight className="w-5 h-5 text-indigo-400" />
                    <span className="text-xs text-gray-400 mt-0.5 whitespace-nowrap">{edge.relationLabel}</span>
                  </div>
                </div>
              ))}
            </div>
          </>
        )}

        {/* Current table */}
        <div className="flex flex-col gap-3">
          <div className="text-xs font-semibold text-indigo-600 uppercase tracking-wider mb-1">Atual</div>
          <TableBox id={objectId} isCurrent />
        </div>

        {/* Downstream column */}
        {downstream.length > 0 && (
          <div className="flex flex-col gap-3">
            <div className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1">Destinos (Downstream)</div>
            {downstream.map((edge, i) => (
              <div key={i} className="flex items-center gap-3">
                <div className="flex flex-col items-center">
                  <ArrowRight className="w-5 h-5 text-indigo-400" />
                  <span className="text-xs text-gray-400 mt-0.5 whitespace-nowrap">{edge.relationLabel}</span>
                </div>
                <TableBox id={edge.toTableId} onClick={() => goTo(catalogApi.getObjectById(edge.toTableId))} />
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
