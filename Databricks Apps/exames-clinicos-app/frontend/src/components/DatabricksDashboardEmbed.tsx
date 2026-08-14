import { useEffect, useRef, useState } from 'react'
import { DatabricksDashboard } from '@databricks/aibi-client'
import LoadingSpinner from './LoadingSpinner'

interface DashboardConfig {
  instanceUrl: string
  workspaceId: string
  dashboardId: string
}

async function fetchDashboardConfig(): Promise<DashboardConfig> {
  const r = await fetch('/api/dashboard-token')
  if (!r.ok) throw new Error(`Erro ao obter configuração: ${r.status}`)
  return r.json()
}

export default function DatabricksDashboardEmbed() {
  const containerRef = useRef<HTMLDivElement>(null)
  const dashboardRef = useRef<DatabricksDashboard | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let dashboard: DatabricksDashboard | null = null

    fetchDashboardConfig()
      .then(({ instanceUrl, workspaceId, dashboardId }) => {
        if (!containerRef.current) return

        dashboard = new DatabricksDashboard({
          instanceUrl,
          workspaceId,
          dashboardId,
          container: containerRef.current,
          // No token — auth via Databricks Apps session cookie
          token: undefined,
          colorScheme: 'light',
          config: { version: 1 },
        })
        dashboard.initialize()
        dashboardRef.current = dashboard
        setLoading(false)
      })
      .catch((e: unknown) => {
        setError(e instanceof Error ? e.message : 'Erro ao carregar dashboard')
        setLoading(false)
      })

    return () => {
      dashboard?.destroy()
    }
  }, [])

  return (
    <div className="relative w-full" style={{ height: '85vh' }}>
      {loading && (
        <div className="absolute inset-0 flex items-center justify-center bg-white rounded-2xl">
          <LoadingSpinner />
        </div>
      )}
      {error && (
        <div className="absolute inset-0 flex items-center justify-center bg-white rounded-2xl">
          <p className="text-red-500 text-sm">{error}</p>
        </div>
      )}
      <div
        ref={containerRef}
        className="w-full h-full rounded-2xl overflow-hidden border border-gray-100 shadow-sm"
      />
    </div>
  )
}
