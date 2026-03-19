import { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Database, Star, TrendingUp, Clock, BookOpen, ArrowRight } from 'lucide-react';
import SearchBar from './SearchBar';
import DomainCards from './DomainCards';
import { catalogApi } from '../services/catalogApi';
import { useStore } from '../store/useStore';
import type { DataObject } from '../types';

function ObjectCard({ obj }: { obj: DataObject }) {
  const navigate = useNavigate();
  return (
    <button
      onClick={() => navigate(`/catalogo/${obj.catalogId}/${obj.schemaId}/${obj.id}`)}
      className="card hover:shadow-md transition-all hover:border-indigo-200 text-left w-full"
    >
      <div className="flex items-start justify-between">
        <div className="flex-1 min-w-0">
          <div className="font-semibold text-gray-800 text-sm truncate">{obj.friendlyName}</div>
          <div className="text-xs text-gray-400 font-mono truncate mt-0.5">{obj.name}</div>
        </div>
        <span className={`badge text-xs ml-2 shrink-0 ${obj.type === 'TABLE' ? 'bg-blue-100 text-blue-800' : 'bg-violet-100 text-violet-800'}`}>
          {obj.type === 'TABLE' ? 'Tabela' : 'View'}
        </span>
      </div>
      <p className="text-xs text-gray-500 mt-2 line-clamp-2">{obj.description}</p>
      <div className="flex items-center gap-2 mt-2">
        <span className="text-xs text-gray-400">{obj.domain}</span>
        <span className="text-gray-300">&middot;</span>
        <div className="flex items-center gap-1">
          <div className="w-10 bg-gray-200 rounded-full h-1">
            <div className="h-1 rounded-full bg-indigo-500" style={{ width: `${obj.popularityScore}%` }} />
          </div>
          <span className="text-xs text-gray-400">{obj.popularityScore}</span>
        </div>
      </div>
    </button>
  );
}

export default function HomePage() {
  const { favorites } = useStore();
  const [popular, setPopular] = useState<DataObject[]>([]);
  const [recent, setRecent] = useState<DataObject[]>([]);
  const [favObjects, setFavObjects] = useState<DataObject[]>([]);

  useEffect(() => {
    catalogApi.getPopular().then(setPopular);
    catalogApi.getRecent().then(setRecent);
  }, []);

  useEffect(() => {
    Promise.all(favorites.map(id => catalogApi.getObjectDetails(id)))
      .then(results => setFavObjects(results.filter(Boolean) as DataObject[]));
  }, [favorites]);

  return (
    <div className="max-w-6xl mx-auto">
      {/* Hero */}
      <div className="text-center py-12">
        <div className="flex items-center justify-center gap-3 mb-4">
          <Database className="w-10 h-10 text-indigo-600" />
          <h1 className="text-3xl font-bold text-gray-900">Data Catalog Explorer</h1>
        </div>
        <p className="text-gray-500 text-lg mb-8 max-w-2xl mx-auto">
          Encontre, entenda e utilize os dados da empresa com confianca. Explore catalogos, entenda a linhagem e solicite acesso.
        </p>
        <SearchBar large className="max-w-2xl mx-auto" />
      </div>

      {/* Domain cards */}
      <section className="mb-10">
        <h2 className="text-lg font-semibold text-gray-800 mb-4 flex items-center gap-2">
          <Database className="w-5 h-5 text-indigo-600" /> Dominios de Dados
        </h2>
        <DomainCards />
      </section>

      {/* Popular */}
      <section className="mb-10">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-gray-800 flex items-center gap-2">
            <TrendingUp className="w-5 h-5 text-indigo-600" /> Mais Acessados
          </h2>
          <Link to="/busca?q=" className="text-sm text-indigo-600 hover:text-indigo-800 flex items-center gap-1">
            Ver todos <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {popular.slice(0, 6).map(obj => <ObjectCard key={obj.id} obj={obj} />)}
        </div>
      </section>

      {/* Favorites */}
      {favObjects.length > 0 && (
        <section className="mb-10">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-800 flex items-center gap-2">
              <Star className="w-5 h-5 text-amber-500" /> Favoritos
            </h2>
            <Link to="/favoritos" className="text-sm text-indigo-600 hover:text-indigo-800 flex items-center gap-1">
              Ver todos <ArrowRight className="w-4 h-4" />
            </Link>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {favObjects.slice(0, 3).map(obj => <ObjectCard key={obj.id} obj={obj} />)}
          </div>
        </section>
      )}

      {/* Recent */}
      <section className="mb-10">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-gray-800 flex items-center gap-2">
            <Clock className="w-5 h-5 text-indigo-600" /> Atualizados Recentemente
          </h2>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {recent.slice(0, 6).map(obj => <ObjectCard key={obj.id} obj={obj} />)}
        </div>
      </section>

      {/* Quick links */}
      <section className="mb-10">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <Link to="/catalogo" className="card hover:shadow-md transition-all hover:border-indigo-200 flex items-center gap-4">
            <div className="p-3 bg-indigo-100 rounded-lg">
              <Database className="w-6 h-6 text-indigo-600" />
            </div>
            <div>
              <div className="font-semibold text-gray-800">Explorar Catalogos</div>
              <div className="text-sm text-gray-500">Navegue pela estrutura completa de dados</div>
            </div>
          </Link>
          <Link to="/glossario" className="card hover:shadow-md transition-all hover:border-indigo-200 flex items-center gap-4">
            <div className="p-3 bg-purple-100 rounded-lg">
              <BookOpen className="w-6 h-6 text-purple-600" />
            </div>
            <div>
              <div className="font-semibold text-gray-800">Glossario de Negocios</div>
              <div className="text-sm text-gray-500">Definicoes de termos e metricas</div>
            </div>
          </Link>
        </div>
      </section>
    </div>
  );
}
