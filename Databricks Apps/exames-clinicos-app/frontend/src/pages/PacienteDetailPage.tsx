import { useParams, Link } from 'react-router-dom'
import { useApi } from '../hooks/useApi'
import StatusBadge from '../components/StatusBadge'
import LoadingSpinner from '../components/LoadingSpinner'
import { ArrowLeft, User } from 'lucide-react'

interface PacienteDetail {
  paciente: {
    cpf: string
    nome: string
    data_nascimento: string | null
    idade: string | null
    sexo: string | null
    medico_solicitante: string | null
  }
  exames: {
    exame_id: string
    nome_exame: string
    categoria: string
    valor_resultado: string
    unidade: string
    valor_referencia: string
    status_resultado: string
    data_exame: string
  }[]
  uploads: {
    upload_id: string
    nome_arquivo: string
    status: string
    data_upload: string
    total_exames: string
  }[]
}

export default function PacienteDetailPage() {
  const { cpf } = useParams<{ cpf: string }>()
  const { data, loading, error } = useApi<PacienteDetail>(`/api/paciente?cpf=${encodeURIComponent(cpf || '')}`)

  if (loading) return <LoadingSpinner />
  if (error) return <div className="text-red-500 p-8">Erro: {error}</div>
  if (!data?.paciente) return <div className="p-8">Paciente nao encontrado</div>

  const p = data.paciente

  return (
    <div>
      <Link to="/pacientes" className="text-blue-500 hover:underline text-sm flex items-center gap-1 mb-4">
        <ArrowLeft className="w-4 h-4" /> Voltar
      </Link>

      {/* Patient Info */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 mb-6">
        <div className="flex items-center gap-4">
          <div className="p-3 rounded-full bg-violet-50">
            <User className="w-8 h-8 text-violet-500" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-gray-800">{p.nome}</h1>
            <div className="flex gap-4 text-sm text-gray-500 mt-1">
              {p.idade && <span>{p.idade} anos</span>}
              {p.sexo && <span>{p.sexo === 'M' ? 'Masculino' : p.sexo === 'F' ? 'Feminino' : p.sexo}</span>}
              {p.data_nascimento && <span>Nasc: {p.data_nascimento}</span>}
              <span>CPF: {p.cpf}</span>
            </div>
            {p.medico_solicitante && (
              <p className="text-sm text-gray-400 mt-1">Medico: Dr(a). {p.medico_solicitante}</p>
            )}
          </div>
        </div>
      </div>

      {/* Uploads */}
      {data.uploads.length > 0 && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5 mb-6">
          <h2 className="font-semibold text-gray-700 mb-3">Uploads</h2>
          <div className="space-y-2">
            {data.uploads.map(u => (
              <Link key={u.upload_id} to={`/upload/${u.upload_id}`}
                className="flex items-center justify-between p-3 rounded-lg bg-gray-50 hover:bg-gray-100 transition">
                <span className="text-sm">{u.nome_arquivo}</span>
                <div className="flex items-center gap-3">
                  <span className="text-xs text-gray-400">{u.total_exames} exames</span>
                  <StatusBadge status={u.status} />
                </div>
              </Link>
            ))}
          </div>
        </div>
      )}

      {/* Exams */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
        <div className="p-5 border-b border-gray-100">
          <h2 className="font-semibold text-gray-700">Exames ({data.exames.length})</h2>
        </div>
        {data.exames.length === 0 ? (
          <p className="p-8 text-center text-gray-400">Nenhum exame encontrado</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-gray-50 border-b border-gray-200">
                <th className="text-left py-3 px-4 font-medium text-gray-500">Exame</th>
                <th className="text-left py-3 px-4 font-medium text-gray-500">Categoria</th>
                <th className="text-left py-3 px-4 font-medium text-gray-500">Resultado</th>
                <th className="text-left py-3 px-4 font-medium text-gray-500">Referencia</th>
                <th className="text-left py-3 px-4 font-medium text-gray-500">Status</th>
                <th className="text-left py-3 px-4 font-medium text-gray-500">Data</th>
              </tr>
            </thead>
            <tbody>
              {data.exames.map(e => (
                <tr key={e.exame_id} className="border-b border-gray-50 hover:bg-gray-50">
                  <td className="py-3 px-4 font-medium">{e.nome_exame}</td>
                  <td className="py-3 px-4">
                    <span className="px-2 py-0.5 rounded text-xs bg-gray-100 text-gray-600">{e.categoria}</span>
                  </td>
                  <td className="py-3 px-4 font-mono">
                    <span className="font-semibold">{e.valor_resultado}</span>
                    {e.unidade && <span className="text-gray-400 ml-1">{e.unidade}</span>}
                  </td>
                  <td className="py-3 px-4 text-gray-500">{e.valor_referencia}</td>
                  <td className="py-3 px-4"><StatusBadge status={e.status_resultado} /></td>
                  <td className="py-3 px-4 text-gray-500">{e.data_exame || '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
