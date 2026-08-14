import { useState, useEffect } from 'react';
import { Routes, Route, Link, useLocation, useNavigate } from 'react-router-dom';
import { Database, BookOpen, Star, Home, Heart } from 'lucide-react';
import HomePage from './components/HomePage';
import CatalogPage from './components/CatalogPage';
import SchemaPage from './components/SchemaPage';
import ObjectListPage from './components/ObjectListPage';
import ObjectDetailPage from './components/ObjectDetailPage';
import GlossaryPage from './components/GlossaryPage';
import SearchBar from './components/SearchBar';
import ObjectTable from './components/ObjectTable';
import Breadcrumbs from './components/Breadcrumbs';
import { catalogApi } from './services/catalogApi';
import { useStore } from './store/useStore';
import type { DataObject } from './types';

function FavoritesPage() {
  const { favorites } = useStore();
  const [objects, setObjects] = useState<DataObject[]>([]);

  useEffect(() => {
    Promise.all(favorites.map(id => catalogApi.getObjectDetails(id)))
      .then(results => setObjects(results.filter(Boolean) as DataObject[]));
  }, [favorites]);

  return (
    <div className="max-w-6xl mx-auto">
      <Breadcrumbs items={[{ label: 'Favoritos' }]} />
      <div className="flex items-center gap-3 mb-6">
        <Star className="w-7 h-7 text-amber-500" />
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Favoritos</h1>
          <p className="text-gray-500 text-sm">{objects.length} dataset{objects.length !== 1 ? 's' : ''} favoritado{objects.length !== 1 ? 's' : ''}</p>
        </div>
      </div>
      {objects.length > 0 ? (
        <div className="card"><ObjectTable objects={objects} /></div>
      ) : (
        <div className="text-center py-12 text-gray-500 card">
          <Heart className="w-10 h-10 mx-auto mb-3 text-gray-300" />
          <p className="text-lg font-medium">Nenhum favorito ainda</p>
          <p className="text-sm mt-1">Explore o catalogo e marque datasets como favoritos</p>
        </div>
      )}
    </div>
  );
}

function NavBar() {
  const location = useLocation();
  const isHome = location.pathname === '/';

  return (
    <header className="bg-white border-b border-gray-200 sticky top-0 z-40">
      <div className="max-w-7xl mx-auto px-4 sm:px-6">
        <div className="flex items-center justify-between h-14">
          <div className="flex items-center gap-6">
            <Link to="/" className="flex items-center gap-2 font-bold text-gray-900 hover:text-indigo-600 transition-colors">
              <Database className="w-5 h-5 text-indigo-600" />
              <span className="hidden sm:inline">Data Catalog</span>
            </Link>
            <nav className="hidden md:flex items-center gap-1">
              <NavLink to="/" icon={<Home className="w-4 h-4" />} label="Inicio" />
              <NavLink to="/catalogo" icon={<Database className="w-4 h-4" />} label="Catalogos" />
              <NavLink to="/glossario" icon={<BookOpen className="w-4 h-4" />} label="Glossario" />
              <NavLink to="/favoritos" icon={<Star className="w-4 h-4" />} label="Favoritos" />
            </nav>
          </div>
          {!isHome && (
            <div className="w-72 hidden lg:block">
              <SearchBar />
            </div>
          )}
        </div>
      </div>
    </header>
  );
}

function NavLink({ to, icon, label }: { to: string; icon: React.ReactNode; label: string }) {
  const location = useLocation();
  const isActive = to === '/' ? location.pathname === '/' : location.pathname.startsWith(to);
  return (
    <Link to={to} className={`flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
      isActive ? 'bg-indigo-50 text-indigo-700' : 'text-gray-600 hover:bg-gray-100 hover:text-gray-800'
    }`}>
      {icon} {label}
    </Link>
  );
}

function Toast() {
  const { toastMessage, hideToast } = useStore();
  if (!toastMessage) return null;
  return (
    <div className="fixed bottom-6 right-6 z-50 animate-slide-up">
      <div className="bg-gray-900 text-white px-4 py-3 rounded-lg shadow-lg flex items-center gap-3 text-sm">
        <span>{toastMessage}</span>
        <button onClick={hideToast} className="text-gray-400 hover:text-white">&times;</button>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <div className="min-h-screen bg-gray-50">
      <NavBar />
      <main className="px-4 sm:px-6 py-6 max-w-7xl mx-auto">
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/catalogo" element={<CatalogPage />} />
          <Route path="/catalogo/:catalogId" element={<SchemaPage />} />
          <Route path="/catalogo/:catalogId/:schemaId" element={<ObjectListPage />} />
          <Route path="/catalogo/:catalogId/:schemaId/:objectId" element={<ObjectDetailPage />} />
          <Route path="/glossario" element={<GlossaryPage />} />
          <Route path="/busca" element={<ObjectListPage />} />
          <Route path="/favoritos" element={<FavoritesPage />} />
        </Routes>
      </main>
      <Toast />
    </div>
  );
}
