import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { BookOpen, Search } from 'lucide-react';
import Breadcrumbs from './Breadcrumbs';
import { catalogApi } from '../services/catalogApi';
import { domainConfig } from '../data/catalog';
import type { GlossaryTerm, Domain } from '../types';

export default function GlossaryPage() {
  const [terms, setTerms] = useState<GlossaryTerm[]>([]);
  const [search, setSearch] = useState('');
  const [domainFilter, setDomainFilter] = useState<string>('all');

  useEffect(() => {
    catalogApi.getGlossary().then(setTerms);
  }, []);

  const filtered = terms.filter(t => {
    if (domainFilter !== 'all' && t.domain !== domainFilter) return false;
    if (search) {
      const q = search.toLowerCase();
      return t.term.toLowerCase().includes(q) || t.definition.toLowerCase().includes(q);
    }
    return true;
  });

  const domains = [...new Set(terms.map(t => t.domain).filter((d): d is string => !!d))].sort();

  return (
    <div className="max-w-4xl mx-auto">
      <Breadcrumbs items={[{ label: 'Glossario de Negocios' }]} />

      <div className="flex items-center gap-3 mb-6">
        <BookOpen className="w-7 h-7 text-purple-600" />
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Glossario de Negocios</h1>
          <p className="text-gray-500 text-sm">Definicoes de termos e metricas utilizados nos dados</p>
        </div>
      </div>

      {/* Search and filters */}
      <div className="flex flex-col sm:flex-row gap-3 mb-6">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Buscar termo..."
            className="w-full pl-9 pr-4 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-purple-500 focus:border-purple-500 outline-none"
          />
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <button onClick={() => setDomainFilter('all')}
            className={`badge cursor-pointer ${domainFilter === 'all' ? 'bg-purple-100 text-purple-800' : 'bg-gray-100 text-gray-600'}`}>
            Todos
          </button>
          {domains.map(d => (
            <button key={d} onClick={() => setDomainFilter(d)}
              className={`badge cursor-pointer ${domainFilter === d ? 'bg-purple-100 text-purple-800' : 'bg-gray-100 text-gray-600'}`}>
              {d}
            </button>
          ))}
        </div>
      </div>

      {/* Terms list */}
      <div className="space-y-4">
        {filtered.map(term => {
          const cfg = (domainConfig as Record<string, { icon: string; color: string }>)[term.domain ?? ''] || { icon: '📊', color: 'bg-gray-100 text-gray-800' };
          return (
            <div key={term.id} className="card">
              <div className="flex items-start justify-between gap-3">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <h3 className="text-lg font-semibold text-gray-800">{term.term}</h3>
                    <span className={`badge ${cfg.color}`}>{cfg.icon} {term.domain}</span>
                  </div>
                  <p className="text-gray-600 text-sm leading-relaxed">{term.definition}</p>

                  {(term.examples?.length ?? 0) > 0 && (
                    <div className="mt-3">
                      <div className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1">Exemplos</div>
                      <ul className="space-y-1">
                        {(term.examples ?? []).map((ex, i) => (
                          <li key={i} className="text-sm text-gray-500 flex items-start gap-1.5">
                            <span className="text-purple-400 mt-0.5 shrink-0">&#9679;</span> {ex}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {term.relatedTableIds.length > 0 && (
                    <div className="mt-3">
                      <div className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1">Datasets Relacionados</div>
                      <div className="flex flex-wrap gap-1.5">
                        {term.relatedTableIds.map(id => {
                          const obj = catalogApi.getObjectById(id);
                          if (!obj) return null;
                          return (
                            <Link key={id} to={`/catalogo/${obj.catalogId}/${obj.schemaId}/${obj.id}`}
                              className="badge bg-indigo-50 text-indigo-700 hover:bg-indigo-100 transition-colors cursor-pointer">
                              {obj.friendlyName}
                            </Link>
                          );
                        })}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          );
        })}

        {filtered.length === 0 && (
          <div className="text-center py-12 text-gray-500">
            <BookOpen className="w-10 h-10 mx-auto mb-3 text-gray-300" />
            <p>Nenhum termo encontrado</p>
          </div>
        )}
      </div>
    </div>
  );
}
