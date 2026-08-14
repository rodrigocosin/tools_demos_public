import React, { useState } from 'react';
import DashboardTab from './components/DashboardTab';
import GenieTab from './components/GenieTab';
import KnowledgeTab from './components/KnowledgeTab';
import SupervisorTab from './components/SupervisorTab';

const TABS = [
  { id: 'dashboard', label: 'Dashboard', icon: '📊' },
  { id: 'genie', label: 'Genie - Dados', icon: '🧞' },
  { id: 'knowledge', label: 'Base de Conhecimento', icon: '📚' },
  { id: 'supervisor', label: 'Agente Supervisor', icon: '🤖' },
];

function DatabricksLogo() {
  return (
    <svg width="28" height="28" viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M20 2L3 12v4.5l17 10 17-10V12L20 2z" fill="#FF3621" />
      <path d="M3 16.5v4.5l17 10 17-10v-4.5L20 26.5 3 16.5z" fill="#FF3621" opacity="0.7" />
      <path d="M3 21v4.5l17 10 17-10V21L20 31 3 21z" fill="#FF3621" opacity="0.4" />
    </svg>
  );
}

export default function App() {
  const [activeTab, setActiveTab] = useState('dashboard');

  return (
    <div className="h-screen flex flex-col bg-db-darker">
      {/* Header */}
      <header className="bg-db-dark border-b border-db-primary/40 px-6 py-3 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-3">
          <DatabricksLogo />
          <h1 className="text-xl font-semibold text-white tracking-tight">
            Centro de Suporte de TI
          </h1>
        </div>
        <div className="flex items-center gap-2 text-xs text-db-muted">
          <span className="inline-block w-2 h-2 rounded-full bg-green-400"></span>
          Online
        </div>
      </header>

      {/* Tab Bar */}
      <nav className="bg-db-dark border-b border-db-primary/30 px-6 flex gap-1 shrink-0">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`px-4 py-2.5 text-sm font-medium rounded-t-lg transition-colors relative
              ${activeTab === tab.id
                ? 'text-white bg-db-surface'
                : 'text-db-muted hover:text-white hover:bg-db-surface/50'
              }`}
          >
            <span className="mr-1.5">{tab.icon}</span>
            {tab.label}
            {activeTab === tab.id && (
              <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-db-accent rounded-full"></span>
            )}
          </button>
        ))}
      </nav>

      {/* Tab Content */}
      <main className="flex-1 overflow-hidden">
        {activeTab === 'dashboard' && <DashboardTab />}
        {activeTab === 'genie' && <GenieTab />}
        {activeTab === 'knowledge' && <KnowledgeTab />}
        {activeTab === 'supervisor' && <SupervisorTab />}
      </main>
    </div>
  );
}
