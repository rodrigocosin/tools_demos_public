import React, { useState } from 'react';
import DashboardTab from './components/DashboardTab';
import GenieTab from './components/GenieTab';
import GenieOneTab from './components/GenieOneTab';
import KnowledgeTab from './components/KnowledgeTab';
import SupervisorTab from './components/SupervisorTab';
import HowItWorksTab from './components/HowItWorksTab';

// --- Inline icon set (lucide-style line icons) ---
const Icon = ({ path, size = 18 }) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="1.8"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    {path}
  </svg>
);

const ICONS = {
  dashboard: (
    <Icon path={<><rect x="3" y="3" width="7" height="9" /><rect x="14" y="3" width="7" height="5" /><rect x="14" y="12" width="7" height="9" /><rect x="3" y="16" width="7" height="5" /></>} />
  ),
  genie: (
    <Icon path={<><path d="M12 3v2M5 8l1.5 1.5M19 8l-1.5 1.5" /><path d="M7 21a5 5 0 0 1 10 0z" /><path d="M9 13a3 3 0 0 1 6 0" /></>} />
  ),
  genieone: (
    <Icon path={<><path d="M5 3h14l-2 5H7L5 3z" /><path d="M7 8v3a5 5 0 0 0 10 0V8" /><path d="M12 16v5M8 21h8" /></>} />
  ),
  knowledge: (
    <Icon path={<><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" /><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" /></>} />
  ),
  supervisor: (
    <Icon path={<><rect x="4" y="8" width="16" height="12" rx="2" /><path d="M12 8V4M8 4h8" /><circle cx="9" cy="14" r="1" /><circle cx="15" cy="14" r="1" /></>} />
  ),
  howitworks: (
    <Icon path={<><circle cx="12" cy="12" r="9" /><path d="M9.5 9a2.5 2.5 0 0 1 4.5 1.5c0 1.5-2 2-2 3" /><line x1="12" y1="17" x2="12" y2="17" /></>} />
  ),
};

const NAV = [
  { id: 'dashboard', label: 'Dashboard', sub: 'Métricas e indicadores' },
  { id: 'genie', label: 'Genie · Dados', sub: 'Perguntas em linguagem natural' },
  { id: 'genieone', label: 'Genie One · MCP', sub: 'Genie One via MCP no app' },
  { id: 'knowledge', label: 'Base de Conhecimento', sub: 'Normas e procedimentos' },
  { id: 'supervisor', label: 'Agente Supervisor', sub: 'Dados + conhecimento' },
  { id: 'howitworks', label: 'Como Funciona', sub: 'Detalhes técnicos de cada conexão' },
];

function DatabricksLogo() {
  return (
    <svg width="30" height="30" viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M20 2L3 12v4.5l17 10 17-10V12L20 2z" fill="#FF3621" />
      <path d="M3 16.5v4.5l17 10 17-10v-4.5L20 26.5 3 16.5z" fill="#FF3621" opacity="0.7" />
      <path d="M3 21v4.5l17 10 17-10V21L20 31 3 21z" fill="#FF3621" opacity="0.4" />
    </svg>
  );
}

export default function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const active = NAV.find((n) => n.id === activeTab);

  return (
    <div className="h-screen flex bg-db-darker">
      {/* Sidebar */}
      <aside className="w-64 shrink-0 bg-db-sidebar border-r border-db-border/50 flex flex-col">
        {/* Brand */}
        <div className="px-5 py-5 flex items-center gap-3 border-b border-db-border/40">
          <DatabricksLogo />
          <div className="leading-tight">
            <h1 className="text-[15px] font-semibold text-white tracking-tight">Suporte de TI</h1>
            <p className="text-[11px] text-db-muted">Plataforma End-to-End</p>
          </div>
        </div>

        {/* Nav */}
        <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
          <p className="px-3 pb-2 text-[10px] font-semibold uppercase tracking-wider text-db-muted/70">
            Navegação
          </p>
          {NAV.map((item) => {
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-left transition-all relative group
                  ${isActive
                    ? 'bg-db-surface text-white'
                    : 'text-db-muted hover:text-white hover:bg-db-surface/40'
                  }`}
              >
                {isActive && (
                  <span className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-6 bg-db-accent rounded-r-full" />
                )}
                <span className={isActive ? 'text-db-accent' : 'text-db-muted group-hover:text-db-light'}>
                  {ICONS[item.id]}
                </span>
                <span className="flex flex-col">
                  <span className="text-sm font-medium">{item.label}</span>
                  <span className="text-[11px] text-db-muted/80 leading-tight">{item.sub}</span>
                </span>
              </button>
            );
          })}
        </nav>

        {/* Footer */}
        <div className="px-5 py-4 border-t border-db-border/40 flex items-center gap-2 text-xs text-db-muted">
          <span className="inline-block w-2 h-2 rounded-full bg-green-400 shadow-[0_0_6px_rgba(74,222,128,0.7)]" />
          Serviços online
        </div>
      </aside>

      {/* Main */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Top bar */}
        <header className="bg-db-dark border-b border-db-border/40 px-6 py-3.5 flex items-center justify-between shrink-0">
          <div className="flex items-center gap-3">
            <span className="text-db-accent">{ICONS[active.id]}</span>
            <div className="leading-tight">
              <h2 className="text-base font-semibold text-white">{active.label}</h2>
              <p className="text-xs text-db-muted">{active.sub}</p>
            </div>
          </div>
          <span className="text-[11px] text-db-muted px-2.5 py-1 rounded-full border border-db-border/50">
            Centro de Suporte de TI
          </span>
        </header>

        {/* Content */}
        <main className="flex-1 overflow-hidden">
          {activeTab === 'dashboard' && <DashboardTab />}
          {activeTab === 'genie' && <GenieTab />}
          {activeTab === 'genieone' && <GenieOneTab />}
          {activeTab === 'knowledge' && <KnowledgeTab />}
          {activeTab === 'supervisor' && <SupervisorTab />}
          {activeTab === 'howitworks' && <HowItWorksTab />}
        </main>
      </div>
    </div>
  );
}
