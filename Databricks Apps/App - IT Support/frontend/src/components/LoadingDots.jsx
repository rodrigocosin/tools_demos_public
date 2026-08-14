import React from 'react';

export default function LoadingDots() {
  return (
    <div className="flex justify-start mb-3">
      <div className="bg-db-surface border border-db-primary/20 rounded-2xl rounded-bl-md px-4 py-3">
        <div className="flex items-center gap-1.5">
          <span className="w-2 h-2 bg-db-muted rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></span>
          <span className="w-2 h-2 bg-db-muted rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></span>
          <span className="w-2 h-2 bg-db-muted rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></span>
        </div>
      </div>
    </div>
  );
}
