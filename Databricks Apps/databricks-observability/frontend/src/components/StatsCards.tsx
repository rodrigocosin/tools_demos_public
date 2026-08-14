import React from 'react';
import { Stats } from '../types';

interface StatsCardsProps {
  stats: Stats | null;
  loading: boolean;
  activeFilter: string | null;
  onFilter: (filter: string | null) => void;
}

export default function StatsCards({ stats, loading, activeFilter, onFilter }: StatsCardsProps) {
  const cards = [
    { label: 'Total Jobs', value: stats?.total_jobs ?? '-', filter: null, color: 'border-blue-500', bg: 'bg-blue-50', text: 'text-blue-700', ring: 'ring-blue-400' },
    { label: 'Running', value: stats?.running ?? '-', filter: 'RUNNING', color: 'border-yellow-500', bg: 'bg-yellow-50', text: 'text-yellow-700', ring: 'ring-yellow-400' },
    { label: 'Failed', value: stats?.failed ?? '-', filter: 'FAILED', color: 'border-red-500', bg: 'bg-red-50', text: 'text-red-700', ring: 'ring-red-400' },
    { label: 'Success', value: stats?.success ?? '-', filter: 'SUCCESS', color: 'border-green-500', bg: 'bg-green-50', text: 'text-green-700', ring: 'ring-green-400' },
    { label: 'Pending', value: stats?.pending ?? '-', filter: 'PENDING', color: 'border-orange-500', bg: 'bg-orange-50', text: 'text-orange-700', ring: 'ring-orange-400' },
  ];

  return (
    <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
      {cards.map((card) => {
        const isActive = activeFilter === card.filter && card.filter !== null;
        const isClickable = card.filter !== null;
        return (
          <div
            key={card.label}
            onClick={() => isClickable && onFilter(isActive ? null : card.filter)}
            className={`${card.bg} border-l-4 ${card.color} rounded-lg p-4 shadow-sm transition-all
              ${isClickable ? 'cursor-pointer hover:shadow-md hover:scale-[1.02]' : ''}
              ${isActive ? `ring-2 ${card.ring} shadow-md scale-[1.02]` : ''}
            `}
          >
            <div className="text-sm font-medium text-gray-600 flex items-center justify-between">
              {card.label}
              {isActive && <span className="text-xs text-gray-400">✕</span>}
            </div>
            <div className={`text-2xl font-bold ${card.text} mt-1`}>
              {loading ? (
                <span className="inline-block w-8 h-7 bg-gray-200 animate-pulse rounded"></span>
              ) : (
                card.value
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
