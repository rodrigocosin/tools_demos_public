import { useParams, Link } from 'react-router-dom'
import { useApi } from '../hooks/useApi'
import StatusBadge from '../components/StatusBadge'
import LoadingSpinner from '../components/LoadingSpinner'
import { ArrowLeft, RefreshCw, TestTubes } from 'lucide-react'
import { useState } from 'react'

interface Exame {
  exame_id: string
  nome_exame: string
  categoria: string
  valor_resultado: string
  unidade: string
  valor_referencia: string
  status_resultado: string
  parecer_llm: string
  paciente_nome: string | null
}

export default function UploadDetailPage() {
  const { uploadId } = useParams<{ uploadId: string }>()
  const { data, loading, error, refetch } = useApi<{ exames: Exame[] }>(`/api/exames/${uploadId}`)
  const [reprocessing, setReprocessing] = useState(false)

  const handleReprocess = async () => {
    setReprocessing(true)
    try {
      await fetch(`/api/processar/${uploadId}`, { method: 'POST' })
      // Wait and refetch
      setTimeout(() => { refetch(); setReprocessing(false) }, 5000)
    } catch {
      setReprocessing(false)
    }
  }

  if (loading) return <LoadingSpinner />
  if (error) return <div className="text-red-500 p-8">Erro: {error}</div>

  const exames = data?.exames || []
  const pacienteName = exames[0]?.paciente_nome || 'Paciente'
  const parecer = exames[0]?.parecer_llm || ''

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <Link to="/upload" className="text-blue-500 hover:underline text-sm flex items-center gap-1 mb-2">
            <ArrowLeft className="w-4 h-4" /> Voltar
          </Link>
          <h1 className="text-2xl font-bold text-gray-800">Detalhes do Upload</h1>
          <p className="text-gray-500 text-sm mt-1">Paciente: {pacienteName} - {exames.length} exame(s)</p>
        </div>
        <button
          onClick={handleReprocess}
          disabled={reprocessing}
          className="flex items-center gap-2 px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50 text-sm"
        >
          <RefreshCw className={`w-4 h-4 ${reprocessing ? 'animate-spin' : ''}`} />
          {reprocessing ? 'Reprocessando...' : 'Reprocessar'}
        </button>
      </div>

      {/* Parecer */}
      {parecer && (
        <div className="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-xl border border-blue-100 p-5 mb-6">
          <h2 className="font-semibold text-blue-800 mb-2">Parecer Medico (IA)</h2>
          <p className="text-sm text-gray-700 whitespace-pre-wrap leading-relaxed">{parecer}</p>
        </div>
      )}

      {/* Exams */}
      {exames.length === 0 ? (
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-12 text-center text-gray-400">
          <TestTubes className="w-12 h-12 mx-auto mb-2 opacity-50" />
          <p>Nenhum exame encontrado para este upload</p>
          <p className="text-xs mt-2">O processamento pode ainda estar em andamento</p>
          <button onClick={refetch} className="mt-4 text-blue-500 hover:underline text-sm">
            Atualizar
          </button>
        </div>
      ) : (
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-gray-50 border-b border-gray-200">
                <th className="text-left py-3 px-4 font-medium text-gray-500">Exame</th>
                <th className="text-left py-3 px-4 font-medium text-gray-500">Categoria</th>
                <th className="text-left py-3 px-4 font-medium text-gray-500">Resultado</th>
                <th className="text-left py-3 px-4 font-medium text-gray-500">Unidade</th>
                <th className="text-left py-3 px-4 font-medium text-gray-500">Referencia</th>
                <th className="text-left py-3 px-4 font-medium text-gray-500">Status</th>
              </tr>
            </thead>
            <tbody>
              {exames.map((e) => (
                <tr key={e.exame_id} className="border-b border-gray-50 hover:bg-gray-50">
                  <td className="py-3 px-4 font-medium">{e.nome_exame}</td>
                  <td className="py-3 px-4">
                    <span className="px-2 py-0.5 rounded text-xs bg-gray-100 text-gray-600">{e.categoria}</span>
                  </td>
                  <td className="py-3 px-4 font-mono font-semibold">{e.valor_resultado}</td>
                  <td className="py-3 px-4 text-gray-500">{e.unidade}</td>
                  <td className="py-3 px-4 text-gray-500">{e.valor_referencia}</td>
                  <td className="py-3 px-4"><StatusBadge status={e.status_resultado} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
