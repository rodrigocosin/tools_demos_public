import React, { useState } from 'react';
import { Run } from '../types';
import StatusBadge from './StatusBadge';
import TasksTable from './TasksTable';

interface RunsTableProps {
  runs: Run[];
  loading: boolean;
}

function formatTime(ts?: number): string {
  if (!ts) return '-';
  return new Date(ts).toLocaleString();
}

function formatDuration(ms?: number): string {
  if (!ms) return '-';
  const seconds = Math.floor(ms / 1000);
  if (seconds < 60) return `${seconds}s`;
  const minutes = Math.floor(seconds / 60);
  const remainSec = seconds % 60;
  if (minutes < 60) return `${minutes}m ${remainSec}s`;
  const hours = Math.floor(minutes / 60);
  const remainMin = minutes % 60;
  return `${hours}h ${remainMin}m`;
}

interface JobParam {
  name: string;
  default?: string;
  value?: string | null;
}

function ParamsDisplay({ params }: { params: Record<string, unknown> }) {
  const entries = Object.entries(params);
  if (entries.length === 0) return <span className="text-gray-400 italic">none</span>;

  return (
    <div className="space-y-1.5">
      {entries.map(([key, value]) => {
        if (key === 'job_parameters' && Array.isArray(value)) {
          const jobParams = value as JobParam[];
          return (
            <div key={key} className="space-y-0.5">
              {jobParams.map((p) => (
                <div key={p.name} className="flex items-baseline gap-1 text-xs">
                  <span className="font-medium text-indigo-600">{p.name}</span>
                  <span className="text-gray-300">=</span>
                  <span className="font-mono bg-gray-100 text-gray-800 px-1.5 py-0.5 rounded text-[11px]">
                    {p.value ?? p.default ?? <span className="text-gray-400">null</span>}
                  </span>
                </div>
              ))}
            </div>
          );
        }
        if (key === 'notebook_params' && typeof value === 'object' && value !== null) {
          const nbParams = value as Record<string, string>;
          return (
            <div key={key} className="space-y-0.5">
              {Object.entries(nbParams).map(([k, v]) => (
                <div key={k} className="flex items-baseline gap-1 text-xs">
                  <span className="font-medium text-purple-600">{k}</span>
                  <span className="text-gray-300">=</span>
                  <span className="font-mono bg-gray-100 text-gray-800 px-1.5 py-0.5 rounded text-[11px]">{v}</span>
                </div>
              ))}
            </div>
          );
        }
        return (
          <div key={key} className="text-xs">
            <span className="font-medium text-gray-600">{key}:</span>{' '}
            <span className="text-gray-800 font-mono bg-gray-100 px-1 rounded text-[11px]">
              {typeof value === 'object' ? JSON.stringify(value) : String(value)}
            </span>
          </div>
        );
      })}
    </div>
  );
}

const STATE_BAR_COLORS: Record<string, string> = {
  SUCCESS: 'bg-green-400',
  RUNNING: 'bg-yellow-400',
  FAILED: 'bg-red-400',
  TIMEDOUT: 'bg-red-300',
  PENDING: 'bg-orange-300',
  QUEUED: 'bg-orange-300',
  CANCELED: 'bg-gray-300',
  CANCELLED: 'bg-gray-300',
};

function DurationBar({ durationMs, maxMs, state }: { durationMs?: number; maxMs: number; state: string }) {
  if (!durationMs || maxMs === 0) {
    return <span className="text-gray-400 text-xs">{formatDuration(durationMs)}</span>;
  }
  const pct = Math.max(2, Math.round((durationMs / maxMs) * 100));
  const barColor = STATE_BAR_COLORS[state] || 'bg-gray-300';
  return (
    <div className="flex flex-col gap-0.5 min-w-[80px]">
      <span className="text-xs text-gray-600">{formatDuration(durationMs)}</span>
      <div className="w-full bg-gray-100 rounded-full h-1.5 overflow-hidden">
        <div className={`${barColor} h-1.5 rounded-full`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

export default function RunsTable({ runs, loading }: RunsTableProps) {
  const [expandedRun, setExpandedRun] = useState<number | null>(null);

  if (loading) {
    return (
      <div className="space-y-2">
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-12 bg-gray-100 animate-pulse rounded"></div>
        ))}
      </div>
    );
  }

  if (runs.length === 0) {
    return <div className="text-gray-400 text-center py-6 italic">No runs found</div>;
  }

  const maxDurationMs = Math.max(...runs.map((r) => r.duration_ms ?? 0));

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b-2 border-gray-200 bg-gray-50">
            <th className="text-left py-3 px-4 font-semibold text-gray-600 w-8"></th>
            <th className="text-left py-3 px-4 font-semibold text-gray-600">Run ID</th>
            <th className="text-left py-3 px-4 font-semibold text-gray-600">Status</th>
            <th className="text-left py-3 px-4 font-semibold text-gray-600">Start Time</th>
            <th className="text-left py-3 px-4 font-semibold text-gray-600">Duration</th>
            <th className="text-left py-3 px-4 font-semibold text-gray-600">Trigger</th>
            <th className="text-left py-3 px-4 font-semibold text-gray-600">Parameters</th>
          </tr>
        </thead>
        <tbody>
          {runs.map((run) => (
            <React.Fragment key={run.run_id}>
              <tr
                className={`border-b border-gray-100 hover:bg-blue-50 cursor-pointer transition-colors ${
                  expandedRun === run.run_id ? 'bg-blue-50' : ''
                }`}
                onClick={() => setExpandedRun(expandedRun === run.run_id ? null : run.run_id)}
              >
                <td className="py-3 px-4 text-gray-400">
                  <span className={`inline-block transition-transform ${expandedRun === run.run_id ? 'rotate-90' : ''}`}>
                    &#9654;
                  </span>
                </td>
                <td className="py-3 px-4">
                  {run.run_page_url ? (
                    <a
                      href={run.run_page_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-blue-600 hover:underline font-mono text-xs"
                      onClick={(e) => e.stopPropagation()}
                    >
                      {run.run_id}
                    </a>
                  ) : (
                    <span className="font-mono text-xs">{run.run_id}</span>
                  )}
                </td>
                <td className="py-3 px-4">
                  <StatusBadge status={run.state} />
                </td>
                <td className="py-3 px-4 text-gray-600 text-xs">{formatTime(run.start_time)}</td>
                <td className="py-3 px-4">
                  <DurationBar durationMs={run.duration_ms} maxMs={maxDurationMs} state={run.state} />
                </td>
                <td className="py-3 px-4 text-gray-500 text-xs">{run.trigger || '-'}</td>
                <td className="py-3 px-4">
                  <ParamsDisplay params={run.params} />
                </td>
              </tr>
              {expandedRun === run.run_id && (
                <tr>
                  <td colSpan={7} className="bg-gray-50 px-8 py-4">
                    <div className="mb-2 font-medium text-gray-700 text-sm">
                      Tasks ({run.tasks.length})
                      {run.state_message && (
                        <span className="ml-4 font-normal text-gray-500 text-xs">
                          {run.state_message}
                        </span>
                      )}
                    </div>
                    <TasksTable tasks={run.tasks} />
                  </td>
                </tr>
              )}
            </React.Fragment>
          ))}
        </tbody>
      </table>
    </div>
  );
}
