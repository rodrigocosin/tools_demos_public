import { Routes, Route, NavLink } from 'react-router-dom'
import { useState } from 'react'
import { LayoutDashboard, Upload, FileSearch, Users, Cpu, Trash2 } from 'lucide-react'
import Dashboard from './pages/Dashboard'
import UploadPage from './pages/UploadPage'
import ExamesPage from './pages/ExamesPage'
import PacientesPage from './pages/PacientesPage'
import UploadDetailPage from './pages/UploadDetailPage'
import PacienteDetailPage from './pages/PacienteDetailPage'

const mainNav = [
  { to: '/upload',    icon: Upload,          label: 'Upload' },
  { to: '/exames',    icon: FileSearch,      label: 'Exames' },
  { to: '/pacientes', icon: Users,           label: 'Pacientes' },
  { to: '/',          icon: LayoutDashboard, label: 'Dashboard', end: true },
]

function NavItem({ to, icon: Icon, label, end }: { to: string; icon: typeof Upload; label: string; end?: boolean }) {
  return (
    <NavLink to={to} end={end}
      className={({ isActive }) =>
        `flex items-center gap-3 mx-3 px-4 py-2.5 rounded-xl text-sm font-medium transition-all duration-150 ${
          isActive ? 'bg-[#E4F7F7] text-[#1BBCBE] border border-[#1BBCBE]/30' : 'text-gray-500 hover:bg-gray-50 hover:text-gray-800'
        }`
      }
    >
      <Icon style={{ width: 18, height: 18 }} className="shrink-0" />
      {label}
    </NavLink>
  )
}

function ResetModal({ onClose }: { onClose: () => void }) {
  const [loading, setLoading] = useState(false)
  const [done, setDone] = useState(false)
  const [error, setError] = useState('')

  const handleReset = async () => {
    setLoading(true)
    setError('')
    try {
      const r = await fetch('/api/reset', { method: 'DELETE' })
      if (!r.ok) throw new Error(`Erro ${r.status}`)
      setDone(true)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Erro desconhecido')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
      <div className="bg-white rounded-2xl shadow-2xl p-8 max-w-sm w-full mx-4">
        {done ? (
          <>
            <div className="w-12 h-12 rounded-full bg-green-100 flex items-center justify-center mx-auto mb-4">
              <span className="text-green-600 text-2xl">✓</span>
            </div>
            <h2 className="text-lg font-bold text-gray-900 text-center mb-2">Ambiente zerado</h2>
            <p className="text-sm text-gray-500 text-center mb-6">Todos os dados foram removidos com sucesso.</p>
            <button onClick={() => { onClose(); window.location.reload() }}
              className="w-full py-2.5 bg-[#1BBCBE] text-white rounded-xl font-semibold hover:bg-[#148F91] transition-colors">
              Fechar
            </button>
          </>
        ) : (
          <>
            <div className="w-12 h-12 rounded-full bg-red-100 flex items-center justify-center mx-auto mb-4">
              <Trash2 className="w-6 h-6 text-red-600" />
            </div>
            <h2 className="text-lg font-bold text-gray-900 text-center mb-2">Zerar ambiente</h2>
            <p className="text-sm text-gray-500 text-center mb-2">
              Esta ação irá apagar <strong>permanentemente</strong> todos os pacientes, exames, uploads e arquivos do volume.
            </p>
            <p className="text-xs text-red-500 text-center mb-6 font-semibold">Esta ação não pode ser desfeita.</p>
            {error && <p className="text-xs text-red-600 text-center mb-4">{error}</p>}
            <div className="flex gap-3">
              <button onClick={onClose} disabled={loading}
                className="flex-1 py-2.5 border border-gray-200 text-gray-600 rounded-xl font-semibold hover:bg-gray-50 transition-colors disabled:opacity-50">
                Cancelar
              </button>
              <button onClick={handleReset} disabled={loading}
                className="flex-1 py-2.5 bg-red-600 text-white rounded-xl font-semibold hover:bg-red-700 transition-colors disabled:opacity-50">
                {loading ? 'Apagando...' : 'Confirmar'}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  )
}

export default function App() {
  const [showReset, setShowReset] = useState(false)

  return (
    <div className="min-h-screen flex">
      {/* Sidebar */}
      <aside className="w-60 bg-white text-gray-700 flex flex-col shrink-0 shadow-md border-r border-gray-100">

        {/* Logo */}
        <div className="px-5 py-4 border-b border-gray-100">
          <img src="/logo-oncoclinicas.png" alt="Onco Clínicas" className="h-8 w-auto max-w-full object-contain object-left" />
          <p className="text-[10px] text-gray-400 mt-2 uppercase tracking-widest">Análise de Exames IA</p>
        </div>

        {/* Navigation */}
        <nav className="flex-1 py-4 space-y-1">
          {mainNav.map(({ to, icon, label, end }) => (
            <NavItem key={to} to={to} icon={icon} label={label} end={end} />
          ))}
        </nav>

        {/* Reset button */}
        <div className="mx-3 mb-2">
          <button onClick={() => setShowReset(true)}
            className="w-full flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-medium text-red-400 hover:bg-red-50 hover:text-red-600 transition-all duration-150">
            <Trash2 style={{ width: 16, height: 16 }} className="shrink-0" />
            Zerar Ambiente
          </button>
        </div>

        {/* AI badge */}
        <div className="mx-3 mb-4 p-3 rounded-xl bg-gray-50 border border-gray-100 flex items-center gap-2">
          <Cpu style={{ width: 16, height: 16 }} className="text-[#1BBCBE] shrink-0" />
          <div>
            <p className="text-[9px] uppercase tracking-widest text-gray-400">Powered by</p>
            <p className="text-xs font-semibold text-gray-500">Databricks + LLM</p>
          </div>
        </div>
      </aside>

      {/* Main */}
      <main className="flex-1 overflow-auto">
        <div className="max-w-7xl mx-auto p-7">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/upload" element={<UploadPage />} />
            <Route path="/exames" element={<ExamesPage />} />
            <Route path="/pacientes" element={<PacientesPage />} />
            <Route path="/upload/:uploadId" element={<UploadDetailPage />} />
            <Route path="/pacientes/:cpf" element={<PacienteDetailPage />} />
          </Routes>
        </div>
      </main>

      {showReset && <ResetModal onClose={() => setShowReset(false)} />}
    </div>
  )
}
