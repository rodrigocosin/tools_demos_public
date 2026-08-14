import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Layers, Table2 } from 'lucide-react';
import Breadcrumbs from './Breadcrumbs';
import { catalogApi } from '../services/catalogApi';
import { domainConfig } from '../data/catalog';
import type { Schema, Catalog } from '../types';

export default function SchemaPage() {
  const { catalogId } = useParams<{ catalogId: string }>();
  const navigate = useNavigate();
  const [catalog, setCatalog] = useState<Catalog | null>(null);
  const [schemas, setSchemas] = useState<Schema[]>([]);

  useEffect(() => {
    if (!catalogId) return;
    const cat = catalogApi.getCatalogById(catalogId);
    setCatalog(cat ?? null);
    catalogApi.listSchemas(catalogId).then(setSchemas);
  }, [catalogId]);

  if (!catalog) return null;

  return (
    <div className="max-w-6xl mx-auto">
      <Breadcrumbs items={[
        { label: 'Catalogos', to: '/catalogo' },
        { label: catalog.name },
      ]} />

      <div className="flex items-center gap-3 mb-6">
        <Layers className="w-7 h-7 text-indigo-600" />
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{catalog.name}</h1>
          <p className="text-gray-500 text-sm">{catalog.description}</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {schemas.map(sch => {
          const cfg = domainConfig[sch.domain] || { icon: '\u{1F4CA}', color: 'bg-gray-100 text-gray-800' };
          return (
            <button
              key={sch.id}
              onClick={() => navigate(`/catalogo/${catalogId}/${sch.id}`)}
              className="card hover:shadow-md transition-all hover:border-indigo-200 text-left"
            >
              <div className="flex items-start gap-3">
                <div className="text-2xl">{cfg.icon}</div>
                <div className="flex-1 min-w-0">
                  <div className="font-semibold text-gray-800">{sch.name}</div>
                  <span className={`badge ${cfg.color} mt-1`}>{sch.domain}</span>
                  <p className="text-sm text-gray-500 mt-2 line-clamp-2">{sch.description}</p>
                  <div className="flex items-center gap-3 mt-3 text-xs text-gray-400">
                    <span className="flex items-center gap-1">
                      <Table2 className="w-3.5 h-3.5" /> {sch.tableCount} objetos
                    </span>
                    <span>{sch.owner}</span>
                  </div>
                </div>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
