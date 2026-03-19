import React from 'react';
import { Task } from '../types';
import StatusBadge from './StatusBadge';

interface TasksTableProps {
  tasks: Task[];
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

const STATE_BAR_COLORS: Record<string, string> = {
  SUCCESS: 'bg-green-400',
  RUNNING: 'bg-yellow-400',
  FAILED: 'bg-red-400',
  TIMEDOUT: 'bg-red-300',
  PENDING: 'bg-orange-300',
  QUEUED: 'bg-orange-300',
  CANCELED: 'bg-gray-300',
  CANCELLED: 'bg-gray-300',
  SKIPPED: 'bg-gray-200',
};

export default function TasksTable({ tasks }: TasksTableProps) {
  if (!tasks || tasks.length === 0) {
    return <div className="text-sm text-gray-400 italic py-2">No tasks</div>;
  }

  const maxDurationMs = Math.max(...tasks.map((t) => t.duration_ms ?? 0));

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-200">
            <th className="text-left py-2 px-3 font-medium text-gray-500">Task Key</th>
            <th className="text-left py-2 px-3 font-medium text-gray-500">Status</th>
            <th className="text-left py-2 px-3 font-medium text-gray-500">Duration</th>
            <th className="text-left py-2 px-3 font-medium text-gray-500">Attempt</th>
          </tr>
        </thead>
        <tbody>
          {tasks.map((task, idx) => {
            const pct = task.duration_ms && maxDurationMs > 0
              ? Math.max(2, Math.round((task.duration_ms / maxDurationMs) * 100))
              : 0;
            const barColor = STATE_BAR_COLORS[task.state] || 'bg-gray-300';
            return (
              <tr key={`${task.task_key}-${idx}`} className="border-b border-gray-100 hover:bg-gray-50">
                <td className="py-2 px-3 font-mono text-xs">{task.task_key}</td>
                <td className="py-2 px-3">
                  <StatusBadge status={task.state} size="sm" />
                </td>
                <td className="py-2 px-3">
                  <div className="flex flex-col gap-0.5 min-w-[100px]">
                    <span className="text-xs text-gray-600">{formatDuration(task.duration_ms)}</span>
                    {pct > 0 && (
                      <div className="w-full bg-gray-100 rounded-full h-1.5 overflow-hidden">
                        <div className={`${barColor} h-1.5 rounded-full`} style={{ width: `${pct}%` }} />
                      </div>
                    )}
                  </div>
                </td>
                <td className="py-2 px-3 text-gray-500">{task.attempt_number ?? 0}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
