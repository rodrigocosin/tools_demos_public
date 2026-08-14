import React, { useState, useCallback } from 'react';
import { Job, Run } from '../types';
import RunsTable from './RunsTable';
import StatusBadge from './StatusBadge';

interface JobsTableProps {
  jobs: Job[];
  loading: boolean;
  activeJobIds?: Set<number>;
}

export default function JobsTable({ jobs, loading, activeJobIds = new Set() }: JobsTableProps) {
  const [expandedJob, setExpandedJob] = useState<number | null>(null);
  const [jobRuns, setJobRuns] = useState<Record<number, Run[]>>({});
  const [loadingRuns, setLoadingRuns] = useState<number | null>(null);

  const toggleJob = useCallback(async (jobId: number) => {
    if (expandedJob === jobId) {
      setExpandedJob(null);
      return;
    }
    setExpandedJob(jobId);
    // Always re-fetch to get fresh data (no stale cache)
    setLoadingRuns(jobId);
    try {
      const res = await fetch(`/api/jobs/${jobId}/runs?limit=25`);
      const data = await res.json();
      setJobRuns((prev) => ({ ...prev, [jobId]: data.runs }));
    } catch (err) {
      console.error('Failed to load runs:', err);
      setJobRuns((prev) => ({ ...prev, [jobId]: [] }));
    } finally {
      setLoadingRuns(null);
    }
  }, [expandedJob]);

  if (loading) {
    return (
      <div className="space-y-3">
        {[1, 2, 3, 4, 5].map((i) => (
          <div key={i} className="h-14 bg-gray-100 animate-pulse rounded-lg"></div>
        ))}
      </div>
    );
  }

  if (jobs.length === 0) {
    return (
      <div className="text-center py-12 text-gray-400">
        <div className="text-4xl mb-2">--</div>
        <div>No jobs found</div>
      </div>
    );
  }

  const statusOrder: Record<string, number> = {
    RUNNING: 0, PENDING: 1, QUEUED: 1, BLOCKED: 1,
    FAILED: 2, TIMEDOUT: 2,
    SUCCESS: 3,
  };
  const sorted = [...jobs].sort((a, b) => {
    if (activeJobIds.has(a.job_id) !== activeJobIds.has(b.job_id))
      return activeJobIds.has(a.job_id) ? -1 : 1;
    const aOrder = statusOrder[a.latest_run?.state ?? ''] ?? 4;
    const bOrder = statusOrder[b.latest_run?.state ?? ''] ?? 4;
    return aOrder - bOrder;
  });

  return (
    <div className="space-y-1">
      {sorted.map((job) => {
        const isActive = activeJobIds.has(job.job_id);
        return (
          <div
            key={job.job_id}
            className={`border rounded-lg overflow-hidden ${
              isActive ? 'border-yellow-400 bg-yellow-50' : 'border-gray-200'
            }`}
          >
            <div
              className={`flex items-center justify-between px-5 py-3 cursor-pointer transition-colors ${
                expandedJob === job.job_id
                  ? isActive ? 'bg-yellow-100 border-b border-yellow-300' : 'bg-gray-50 border-b border-gray-200'
                  : isActive ? 'hover:bg-yellow-100' : 'hover:bg-gray-50'
              }`}
              onClick={() => toggleJob(job.job_id)}
            >
              <div className="flex items-center gap-3 flex-1 min-w-0">
                <span
                  className={`text-gray-400 transition-transform inline-block flex-shrink-0 ${
                    expandedJob === job.job_id ? 'rotate-90' : ''
                  }`}
                >
                  &#9654;
                </span>
                <div className="flex-1 min-w-0">
                  <div className="font-medium text-gray-900 flex items-center gap-2 flex-wrap">
                    {job.name}
                  </div>
                  <div className="text-xs text-gray-400">
                    Job ID: {job.job_id}
                    {job.creator_user_name && <span className="ml-3">by {job.creator_user_name}</span>}
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-3 flex-shrink-0">
                {job.latest_run && (
                  <div className="flex items-center gap-2">
                    <StatusBadge status={isActive ? 'RUNNING' : job.latest_run.state} size="sm" />
                    {job.latest_run.start_time && (
                      <span className="text-xs text-gray-400">
                        {new Date(job.latest_run.start_time).toLocaleString()}
                      </span>
                    )}
                  </div>
                )}
                {!job.latest_run && (
                  <span className="text-xs text-gray-400">No runs yet</span>
                )}
              </div>
            </div>
            {expandedJob === job.job_id && (
              <div className="px-5 py-4 bg-white">
                <RunsTable
                  runs={jobRuns[job.job_id] || []}
                  loading={loadingRuns === job.job_id}
                />
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
