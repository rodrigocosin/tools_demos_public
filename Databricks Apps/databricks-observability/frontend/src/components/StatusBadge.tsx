import React from 'react';

interface StatusBadgeProps {
  status: string;
  size?: 'sm' | 'md';
}

const STATUS_COLORS: Record<string, string> = {
  SUCCESS: 'bg-green-100 text-green-800 border-green-200',
  RUNNING: 'bg-yellow-100 text-yellow-800 border-yellow-200',
  PENDING: 'bg-yellow-50 text-yellow-700 border-yellow-200',
  QUEUED: 'bg-yellow-50 text-yellow-700 border-yellow-200',
  BLOCKED: 'bg-orange-100 text-orange-800 border-orange-200',
  FAILED: 'bg-red-100 text-red-800 border-red-200',
  TIMEDOUT: 'bg-red-100 text-red-700 border-red-200',
  CANCELED: 'bg-gray-100 text-gray-600 border-gray-200',
  CANCELLED: 'bg-gray-100 text-gray-600 border-gray-200',
  SKIPPED: 'bg-gray-100 text-gray-500 border-gray-200',
  TERMINATED: 'bg-gray-100 text-gray-600 border-gray-200',
  UNKNOWN: 'bg-gray-50 text-gray-400 border-gray-200',
};

const STATUS_DOTS: Record<string, string> = {
  SUCCESS: 'bg-green-500',
  RUNNING: 'bg-yellow-500 animate-pulse',
  PENDING: 'bg-yellow-400 animate-pulse',
  QUEUED: 'bg-yellow-400 animate-pulse',
  BLOCKED: 'bg-orange-500',
  FAILED: 'bg-red-500',
  TIMEDOUT: 'bg-red-400',
  CANCELED: 'bg-gray-400',
  CANCELLED: 'bg-gray-400',
  SKIPPED: 'bg-gray-300',
  TERMINATED: 'bg-gray-400',
  UNKNOWN: 'bg-gray-300',
};

export default function StatusBadge({ status, size = 'md' }: StatusBadgeProps) {
  const colorClass = STATUS_COLORS[status] || STATUS_COLORS.UNKNOWN;
  const dotClass = STATUS_DOTS[status] || STATUS_DOTS.UNKNOWN;
  const sizeClass = size === 'sm' ? 'text-xs px-2 py-0.5' : 'text-xs px-2.5 py-1';

  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full border font-medium ${colorClass} ${sizeClass}`}>
      <span className={`inline-block w-1.5 h-1.5 rounded-full ${dotClass}`}></span>
      {status}
    </span>
  );
}
