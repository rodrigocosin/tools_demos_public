import { useState, useMemo } from 'react'
import { useApi } from '../hooks/useApi'
import StatusBadge from '../components/StatusBadge'
import LoadingSpinner from '../components/LoadingSpinner'
import { TestTubes, Filter, MessageSquare, Search, X } from 'lucide-react'

interface Exame {
  exame_id: string
  upload_id: string
  cpf: string
  paciente_nome: string | null
  tipo_exame: string
  categoria: string
  nome_exame: string
  valor_resultado: string
  unidade: string
  valor_referencia: string
  status_resultado: string
  parecer_llm: string
  data_exame: string
}

const categorias = ['', 'hemograma', 'glicemia', 'colesterol', 'funcao_renal', 'hormonios', 'urina', 'bioquimica', 'outros']
const statusOptions = ['', 'normal', 'alterado', 'critico']
const tipoOptions = ['', 'sangue', 'urina', 'imagem', 'hormonios', 'bioquimica', 'outros']

export default function ExamesPage() {
  const [categoria, setCategoria] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [tipoFilter, setTipoFilter] = useState('')
  const [searchPaciente, setSearchPaciente] = useState('')
  const [searchExame, setSearchExame] = useState('')
  const [dataInicio, setDataInicio] = useState('')
  const [dataFim, setDataFim] = useState('')
  const [parecerExameId, setParecerExameId] = useState<string | null>(null)

  const params = new URLSearchParams()
  if (categoria) params.set('categoria', categoria)
  if (statusFilter) params.set('status_resultado', statusFilter)
  const url = `/api/exames?${params.toString()}`

  const { data, loading, error } = useApi<{ exames: Exame[] }>(url, [categoria, statusFilter])

  const filtered = useMemo(() => {
    if (!data?.exames) return []
    return data.exames.filter(e => {
      if (tipoFilter && e.tipo_exame !== tipoFilter) return false
      if (searchPaciente && !(e.paciente_nome ?? '').toLowerCase().includes(searchPaciente.toLowerCase())) return false
      if (searchExame && !e.nome_exame.toLowerCase().includes(searchExame.toLowerCase())) return false
      if (dataInicio && e.data_exame && e.data_exame < dataInicio) return false
      if (dataFim && e.data_exame && e.data_exame > dataFim) return false
      return true
    })
  }, [data, tipoFilter, searchPaciente, searchExame, dataInicio, dataFim])

  const hasLocalFilters = tipoFilter || searchPaciente || searchExame || dataInicio || dataFim
  const clearAll = () => {
    setCategoria(''); setStatusFilter(''); setTipoFilter('')
    setSearchPaciente(''); setSearchExame(''); setDataInicio(''); setDataFim('')
  }

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-800">Exames</h1>
        <p className="text-gray-500 text-sm mt-1">Todos os exames processados com analise IA</p>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-4 mb-6 space-y-3">
        {/* Row 1: text searches */}
        <div className="flex flex-wrap gap-3">
          <div className="flex items-center gap-2 border border-gray-200 rounded-lg px-3 py-1.5 flex-1 min-w-[180px]">
            <Search className="w-4 h-4 text-gray-400 shrink-0" />
            <input
              type="text"
              placeholder="Buscar paciente..."
              value={searchPaciente}
              onChange={e => setSearchPaciente(e.target.value)}
              className="flex-1 text-sm outline-none placeholder-gray-400"
            />
            {searchPaciente && <button onClick={() => setSearchPaciente('')}><X className="w-3.5 h-3.5 text-gray-400" /></button>}
          </div>
          <div className="flex items-center gap-2 border border-gray-200 rounded-lg px-3 py-1.5 flex-1 min-w-[180px]">
            <Search className="w-4 h-4 text-gray-400 shrink-0" />
            <input
              type="text"
              placeholder="Buscar exame..."
              value={searchExame}
              onChange={e => setSearchExame(e.target.value)}
              className="flex-1 text-sm outline-none placeholder-gray-400"
            />
            {searchExame && <button onClick={() => setSearchExame('')}><X className="w-3.5 h-3.5 text-gray-400" /></button>}
          </div>
        </div>

        {/* Row 2: selects + dates */}
        <div className="flex flex-wrap gap-3 items-end">
          <div>
            <label className="block text-xs text-gray-500 mb-1">Categoria</label>
            <select value={categoria} onChange={e => setCategoria(e.target.value)}
              className="border border-gray-200 rounded-lg px-3 py-1.5 text-sm focus:ring-2 focus:ring-blue-300 focus:outline-none">
              {categorias.map(c => <option key={c} value={c}>{c || 'Todas categorias'}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">Tipo</label>
            <select value={tipoFilter} onChange={e => setTipoFilter(e.target.value)}
              className="border border-gray-200 rounded-lg px-3 py-1.5 text-sm focus:ring-2 focus:ring-blue-300 focus:outline-none">
              {tipoOptions.map(t => <option key={t} value={t}>{t || 'Todos tipos'}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">Status</label>
            <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)}
              className="border border-gray-200 rounded-lg px-3 py-1.5 text-sm focus:ring-2 focus:ring-blue-300 focus:outline-none">
              {statusOptions.map(s => <option key={s} value={s}>{s || 'Todos status'}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">Data inicio</label>
            <input type="date" value={dataInicio} onChange={e => setDataInicio(e.target.value)}
              className="border border-gray-200 rounded-lg px-3 py-1.5 text-sm focus:ring-2 focus:ring-blue-300 focus:outline-none" />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">Data fim</label>
            <input type="date" value={dataFim} onChange={e => setDataFim(e.target.value)}
              className="border border-gray-200 rounded-lg px-3 py-1.5 text-sm focus:ring-2 focus:ring-blue-300 focus:outline-none" />
          </div>
          <div className="flex items-center gap-3 ml-auto">
            {(categoria || statusFilter || hasLocalFilters) && (
              <button onClick={clearAll} className="text-xs text-gray-400 hover:text-gray-600 flex items-center gap-1">
                <X className="w-3.5 h-3.5" /> Limpar filtros
              </button>
            )}
            <span className="text-sm text-gray-400">
              <Filter className="w-4 h-4 inline mr-1" />
              {filtered.length} resultado(s)
            </span>
          </div>
        </div>
      </div>

      {/* Exams Table */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100">
        {loading ? (
          <LoadingSpinner />
        ) : error ? (
          <div className="p-8 text-red-500">Erro: {error}</div>
        ) : !filtered.length ? (
          <div className="text-center py-12 text-gray-400">
            <TestTubes className="w-12 h-12 mx-auto mb-2 opacity-50" />
            <p>Nenhum exame encontrado</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 border-b border-gray-200">
                  <th className="text-left py-3 px-4 font-medium text-gray-500">Paciente</th>
                  <th className="text-left py-3 px-4 font-medium text-gray-500">Exame</th>
                  <th className="text-left py-3 px-4 font-medium text-gray-500">Categoria</th>
                  <th className="text-left py-3 px-4 font-medium text-gray-500">Tipo</th>
                  <th className="text-left py-3 px-4 font-medium text-gray-500">Resultado</th>
                  <th className="text-left py-3 px-4 font-medium text-gray-500">Referencia</th>
                  <th className="text-left py-3 px-4 font-medium text-gray-500">Status</th>
                  <th className="text-left py-3 px-4 font-medium text-gray-500">Data</th>
                  <th className="text-left py-3 px-4 font-medium text-gray-500">Parecer</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((e) => (
                  <>
                    <tr key={e.exame_id} className="border-b border-gray-50 hover:bg-gray-50">
                      <td className="py-3 px-4 font-medium">{e.paciente_nome || '-'}</td>
                      <td className="py-3 px-4">{e.nome_exame}</td>
                      <td className="py-3 px-4">
                        <span className="px-2 py-0.5 rounded text-xs bg-gray-100 text-gray-600">{e.categoria}</span>
                      </td>
                      <td className="py-3 px-4">
                        <span className="px-2 py-0.5 rounded text-xs bg-blue-50 text-blue-600">{e.tipo_exame}</span>
                      </td>
                      <td className="py-3 px-4 font-mono">
                        <span className="font-semibold">{e.valor_resultado}</span>
                        {e.unidade && <span className="text-gray-400 ml-1">{e.unidade}</span>}
                      </td>
                      <td className="py-3 px-4 text-gray-500">{e.valor_referencia || '-'}</td>
                      <td className="py-3 px-4"><StatusBadge status={e.status_resultado} /></td>
                      <td className="py-3 px-4 text-gray-500 text-xs">{e.data_exame || '-'}</td>
                      <td className="py-3 px-4">
                        {e.parecer_llm && (
                          <button
                            onClick={() => setParecerExameId(parecerExameId === e.exame_id ? null : e.exame_id)}
                            className="text-blue-500 hover:text-blue-700"
                            title="Ver parecer"
                          >
                            <MessageSquare className="w-4 h-4" />
                          </button>
                        )}
                      </td>
                    </tr>
                    {parecerExameId === e.exame_id && e.parecer_llm && (
                      <tr key={`${e.exame_id}-parecer`}>
                        <td colSpan={9} className="px-4 py-3 bg-blue-50 border-b border-blue-100">
                          <div className="text-sm text-gray-700 whitespace-pre-wrap">
                            <span className="font-semibold text-blue-700">Parecer IA:</span>{' '}
                            {e.parecer_llm}
                          </div>
                        </td>
                      </tr>
                    )}
                  </>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
