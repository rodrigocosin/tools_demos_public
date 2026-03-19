import { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import {
  Star, Link2, Lock, AlertTriangle, User, Clock, Shield,
  BarChart3, Columns3, GitBranch, FileText, RefreshCw, CheckCircle
} from 'lucide-react';
import Breadcrumbs from './Breadcrumbs';
import SensitivityBadge from './SensitivityBadge';
import QualityBadge from './QualityBadge';
import LineageViewer from './LineageViewer';
import RequestAccessModal from './RequestAccessModal';
import ReportProblemModal from './ReportProblemModal';
import { catalogApi } from '../services/catalogApi';
import { useStore } from '../store/useStore';
import type { DataObject, LineageEdge, Column, Sensitivity } from '../types';

function relativeTime(dateStr: string): string {
  const now = new Date('2026-03-09T09:00:00Z');
  const date = new Date(dateStr);
  const diffMs = now.getTime() - date.getTime();
  const diffMin = Math.floor(diffMs / 60000);
  if (diffMin < 60) return `ha ${diffMin} minutos`;
  const diffH = Math.floor(diffMin / 60);
  if (diffH < 24) return `ha ${diffH} hora${diffH > 1 ? 's' : ''}`;
  const diffD = Math.floor(diffH / 24);
  if (diffD < 30) return `ha ${diffD} dia${diffD > 1 ? 's' : ''}`;
  const diffM = Math.floor(diffD / 30);
  return `ha ${diffM} mes${diffM > 1 ? 'es' : ''}`;
}

function formatNumber(n: number): string {
  if (n >= 1000000) return `${(n / 1000000).toFixed(1)}M`;
  if (n >= 1000) return `${(n / 1000).toFixed(1)}K`;
  return n.toString();
}

type TabId = 'about' | 'governance' | 'freshness' | 'columns' | 'quality' | 'lineage';

const TABS: { id: TabId; label: string; icon: React.ReactNode }[] = [
  { id: 'about', label: 'Sobre', icon: <FileText className="w-4 h-4" /> },
  { id: 'governance', label: 'Governanca', icon: <Shield className="w-4 h-4" /> },
  { id: 'freshness', label: 'Atualizacao & SLA', icon: <RefreshCw className="w-4 h-4" /> },
  { id: 'columns', label: 'Colunas', icon: <Columns3 className="w-4 h-4" /> },
  { id: 'quality', label: 'Qualidade', icon: <BarChart3 className="w-4 h-4" /> },
  { id: 'lineage', label: 'Linhagem', icon: <GitBranch className="w-4 h-4" /> },
];

export default function ObjectDetailPage() {
  const { catalogId, schemaId, objectId } = useParams<{
    catalogId: string; schemaId: string; objectId: string;
  }>();
  const { favorites, toggleFavorite, addRecentlyViewed, showToast } = useStore();

  const [obj, setObj] = useState<DataObject | null>(null);
  const [lineage, setLineage] = useState<{ upstream: LineageEdge[]; downstream: LineageEdge[] }>({ upstream: [], downstream: [] });
  const [tab, setTab] = useState<TabId>('about');
  const [showAccessModal, setShowAccessModal] = useState(false);
  const [showReportModal, setShowReportModal] = useState(false);
  const [colSensitivityFilter, setColSensitivityFilter] = useState<Sensitivity | 'all'>('all');

  const isFav = objectId ? favorites.includes(objectId) : false;

  useEffect(() => {
    if (!objectId) return;
    catalogApi.getObjectDetails(objectId).then(result => {
      setObj(result);
      if (result) addRecentlyViewed(objectId);
    });
    catalogApi.getLineage(objectId).then(setLineage);
  }, [objectId]);

  if (!obj) {
    return <div className="flex items-center justify-center h-64 text-gray-500">Carregando...</div>;
  }

  const catalog = catalogApi.getCatalogById(obj.catalogId);
  const schema = catalogApi.getSchemaById(obj.schemaId);
  const avgQuality = Math.round((obj.qualityCompleteness + obj.qualityUniqueness + obj.qualityConsistency) / 3);

  const filteredColumns = colSensitivityFilter === 'all'
    ? obj.columns
    : obj.columns.filter(c => c.sensitivity === colSensitivityFilter);

  return (
    <div className="max-w-6xl mx-auto">
      <Breadcrumbs items={[
        { label: 'Catalogos', to: '/catalogo' },
        ...(catalog ? [{ label: catalog.name, to: `/catalogo/${catalogId}` }] : []),
        ...(schema ? [{ label: schema.name, to: `/catalogo/${catalogId}/${schemaId}` }] : []),
        { label: obj.friendlyName },
      ]} />

      {/* Header */}
      <div className="card mb-6">
        <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-4">
          <div className="flex-1">
            <div className="flex items-center gap-3 flex-wrap">
              <h1 className="text-2xl font-bold text-gray-900">{obj.friendlyName}</h1>
              <span className={`badge ${obj.type === 'TABLE' ? 'bg-blue-100 text-blue-800' : 'bg-violet-100 text-violet-800'}`}>
                {obj.type === 'TABLE' ? 'Tabela' : 'View'}
              </span>
              <SensitivityBadge sensitivity={obj.sensitivity} />
              {obj.status === 'ACTIVE' ? (
                <span className="badge bg-green-100 text-green-800">Ativo</span>
              ) : (
                <span className="badge bg-amber-100 text-amber-800 flex items-center gap-1">
                  <AlertTriangle className="w-3 h-3" /> Descontinuado
                </span>
              )}
            </div>
            <p className="text-sm text-gray-400 font-mono mt-1">
              {catalog?.name}.{schema?.name}.{obj.name}
            </p>
            {obj.status === 'DEPRECATED' && obj.deprecationReason && (
              <div className="mt-2 p-3 bg-amber-50 border border-amber-200 rounded-lg">
                <p className="text-sm text-amber-800">
                  <strong>Aviso:</strong> {obj.deprecationReason}
                </p>
              </div>
            )}
          </div>
          <div className="flex items-center gap-2 shrink-0">
            <button onClick={() => { if (objectId) toggleFavorite(objectId); }}
              className={`btn-secondary flex items-center gap-1.5 ${isFav ? 'bg-amber-50 border-amber-300 text-amber-700' : ''}`}>
              <Star className={`w-4 h-4 ${isFav ? 'fill-amber-500 text-amber-500' : ''}`} />
              {isFav ? 'Favoritado' : 'Favoritar'}
            </button>
            <button onClick={() => { navigator.clipboard.writeText(window.location.href); showToast('Link copiado!'); }}
              className="btn-secondary flex items-center gap-1.5">
              <Link2 className="w-4 h-4" /> Compartilhar
            </button>
            <button onClick={() => setShowAccessModal(true)} className="btn-primary flex items-center gap-1.5">
              <Lock className="w-4 h-4" /> Solicitar Acesso
            </button>
            <button onClick={() => setShowReportModal(true)} className="btn-secondary flex items-center gap-1.5 text-amber-600 border-amber-300 hover:bg-amber-50">
              <AlertTriangle className="w-4 h-4" /> Reportar
            </button>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200 mb-6">
        <nav className="flex gap-0 overflow-x-auto">
          {TABS.map(t => (
            <button key={t.id} onClick={() => setTab(t.id)}
              className={`flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-colors whitespace-nowrap ${
                tab === t.id
                  ? 'border-indigo-600 text-indigo-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}>
              {t.icon} {t.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab content */}
      <div className="card">
        {tab === 'about' && <AboutTab obj={obj} />}
        {tab === 'governance' && <GovernanceTab obj={obj} />}
        {tab === 'freshness' && <FreshnessTab obj={obj} />}
        {tab === 'columns' && (
          <ColumnsTab columns={filteredColumns} allColumns={obj.columns}
            filter={colSensitivityFilter} onFilterChange={setColSensitivityFilter} />
        )}
        {tab === 'quality' && <QualityTab obj={obj} avgQuality={avgQuality} />}
        {tab === 'lineage' && (
          <LineageViewer objectId={obj.id} objectName={obj.friendlyName}
            upstream={lineage.upstream} downstream={lineage.downstream} />
        )}
      </div>

      <RequestAccessModal isOpen={showAccessModal} onClose={() => setShowAccessModal(false)}
        objectName={obj.friendlyName} owner={obj.owner} contactChannel={obj.contactChannel} />
      <ReportProblemModal isOpen={showReportModal} onClose={() => setShowReportModal(false)}
        objectName={obj.friendlyName} />
    </div>
  );
}

// ---- SUB TABS ----

function AboutTab({ obj }: { obj: DataObject }) {
  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-semibold text-gray-800 mb-2">Descricao de Negocios</h3>
        <p className="text-gray-600 leading-relaxed">{obj.businessDescription}</p>
      </div>

      {obj.usageExamples.length > 0 && (
        <div>
          <h3 className="text-lg font-semibold text-gray-800 mb-2">Exemplos de Uso</h3>
          <ul className="space-y-2">
            {obj.usageExamples.map((ex, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-gray-600">
                <span className="text-indigo-500 mt-0.5 shrink-0">&#9679;</span>
                <span className={ex.includes('SELECT') ? 'font-mono text-xs bg-gray-50 px-2 py-1 rounded' : ''}>{ex}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="border-t pt-6">
        <h3 className="text-lg font-semibold text-gray-800 mb-3">Responsavel</h3>
        <div className="flex items-start gap-4">
          <div className="w-12 h-12 bg-indigo-100 rounded-full flex items-center justify-center shrink-0">
            <User className="w-6 h-6 text-indigo-600" />
          </div>
          <div>
            <div className="font-semibold text-gray-800">{obj.owner}</div>
            <div className="text-sm text-gray-500">{obj.team}</div>
            <div className="text-sm text-gray-500">Steward: {obj.steward}</div>
            <div className="text-sm text-indigo-600 mt-1">{obj.contactChannel}</div>
          </div>
        </div>
        <div className="mt-4 p-3 bg-indigo-50 rounded-lg">
          <p className="text-sm text-indigo-800">
            <strong>Proximo passo:</strong> Quer usar este dado? Solicite acesso ao owner via {obj.contactChannel}
          </p>
        </div>
      </div>

      <div className="border-t pt-6">
        <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-2">Tags</h3>
        <div className="flex flex-wrap gap-2">
          {obj.tags.map(tag => (
            <span key={tag} className="badge bg-gray-100 text-gray-700">{tag}</span>
          ))}
        </div>
      </div>
    </div>
  );
}

function GovernanceTab({ obj }: { obj: DataObject }) {
  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-semibold text-gray-800 mb-3">Classificacao de Sensibilidade</h3>
        <div className="flex items-center gap-3 mb-2">
          <SensitivityBadge sensitivity={obj.sensitivity} showTooltip={false} />
        </div>
        <p className="text-sm text-gray-600">
          {obj.sensitivity === 'Publico' && 'Dados publicos sem restricao de acesso. Podem ser utilizados livremente por qualquer colaborador.'}
          {obj.sensitivity === 'Interno' && 'Dados de uso interno da empresa. Acesso restrito a colaboradores autorizados. Nao devem ser compartilhados externamente.'}
          {obj.sensitivity === 'Confidencial' && 'Dados confidenciais com acesso restrito por funcao. Requerem justificativa e aprovacao do owner para acesso.'}
          {obj.sensitivity === 'PII' && 'Dados pessoais identificaveis protegidos pela LGPD. Acesso extremamente restrito, requer base legal e aprovacao formal.'}
        </p>
      </div>

      {obj.isPII && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
          <div className="flex items-center gap-2 mb-2">
            <Lock className="w-5 h-5 text-red-600" />
            <h4 className="font-semibold text-red-800">Contém Dados Pessoais (PII)</h4>
          </div>
          <p className="text-sm text-red-700">
            Este dataset contem dados pessoais identificaveis (PII) protegidos pela LGPD. O acesso e processamento destes dados requerem base legal adequada, consentimento quando aplicavel, e registro de operacoes de tratamento.
          </p>
        </div>
      )}

      <div>
        <h3 className="text-lg font-semibold text-gray-800 mb-3">Politica de Retencao</h3>
        <div className="flex items-center gap-2">
          <Clock className="w-5 h-5 text-gray-500" />
          <span className="text-gray-700">
            {!obj.retentionDays || obj.retentionDays >= 99999 ? 'Retenção permanente' : `${obj.retentionDays} dias (${Math.round(obj.retentionDays / 365)} anos)`}
          </span>
        </div>
      </div>

      {obj.compliance.length > 0 && (
        <div>
          <h3 className="text-lg font-semibold text-gray-800 mb-3">Compliance</h3>
          <div className="flex flex-wrap gap-2">
            {obj.compliance.map(c => (
              <span key={c} className="badge bg-blue-100 text-blue-800 text-sm">
                <Shield className="w-3 h-3 mr-1" /> {c}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function FreshnessTab({ obj }: { obj: DataObject }) {
  const isOnTime = obj.status === 'ACTIVE' && obj.freshness !== 'Congelada';
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div>
          <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-2">Frequencia de Atualizacao</h3>
          <div className="flex items-center gap-2">
            <RefreshCw className="w-5 h-5 text-indigo-600" />
            <span className="text-lg font-semibold text-gray-800">{obj.freshness}</span>
          </div>
        </div>
        <div>
          <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-2">Ultima Atualizacao</h3>
          <div className="flex items-center gap-2">
            <Clock className="w-5 h-5 text-gray-500" />
            <span className="text-lg text-gray-800">{relativeTime(obj.lastUpdated)}</span>
          </div>
          <span className="text-xs text-gray-400">{new Date(obj.lastUpdated).toLocaleString('pt-BR')}</span>
        </div>
        <div>
          <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-2">SLA</h3>
          <p className="text-gray-700">{obj.sla}</p>
        </div>
        <div>
          <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-2">Status</h3>
          {isOnTime ? (
            <span className="inline-flex items-center gap-1.5 text-green-700 font-medium">
              <CheckCircle className="w-5 h-5" /> Dentro do SLA
            </span>
          ) : (
            <span className="inline-flex items-center gap-1.5 text-amber-700 font-medium">
              <AlertTriangle className="w-5 h-5" /> {obj.freshness === 'Congelada' ? 'Dados congelados' : 'Atencao'}
            </span>
          )}
        </div>
      </div>

      <div className="border-t pt-6">
        <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-2">Volume de Dados</h3>
        <div className="text-2xl font-bold text-gray-800">~{formatNumber(obj.rowCountApprox)} registros</div>
      </div>
    </div>
  );
}

function ColumnsTab({
  columns, allColumns, filter, onFilterChange,
}: {
  columns: Column[];
  allColumns: Column[];
  filter: Sensitivity | 'all';
  onFilterChange: (f: Sensitivity | 'all') => void;
}) {
  const sensitivities = [...new Set(allColumns.map(c => c.sensitivity))];
  return (
    <div>
      <div className="flex items-center gap-2 mb-4 flex-wrap">
        <span className="text-sm text-gray-500">Filtrar por sensibilidade:</span>
        <button onClick={() => onFilterChange('all')}
          className={`badge cursor-pointer ${filter === 'all' ? 'bg-indigo-100 text-indigo-800' : 'bg-gray-100 text-gray-600'}`}>
          Todas ({allColumns.length})
        </button>
        {sensitivities.map(s => (
          <button key={s} onClick={() => onFilterChange(s)}
            className={`badge cursor-pointer ${filter === s ? 'bg-indigo-100 text-indigo-800' : 'bg-gray-100 text-gray-600'}`}>
            {s} ({allColumns.filter(c => c.sensitivity === s).length})
          </button>
        ))}
      </div>

      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="bg-gray-50 border-b">
            <tr>
              <th className="px-3 py-2.5 text-left text-xs font-semibold text-gray-500 uppercase">Nome</th>
              <th className="px-3 py-2.5 text-left text-xs font-semibold text-gray-500 uppercase">Tipo</th>
              <th className="px-3 py-2.5 text-left text-xs font-semibold text-gray-500 uppercase">Descricao</th>
              <th className="px-3 py-2.5 text-left text-xs font-semibold text-gray-500 uppercase">Sensibilidade</th>
              <th className="px-3 py-2.5 text-left text-xs font-semibold text-gray-500 uppercase">Exemplos</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {columns.map(col => (
              <tr key={col.id} className={`${col.isPII ? 'bg-red-50/50' : ''}`}>
                <td className="px-3 py-2.5 text-sm font-mono text-gray-800 font-medium">
                  {col.name}
                  {col.isPII && <span className="ml-1.5 badge bg-red-100 text-red-700 text-xs">PII</span>}
                </td>
                <td className="px-3 py-2.5 text-sm text-gray-500 font-mono">{col.type}</td>
                <td className="px-3 py-2.5 text-sm text-gray-600 max-w-xs">{col.description}</td>
                <td className="px-3 py-2.5"><SensitivityBadge sensitivity={col.sensitivity} /></td>
                <td className="px-3 py-2.5 text-sm text-gray-500">
                  {col.isPII ? (
                    <span className="text-red-600 italic flex items-center gap-1">
                      <Lock className="w-3 h-3" /> [RESTRITO - Solicite Acesso]
                    </span>
                  ) : (
                    <span className="font-mono text-xs">{col.exampleValues.filter(Boolean).join(', ')}</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {columns.length === 0 && (
        <p className="text-center py-6 text-gray-500">Nenhuma coluna com esse filtro</p>
      )}
    </div>
  );
}

function QualityTab({ obj, avgQuality }: { obj: DataObject; avgQuality: number }) {
  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4 mb-4">
        <div className="text-center">
          <div className="text-3xl font-bold text-gray-800">{avgQuality}%</div>
          <div className="text-sm text-gray-500">Score Geral</div>
        </div>
        <QualityBadge score={avgQuality} />
      </div>

      <div className="space-y-4">
        <div>
          <QualityBadge score={obj.qualityCompleteness} label="Completude" showBar />
          <p className="text-xs text-gray-400 mt-1">Percentual de registros sem valores em branco ou nulos</p>
        </div>
        <div>
          <QualityBadge score={obj.qualityUniqueness} label="Unicidade" showBar />
          <p className="text-xs text-gray-400 mt-1">Percentual de registros unicos (sem duplicatas)</p>
        </div>
        <div>
          <QualityBadge score={obj.qualityConsistency} label="Consistencia" showBar />
          <p className="text-xs text-gray-400 mt-1">Percentual de registros que seguem as regras de validacao</p>
        </div>
      </div>

      <div className="border-t pt-4">
        <p className="text-xs text-gray-400">
          Ultima verificacao de qualidade: {new Date(obj.lastUpdated).toLocaleDateString('pt-BR')}
        </p>
      </div>
    </div>
  );
}
