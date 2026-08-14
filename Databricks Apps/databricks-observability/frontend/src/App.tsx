import React, { useState, useEffect, useCallback } from 'react';
import { Job, Run, Stats } from './types';
import StatsCards from './components/StatsCards';
import JobsTable from './components/JobsTable';
import RunsTable from './components/RunsTable';
import StatusBadge from './components/StatusBadge';
import JobTasksView from './components/JobTasksView';

type TabId = 'dashboard' | 'job-tasks';

const ACTIVE_STATES = new Set(['RUNNING', 'PENDING', 'QUEUED', 'BLOCKED']);

const REFRESH_INTERVAL = 30000;

function App() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [activeRuns, setActiveRuns] = useState<Run[]>([]);
  const [loadingStats, setLoadingStats] = useState(true);
  const [loadingJobs, setLoadingJobs] = useState(true);
  const [loadingActive, setLoadingActive] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<string | null>(null);
  const [lastRefresh, setLastRefresh] = useState<Date>(new Date());
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<TabId>('dashboard');
  const [refreshKey, setRefreshKey] = useState(0);

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch('/api/stats');
      if (!res.ok) throw new Error(`Stats API error: ${res.status}`);
      setStats(await res.json());
      setError(null);
    } catch (err) {
      setError(String(err));
    } finally {
      setLoadingStats(false);
    }
  }, []);

  const fetchActiveRuns = useCallback(async () => {
    setLoadingActive(true);
    try {
      const res = await fetch('/api/runs/active');
      if (!res.ok) throw new Error(`Active runs API error: ${res.status}`);
      const data = await res.json();
      // Client-side guard: only keep truly active states to prevent stale runs from leaking in
      setActiveRuns((data.runs as Run[]).filter(r => ACTIVE_STATES.has(r.state)));
    } catch (err) {
      console.error('Failed to fetch active runs:', err);
    } finally {
      setLoadingActive(false);
    }
  }, []);

  const fetchJobs = useCallback(async () => {
    try {
      const res = await fetch(`/api/jobs?limit=200`);
      if (!res.ok) throw new Error(`Jobs API error: ${res.status}`);
      const data = await res.json();
      setJobs(data.jobs);
      setError(null);
    } catch (err) {
      setError(String(err));
    } finally {
      setLoadingJobs(false);
    }
  }, []);

  const refresh = useCallback(() => {
    setLoadingStats(true);
    setLoadingJobs(true);
    fetchStats();
    fetchJobs();
    fetchActiveRuns();
    setRefreshKey(k => k + 1);
    setLastRefresh(new Date());
  }, [fetchStats, fetchJobs, fetchActiveRuns]);

  useEffect(() => {
    refresh();
  }, []);

  // Build a map of job_id -> active run states for badges in JobsTable
  const activeJobIds = new Set(activeRuns.map((r) => r.job_id));

  // Client-side filtering: global text + status card filter
  const filteredJobs = jobs.filter((job) => {
    // Use the actual latest_run.state; fall back to RUNNING if job is active but state not yet loaded
    const jobState = job.latest_run?.state ?? (activeJobIds.has(job.job_id) ? 'RUNNING' : '');
    if (statusFilter) {
      if (statusFilter === 'PENDING') {
        if (!['PENDING', 'QUEUED', 'BLOCKED'].includes(jobState)) return false;
      } else if (statusFilter === 'RUNNING') {
        // Show jobs that are currently active OR whose latest run state is RUNNING
        if (!activeJobIds.has(job.job_id) && jobState !== 'RUNNING') return false;
      } else {
        if (jobState !== statusFilter) return false;
      }
    }
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      const paramsStr = job.latest_run?.params
        ? JSON.stringify(job.latest_run.params).toLowerCase()
        : '';
      return (
        job.name.toLowerCase().includes(q) ||
        String(job.job_id).includes(q) ||
        jobState.toLowerCase().includes(q) ||
        (job.creator_user_name ?? '').toLowerCase().includes(q) ||
        paramsStr.includes(q)
      );
    }
    return true;
  });

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Databricks Observability</h1>
              <p className="text-sm text-gray-500 mt-0.5">Jobs & Runs Monitoring Dashboard</p>
            </div>
            <div className="flex items-center gap-4">
              <span className="text-xs text-gray-400">
                Last refresh: {lastRefresh.toLocaleTimeString()}
              </span>
              <button
                onClick={refresh}
                className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
              >
                Refresh
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Tab bar */}
      <div className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <nav className="flex gap-1">
            {([
              { id: 'dashboard', label: 'Dashboard' },
              { id: 'job-tasks', label: 'Jobs & Tasks' },
            ] as { id: TabId; label: string }[]).map(tab => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
                  activeTab === tab.id
                    ? 'border-blue-600 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </nav>
        </div>
      </div>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {error && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
            Error: {error}
          </div>
        )}

        {activeTab === 'job-tasks' && (
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
            <h2 className="text-lg font-semibold text-gray-800 mb-4">Jobs &amp; Task Definitions</h2>
            <JobTasksView refreshKey={refreshKey} />
          </div>
        )}

        {activeTab === 'dashboard' && <>

        <StatsCards stats={stats} loading={loadingStats} activeFilter={statusFilter} onFilter={setStatusFilter} />

        {/* Active Runs Section */}
        <div className="mb-6 bg-white rounded-xl shadow-sm border border-yellow-300 p-4">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-lg font-semibold text-gray-800 flex items-center gap-2">
              <span className="inline-block w-2.5 h-2.5 rounded-full bg-yellow-400 animate-pulse"></span>
              Active Runs
              {!loadingActive && (
                <span className="ml-2 text-sm font-normal text-gray-500">
                  ({activeRuns.length} run{activeRuns.length !== 1 ? 's' : ''})
                </span>
              )}
            </h2>
          </div>
          {loadingActive ? (
            <div className="space-y-2">
              {[1, 2].map((i) => (
                <div key={i} className="h-10 bg-gray-100 animate-pulse rounded"></div>
              ))}
            </div>
          ) : activeRuns.length === 0 ? (
            <div className="text-sm text-gray-400 py-4 text-center">No active runs at this moment</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-xs text-gray-500 border-b border-gray-100">
                    <th className="pb-2 pr-4">Run ID</th>
                    <th className="pb-2 pr-4">Job</th>
                    <th className="pb-2 pr-4">Run Name</th>
                    <th className="pb-2 pr-4">Status</th>
                    <th className="pb-2 pr-4">Started</th>
                    <th className="pb-2 pr-4">Tasks</th>
                    <th className="pb-2">Parameters</th>
                  </tr>
                </thead>
                <tbody>
                  {activeRuns.map((run) => (
                    <tr key={run.run_id} className="border-b border-gray-50 hover:bg-yellow-50 transition-colors">
                      <td className="py-2 pr-4 font-mono text-xs text-gray-600">
                        {run.run_page_url ? (
                          <a href={run.run_page_url} target="_blank" rel="noreferrer" className="text-blue-600 hover:underline">
                            {run.run_id}
                          </a>
                        ) : run.run_id}
                      </td>
                      <td className="py-2 pr-4 text-xs text-gray-700">
                        {(run as any).job_name || run.job_id}
                        <div className="text-gray-400 font-mono">#{run.job_id}</div>
                      </td>
                      <td className="py-2 pr-4 text-gray-700">{run.run_name || '—'}</td>
                      <td className="py-2 pr-4"><StatusBadge status={run.state} /></td>
                      <td className="py-2 pr-4 text-xs text-gray-500">
                        {run.start_time ? new Date(run.start_time).toLocaleString() : '—'}
                      </td>
                      <td className="py-2 pr-4 text-xs text-gray-500">
                        {run.tasks.length > 0 ? (
                          <span>
                            {run.tasks.filter(t => t.state === 'RUNNING').length} running,{' '}
                            {run.tasks.filter(t => ['FAILED','ERROR'].includes(t.state)).length} failed
                            {' '}/ {run.tasks.length} total
                          </span>
                        ) : '—'}
                      </td>
                      <td className="py-2 text-xs text-gray-500">
                        {Object.keys(run.params).length === 0 ? (
                          <span className="text-gray-300">none</span>
                        ) : (
                          <details>
                            <summary className="cursor-pointer text-blue-500 hover:underline">
                              {Object.keys(run.params).length} param group{Object.keys(run.params).length !== 1 ? 's' : ''}
                            </summary>
                            <pre className="mt-1 text-xs bg-gray-50 p-2 rounded max-w-xs overflow-auto">
                              {JSON.stringify(run.params, null, 2)}
                            </pre>
                          </details>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Filters + Jobs List */}
        <div className="mb-4 flex items-center gap-3 flex-wrap">
          <div className="flex-1 min-w-[200px]">
            <input
              type="text"
              placeholder="Filtrar por nome, ID, status, usuário..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full max-w-lg px-4 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
          {(searchQuery || statusFilter) && (
            <button
              onClick={() => { setSearchQuery(''); setStatusFilter(null); }}
              className="text-xs px-3 py-1.5 bg-gray-100 hover:bg-gray-200 text-gray-600 rounded-md transition-colors"
            >
              Limpar filtros
            </button>
          )}
          <div className="text-sm text-gray-500 ml-auto">
            {filteredJobs.length} de {jobs.length} job{jobs.length !== 1 ? 's' : ''}
            {statusFilter && <span className="ml-2 px-2 py-0.5 bg-blue-100 text-blue-700 rounded-full text-xs font-medium">{statusFilter}</span>}
          </div>
        </div>

        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
          <h2 className="text-lg font-semibold text-gray-800 mb-4">All Jobs</h2>
          <JobsTable jobs={filteredJobs} loading={loadingJobs} activeJobIds={activeJobIds} />
        </div>

        </>}
      </main>
    </div>
  );
}

export default App;
