import { useState, useEffect } from 'react';
import { useParams, useSearchParams } from 'react-router-dom';
import { Table2 } from 'lucide-react';
import Breadcrumbs from './Breadcrumbs';
import FilterPanel from './FilterPanel';
import ObjectTable from './ObjectTable';
import { catalogApi } from '../services/catalogApi';
import { useStore } from '../store/useStore';
import type { DataObject, Schema, Catalog } from '../types';
import type { Domain } from '../types';

export default function ObjectListPage() {
  const { catalogId, schemaId } = useParams<{ catalogId: string; schemaId: string }>();
  const [searchParams] = useSearchParams();
  const { filters } = useStore();
  const [objects, setObjects] = useState<DataObject[]>([]);
  const [schema, setSchema] = useState<Schema | null>(null);
  const [catalog, setCatalog] = useState<Catalog | null>(null);

  const searchQuery = searchParams.get('q') ?? undefined;
  const domainFilter = searchParams.get('domain') as Domain | null;

  useEffect(() => {
    if (catalogId) {
      setCatalog(catalogApi.getCatalogById(catalogId) ?? null);
    }
    if (schemaId) {
      setSchema(catalogApi.getSchemaById(schemaId) ?? null);
    }
  }, [catalogId, schemaId]);

  useEffect(() => {
    const effectiveFilters = { ...filters };
    if (domainFilter) {
      effectiveFilters.domain = [domainFilter];
    }

    if (schemaId) {
      catalogApi.listObjects(schemaId, effectiveFilters).then(setObjects);
    } else if (searchQuery !== undefined) {
      catalogApi.search(searchQuery || '', effectiveFilters).then(setObjects);
    } else {
      catalogApi.getAllObjects(effectiveFilters).then(setObjects);
    }
  }, [schemaId, searchQuery, filters, domainFilter]);

  const crumbs = [];
  if (catalogId && catalog) {
    crumbs.push({ label: 'Catalogos', to: '/catalogo' });
    crumbs.push({ label: catalog.name, to: `/catalogo/${catalogId}` });
  }
  if (schema) {
    crumbs.push({ label: schema.name });
  } else if (searchQuery !== undefined) {
    crumbs.push({ label: `Busca: "${searchQuery || 'todos'}"` });
  }

  const title = schema
    ? schema.name
    : searchQuery !== undefined
      ? `Resultados da busca${searchQuery ? ` para "${searchQuery}"` : ''}`
      : domainFilter
        ? `Datasets: ${domainFilter}`
        : 'Todos os Datasets';

  return (
    <div className="max-w-6xl mx-auto">
      <Breadcrumbs items={crumbs.length ? crumbs : [{ label: title }]} />

      <div className="flex items-center gap-3 mb-6">
        <Table2 className="w-7 h-7 text-indigo-600" />
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{title}</h1>
          <p className="text-gray-500 text-sm">{objects.length} dataset{objects.length !== 1 ? 's' : ''} encontrado{objects.length !== 1 ? 's' : ''}</p>
        </div>
      </div>

      <div className="flex gap-6">
        <aside className="w-64 shrink-0 hidden lg:block">
          <FilterPanel />
        </aside>
        <main className="flex-1 min-w-0">
          <div className="card">
            <ObjectTable objects={objects} />
          </div>
        </main>
      </div>
    </div>
  );
}
