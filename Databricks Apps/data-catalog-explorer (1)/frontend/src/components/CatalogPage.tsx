import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Database, Layers } from 'lucide-react';
import Breadcrumbs from './Breadcrumbs';
import { catalogApi } from '../services/catalogApi';
import type { Catalog } from '../types';

export default function CatalogPage() {
  const navigate = useNavigate();
  const [catalogs, setCatalogs] = useState<Catalog[]>([]);

  useEffect(() => {
    catalogApi.listCatalogs().then(setCatalogs);
  }, []);

  return (
    <div className="max-w-6xl mx-auto">
      <Breadcrumbs items={[{ label: 'Catalogos' }]} />

      <div className="flex items-center gap-3 mb-6">
        <Database className="w-7 h-7 text-indigo-600" />
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Catalogos de Dados</h1>
          <p className="text-gray-500 text-sm">Explore os catalogos de dados da organizacao</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {catalogs.map(cat => (
          <button
            key={cat.id}
            onClick={() => navigate(`/catalogo/${cat.id}`)}
            className="card hover:shadow-md transition-all hover:border-indigo-200 text-left"
          >
            <div className="flex items-start gap-3">
              <div className="p-2 bg-indigo-100 rounded-lg shrink-0">
                <Database className="w-5 h-5 text-indigo-600" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="font-semibold text-gray-800">{cat.name}</div>
                <p className="text-sm text-gray-500 mt-1 line-clamp-2">{cat.description}</p>
                <div className="flex items-center gap-3 mt-3 text-xs text-gray-400">
                  <span className="flex items-center gap-1">
                    <Layers className="w-3.5 h-3.5" /> {cat.schemaCount} schemas
                  </span>
                  <span>{cat.owner}</span>
                </div>
                <div className="flex flex-wrap gap-1.5 mt-2">
                  {cat.tags.map(tag => (
                    <span key={tag} className="badge bg-gray-100 text-gray-600">{tag}</span>
                  ))}
                </div>
              </div>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
