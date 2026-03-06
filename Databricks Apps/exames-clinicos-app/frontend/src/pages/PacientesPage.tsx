import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useApi } from '../hooks/useApi'
import LoadingSpinner from '../components/LoadingSpinner'
import { Users, User, TestTubes, FileUp, Search, X } from 'lucide-react'

interface Paciente {
  cpf: string
  nome: string
  idade: string | null
  sexo: string | null
  medico_solicitante: string | null
  criado_em: string
  total_exames: string
  total_uploads: string
}

export default function PacientesPage() {
  const { data, loading, error } = useApi<{ pacientes: Paciente[] }>('/api/pacientes')
  const [search, setSearch] = useState('')

  if (loading) return <LoadingSpinner />
  if (error) return <div className="text-red-500 p-8">Erro: {error}</div>

  const q = search.toLowerCase().trim()
  const pacientes = (data?.pacientes ?? []).filter(p =>
    !q ||
    p.nome.toLowerCase().includes(q) ||
    p.cpf.toLowerCase().includes(q) ||
    (p.medico_solicitante ?? '').toLowerCase().includes(q)
  )

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Pacientes</h1>
          <p className="text-gray-500 text-sm mt-1">Lista de pacientes com exames processados</p>
        </div>
        <span className="text-sm text-gray-400">{pacientes.length} de {data?.pacientes?.length ?? 0}</span>
      </div>

      {/* Search */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-3 mb-5 flex items-center gap-2">
        <Search className="w-4 h-4 text-gray-400 shrink-0" />
        <input
          type="text"
          placeholder="Buscar por nome, CPF ou médico..."
          value={search}
          onChange={e => setSearch(e.target.value)}
          className="flex-1 text-sm outline-none placeholder-gray-400"
        />
        {search && (
          <button onClick={() => setSearch('')}>
            <X className="w-4 h-4 text-gray-400 hover:text-gray-600" />
          </button>
        )}
      </div>

      {!pacientes.length ? (
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-12 text-center text-gray-400">
          <Users className="w-12 h-12 mx-auto mb-2 opacity-50" />
          <p>Nenhum paciente encontrado</p>
          <p className="text-xs mt-2">Faca upload de exames para ver os pacientes</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {pacientes.map((p) => (
            <Link
              key={p.cpf}
              to={`/pacientes/${encodeURIComponent(p.cpf)}`}
              className="bg-white rounded-xl shadow-sm border border-gray-100 p-5 hover:shadow-md transition-shadow"
            >
              <div className="flex items-start gap-3">
                <div className="p-2 rounded-full bg-violet-50">
                  <User className="w-6 h-6 text-violet-500" />
                </div>
                <div className="flex-1">
                  <h3 className="font-semibold text-gray-800">{p.nome}</h3>
                  <div className="flex gap-3 text-xs text-gray-500 mt-1">
                    {p.idade && <span>{p.idade} anos</span>}
                    {p.sexo && <span>{p.sexo === 'M' ? 'Masculino' : p.sexo === 'F' ? 'Feminino' : p.sexo}</span>}
                  </div>
                  {p.medico_solicitante && (
                    <p className="text-xs text-gray-400 mt-1">Dr(a). {p.medico_solicitante}</p>
                  )}
                  <div className="flex gap-4 mt-3 pt-3 border-t border-gray-100">
                    <div className="flex items-center gap-1 text-xs text-gray-500">
                      <TestTubes className="w-3.5 h-3.5" />
                      <span>{p.total_exames} exames</span>
                    </div>
                    <div className="flex items-center gap-1 text-xs text-gray-500">
                      <FileUp className="w-3.5 h-3.5" />
                      <span>{p.total_uploads} uploads</span>
                    </div>
                  </div>
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}
