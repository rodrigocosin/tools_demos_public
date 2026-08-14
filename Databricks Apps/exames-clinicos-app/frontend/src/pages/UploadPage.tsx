import { useState, useCallback, useRef } from 'react'
import { Link } from 'react-router-dom'
import { Upload, FileText, CheckCircle, AlertCircle, Loader2, X } from 'lucide-react'
import { useApi } from '../hooks/useApi'
import StatusBadge from '../components/StatusBadge'
import LoadingSpinner from '../components/LoadingSpinner'

interface UploadResult {
  upload_id: string
  filename: string
  status: string
}

interface UploadsResponse {
  uploads: {
    upload_id: string
    paciente_id: string | null
    nome_arquivo: string
    status: string
    data_upload: string
    total_exames: string | null
  }[]
}

export default function UploadPage() {
  const [dragOver, setDragOver] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [results, setResults] = useState<UploadResult[]>([])
  const [uploadError, setUploadError] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const { data, loading, refetch } = useApi<UploadsResponse>('/api/uploads')

  const handleUpload = useCallback(async (files: FileList | File[]) => {
    setUploading(true)
    setUploadError(null)
    const newResults: UploadResult[] = []

    for (const file of Array.from(files)) {
      if (!file.name.toLowerCase().endsWith('.pdf')) {
        newResults.push({ upload_id: '', filename: file.name, status: 'erro: nao e PDF' })
        continue
      }
      const formData = new FormData()
      formData.append('file', file)
      try {
        const resp = await fetch('/api/upload', { method: 'POST', body: formData })
        if (!resp.ok) {
          const errBody = await resp.json().catch(() => ({}))
          throw new Error(errBody.detail || `HTTP ${resp.status}`)
        }
        const json = await resp.json()
        newResults.push({
          upload_id: json.upload_id,
          filename: json.filename,
          status: json.status,
        })
      } catch (err) {
        newResults.push({
          upload_id: '',
          filename: file.name,
          status: `erro: ${err instanceof Error ? err.message : 'desconhecido'}`,
        })
      }
    }

    setResults(prev => [...newResults, ...prev])
    setUploading(false)
    // Wait a bit and refetch uploads list
    setTimeout(() => refetch(), 2000)
  }, [refetch])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setDragOver(false)
    if (e.dataTransfer.files.length > 0) {
      handleUpload(e.dataTransfer.files)
    }
  }, [handleUpload])

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-800">Upload de Exames</h1>
        <p className="text-gray-500 text-sm mt-1">Envie PDFs de exames clinicos para analise com IA</p>
      </div>

      {/* Drop Zone */}
      <div
        className={`relative border-2 border-dashed rounded-xl p-12 text-center transition-all cursor-pointer mb-8 ${
          dragOver
            ? 'border-blue-400 bg-blue-50'
            : 'border-gray-300 bg-white hover:border-blue-300 hover:bg-gray-50'
        }`}
        onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf"
          multiple
          className="hidden"
          onChange={(e) => e.target.files && handleUpload(e.target.files)}
        />
        {uploading ? (
          <div className="flex flex-col items-center">
            <Loader2 className="w-12 h-12 text-blue-500 animate-spin mb-3" />
            <p className="text-blue-600 font-medium">Enviando arquivos...</p>
          </div>
        ) : (
          <>
            <Upload className="w-12 h-12 text-gray-400 mx-auto mb-3" />
            <p className="text-lg font-medium text-gray-600">
              Arraste PDFs aqui ou clique para selecionar
            </p>
            <p className="text-sm text-gray-400 mt-2">Aceita apenas arquivos PDF de exames clinicos</p>
          </>
        )}
      </div>

      {/* Upload Results */}
      {results.length > 0 && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5 mb-8">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold text-gray-700">Resultados do Upload</h2>
            <button
              onClick={() => setResults([])}
              className="text-gray-400 hover:text-gray-600"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
          <div className="space-y-2">
            {results.map((r, i) => (
              <div key={i} className="flex items-center gap-3 py-2 border-b border-gray-50 last:border-0">
                {r.status.startsWith('erro') ? (
                  <AlertCircle className="w-5 h-5 text-red-500 shrink-0" />
                ) : (
                  <CheckCircle className="w-5 h-5 text-green-500 shrink-0" />
                )}
                <span className="text-sm flex-1">{r.filename}</span>
                <StatusBadge status={r.status} />
                {r.upload_id && (
                  <Link
                    to={`/upload/${r.upload_id}`}
                    className="text-xs text-blue-500 hover:underline"
                  >
                    Ver detalhes
                  </Link>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {uploadError && (
        <div className="bg-red-50 text-red-700 rounded-lg p-4 mb-6">{uploadError}</div>
      )}

      {/* Uploads History */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
        <h2 className="font-semibold text-gray-700 mb-4">Historico de Uploads</h2>
        {loading ? (
          <LoadingSpinner />
        ) : !data?.uploads?.length ? (
          <div className="text-center py-8 text-gray-400">
            <FileText className="w-12 h-12 mx-auto mb-2 opacity-50" />
            <p>Nenhum upload realizado ainda</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200">
                  <th className="text-left py-3 px-4 font-medium text-gray-500">Arquivo</th>
                  <th className="text-left py-3 px-4 font-medium text-gray-500">Data</th>
                  <th className="text-left py-3 px-4 font-medium text-gray-500">Status</th>
                  <th className="text-left py-3 px-4 font-medium text-gray-500">Exames</th>
                  <th className="text-left py-3 px-4 font-medium text-gray-500">Acoes</th>
                </tr>
              </thead>
              <tbody>
                {data.uploads.map((u) => (
                  <tr key={u.upload_id} className="border-b border-gray-50 hover:bg-gray-50">
                    <td className="py-3 px-4">
                      <div className="flex items-center gap-2">
                        <FileText className="w-4 h-4 text-red-400" />
                        <span className="truncate max-w-[200px]">{u.nome_arquivo}</span>
                      </div>
                    </td>
                    <td className="py-3 px-4 text-gray-500">
                      {u.data_upload ? new Date(u.data_upload).toLocaleString('pt-BR') : '-'}
                    </td>
                    <td className="py-3 px-4"><StatusBadge status={u.status} /></td>
                    <td className="py-3 px-4">{u.total_exames || '-'}</td>
                    <td className="py-3 px-4">
                      <Link
                        to={`/upload/${u.upload_id}`}
                        className="text-blue-500 hover:underline text-sm"
                      >
                        Ver detalhes
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
