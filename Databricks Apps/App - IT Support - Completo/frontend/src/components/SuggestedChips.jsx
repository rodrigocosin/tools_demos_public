import React from 'react';

export default function SuggestedChips({ suggestions, onSelect, disabled }) {
  return (
    <div className="flex flex-wrap gap-2 px-4 py-3">
      {suggestions.map((s, i) => (
        <button
          key={i}
          onClick={() => onSelect(s)}
          disabled={disabled}
          className="text-xs bg-db-surface hover:bg-db-card border border-db-primary/30
                     text-db-light rounded-full px-3 py-1.5 transition-colors
                     disabled:opacity-40 disabled:cursor-not-allowed
                     hover:border-db-accent/50"
        >
          {s}
        </button>
      ))}
    </div>
  );
}
