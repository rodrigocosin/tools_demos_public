import { useState } from 'react'
import { useApi } from '../hooks/useApi'
import StatsCard from '../components/StatsCard'
import StatusBadge from '../components/StatusBadge'
import LoadingSpinner from '../components/LoadingSpinner'
import DatabricksDashboardEmbed from '../components/DatabricksDashboardEmbed'
import { Link } from 'react-router-dom'
import {
  FileUp,
  TestTubes,
  Users,
  AlertTriangle,
  AlertCircle,
  BarChart3,
  LayoutDashboard,
} from 'lucide-react'

interface Stats {
  total_uploads: number
  total_exames: number
  total_pacientes: number
  exames_alterados: number
  exames_criticos: number
  by_category: { categoria: string; cnt: string }[]
  by_status: { status_resultado: string; cnt: string }[]
  recent_uploads: {
    upload_id: string
    paciente_nome: string | null
    nome_arquivo: string
    status: string
    data_upload: string
    total_exames: string | null
  }[]
}

export default function Dashboard() {
  const [tab, setTab] = useState<'resumo' | 'analytics'>('resumo')
  const { data, loading, error } = useApi<Stats>('/api/stats')

  if (loading) return <LoadingSpinner />
  if (error) return <div className="text-red-500 p-8">Erro: {error}</div>
  if (!data) return null

  const catColors: Record<string, string> = {
    hemograma: 'bg-red-100 text-red-700',
    glicemia: 'bg-amber-100 text-amber-700',
    colesterol: 'bg-orange-100 text-orange-700',
    funcao_renal: 'bg-blue-100 text-blue-700',
    hormonios: 'bg-purple-100 text-purple-700',
    urina: 'bg-yellow-100 text-yellow-700',
    bioquimica: 'bg-teal-100 text-teal-700',
    outros: 'bg-gray-100 text-gray-700',
  }

  const today = new Date().toLocaleDateString('pt-BR', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })

  return (
    <div>
      {/* Header */}
      <div className="mb-6 flex items-end justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-widest text-[#1BBCBE] mb-1">Painel Geral</p>
          <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
          <p className="text-gray-400 text-sm mt-1 capitalize">{today}</p>
        </div>
        {data.exames_criticos > 0 && (
          <div className="flex items-center gap-2 bg-red-50 border border-red-200 text-red-700 text-sm font-semibold px-4 py-2 rounded-xl">
            <AlertCircle className="w-4 h-4" />
            {data.exames_criticos} exame(s) crítico(s)
          </div>
        )}
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-6 bg-gray-100 p-1 rounded-xl w-fit">
        <button
          onClick={() => setTab('resumo')}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold transition-all ${
            tab === 'resumo'
              ? 'bg-white text-[#1BBCBE] shadow-sm'
              : 'text-gray-500 hover:text-gray-700'
          }`}
        >
          <LayoutDashboard className="w-4 h-4" />
          Resumo
        </button>
        <button
          onClick={() => setTab('analytics')}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold transition-all ${
            tab === 'analytics'
              ? 'bg-white text-[#1BBCBE] shadow-sm'
              : 'text-gray-500 hover:text-gray-700'
          }`}
        >
          <BarChart3 className="w-4 h-4" />
          Analytics Avançado
        </button>
      </div>

      {/* Analytics tab */}
      {tab === 'analytics' && <DatabricksDashboardEmbed />}

      {/* Resumo tab */}
      {tab === 'resumo' && <>

      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-4 mb-8">
        <StatsCard title="Uploads"   value={data.total_uploads}    icon={FileUp}        color="bg-[#1BBCBE]" />
        <StatsCard title="Exames"    value={data.total_exames}     icon={TestTubes}     color="bg-teal-500" />
        <StatsCard title="Pacientes" value={data.total_pacientes}  icon={Users}         color="bg-indigo-500" />
        <StatsCard title="Alterados" value={data.exames_alterados} icon={AlertTriangle} color="bg-amber-500" />
        <StatsCard title="Críticos"  value={data.exames_criticos}  icon={AlertCircle}   color="bg-red-500" />
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

        {/* By Category */}
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
          <div className="flex items-center gap-2 mb-5">
            <div className="w-7 h-7 rounded-lg bg-[#E4F7F7] flex items-center justify-center">
              <BarChart3 className="w-4 h-4 text-[#1BBCBE]" />
            </div>
            <h2 className="font-semibold text-gray-800">Por Categoria</h2>
          </div>
          {data.by_category.length === 0 ? (
            <p className="text-sm text-gray-400">Nenhum exame processado</p>
          ) : (
            <div className="space-y-3.5">
              {data.by_category.map((c) => {
                const total = data.total_exames || 1
                const pct = Math.round((parseInt(c.cnt) / total) * 100)
                const colorCls = catColors[c.categoria] || catColors.outros
                return (
                  <div key={c.categoria}>
                    <div className="flex justify-between items-center mb-1.5">
                      <span className={`px-2.5 py-0.5 rounded-full text-xs font-semibold ${colorCls}`}>{c.categoria}</span>
                      <span className="text-gray-400 text-xs">{c.cnt} · {pct}%</span>
                    </div>
                    <div className="w-full bg-gray-100 rounded-full h-1.5">
                      <div className="h-1.5 rounded-full bg-[#1BBCBE] transition-all" style={{ width: `${pct}%` }} />
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>

        {/* By Status */}
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
          <div className="flex items-center gap-2 mb-5">
            <div className="w-7 h-7 rounded-lg bg-[#E4F7F7] flex items-center justify-center">
              <AlertTriangle className="w-4 h-4 text-[#1BBCBE]" />
            </div>
            <h2 className="font-semibold text-gray-800">Status dos Resultados</h2>
          </div>
          {data.by_status.length === 0 ? (
            <p className="text-sm text-gray-400">Nenhum exame ainda</p>
          ) : (
            <div className="space-y-3">
              {data.by_status.map((s) => {
                const total = data.total_exames || 1
                const pct = Math.round((parseInt(s.cnt) / total) * 100)
                return (
                  <div key={s.status_resultado} className="flex items-center justify-between p-3 rounded-xl bg-gray-50">
                    <StatusBadge status={s.status_resultado} size="md" />
                    <div className="text-right">
                      <p className="text-xl font-bold text-gray-800">{s.cnt}</p>
                      <p className="text-xs text-gray-400">{pct}%</p>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>

        {/* Recent Uploads */}
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
          <div className="flex items-center gap-2 mb-5">
            <div className="w-7 h-7 rounded-lg bg-[#E4F7F7] flex items-center justify-center">
              <FileUp className="w-4 h-4 text-[#1BBCBE]" />
            </div>
            <h2 className="font-semibold text-gray-800">Uploads Recentes</h2>
          </div>
          {data.recent_uploads.length === 0 ? (
            <p className="text-sm text-gray-400">Nenhum upload ainda</p>
          ) : (
            <div className="space-y-2">
              {data.recent_uploads.map((u) => (
                <Link key={u.upload_id} to={`/upload/${u.upload_id}`}
                  className="flex items-center justify-between p-3 rounded-xl bg-gray-50 hover:bg-[#E4F7F7] transition-colors group">
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium text-gray-800 truncate group-hover:text-[#148F91]">{u.nome_arquivo}</p>
                    <p className="text-xs text-gray-400 mt-0.5">
                      {u.paciente_nome || '—'}{u.total_exames ? ` · ${u.total_exames} exames` : ''}
                    </p>
                  </div>
                  <StatusBadge status={u.status} />
                </Link>
              ))}
            </div>
          )}
        </div>
      </div>

      </>}
    </div>
  )
}
