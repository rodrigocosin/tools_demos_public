import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, X } from 'lucide-react';
import { catalogApi } from '../services/catalogApi';
import { useStore } from '../store/useStore';
import type { DataObject } from '../types';

interface Props {
  large?: boolean;
  className?: string;
}

export default function SearchBar({ large = false, className = '' }: Props) {
  const navigate = useNavigate();
  const { searchQuery, setSearchQuery } = useStore();
  const [localQuery, setLocalQuery] = useState(searchQuery);
  const [suggestions, setSuggestions] = useState<DataObject[]>([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const timer = setTimeout(async () => {
      if (localQuery.length >= 2) {
        const results = await catalogApi.search(localQuery);
        setSuggestions(results.slice(0, 6));
        setShowSuggestions(true);
      } else {
        setSuggestions([]);
        setShowSuggestions(false);
      }
    }, 300);
    return () => clearTimeout(timer);
  }, [localQuery]);

  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setShowSuggestions(false);
      }
    };
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, []);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (localQuery.trim()) {
      setSearchQuery(localQuery.trim());
      setShowSuggestions(false);
      navigate(`/busca?q=${encodeURIComponent(localQuery.trim())}`);
    }
  };

  const handleSelect = (obj: DataObject) => {
    setShowSuggestions(false);
    setLocalQuery('');
    navigate(`/catalogo/${obj.catalogId}/${obj.schemaId}/${obj.id}`);
  };

  const clear = () => {
    setLocalQuery('');
    setSearchQuery('');
    setSuggestions([]);
    setShowSuggestions(false);
  };

  return (
    <div ref={ref} className={`relative ${className}`}>
      <form onSubmit={handleSubmit}>
        <div className="relative">
          <Search className={`absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 ${large ? 'w-5 h-5' : 'w-4 h-4'}`} />
          <input
            type="text"
            value={localQuery}
            onChange={e => setLocalQuery(e.target.value)}
            onFocus={() => suggestions.length > 0 && setShowSuggestions(true)}
            placeholder="Buscar dados... ex: receita, cliente, churn"
            className={`w-full border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none transition-all ${
              large ? 'pl-11 pr-10 py-3.5 text-lg' : 'pl-9 pr-9 py-2 text-sm'
            }`}
          />
          {localQuery && (
            <button type="button" onClick={clear} className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600">
              <X className={large ? 'w-5 h-5' : 'w-4 h-4'} />
            </button>
          )}
        </div>
      </form>

      {showSuggestions && suggestions.length > 0 && (
        <div className="absolute z-50 w-full mt-1 bg-white border border-gray-200 rounded-lg shadow-lg overflow-hidden">
          {suggestions.map(obj => (
            <button
              key={obj.id}
              onClick={() => handleSelect(obj)}
              className="w-full text-left px-4 py-2.5 hover:bg-indigo-50 transition-colors flex items-center justify-between"
            >
              <div>
                <div className="font-medium text-gray-800 text-sm">{obj.friendlyName}</div>
                <div className="text-xs text-gray-500">{obj.name} &middot; {obj.domain}</div>
              </div>
              <span className={`badge text-xs ${obj.type === 'TABLE' ? 'bg-blue-100 text-blue-800' : 'bg-violet-100 text-violet-800'}`}>
                {obj.type === 'TABLE' ? 'Tabela' : 'View'}
              </span>
            </button>
          ))}
          <button
            onClick={handleSubmit}
            className="w-full text-left px-4 py-2.5 bg-gray-50 hover:bg-gray-100 transition-colors text-sm text-indigo-600 font-medium border-t"
          >
            Ver todos os resultados para "{localQuery}"
          </button>
        </div>
      )}
    </div>
  );
}
