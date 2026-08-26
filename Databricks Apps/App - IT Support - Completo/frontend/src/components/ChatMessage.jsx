import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

export default function ChatMessage({ role, content, sql, references }) {
  const [showSql, setShowSql] = useState(false);
  const isUser = role === 'user';
  const hasRefs = !isUser && Array.isArray(references) && references.length > 0;

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-3`}>
      <div
        className={`max-w-[85%] rounded-2xl px-4 py-3 ${
          isUser
            ? 'bg-db-primary text-white rounded-br-md'
            : 'bg-db-surface text-db-light rounded-bl-md border border-db-primary/20'
        }`}
      >
        {isUser ? (
          <p className="text-sm leading-relaxed">{content}</p>
        ) : (
          <div className="markdown-content text-sm leading-relaxed">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
          </div>
        )}

        {hasRefs && (
          <div className="mt-3 pt-2.5 border-t border-db-primary/30">
            <p className="text-[10px] font-semibold text-db-muted mb-1.5 uppercase tracking-wider flex items-center gap-1">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                <polyline points="14 2 14 8 20 8" />
              </svg>
              Fontes
            </p>
            <ul className="space-y-1">
              {references.map((r, i) => {
                const label = `${r.title}${r.page != null ? ` · p. ${r.page}` : ''}`;
                return (
                  <li key={i} className="text-xs">
                    {r.url ? (
                      <a
                        href={r.url}
                        target="_blank"
                        rel="noreferrer"
                        className="text-db-accent hover:underline break-all"
                      >
                        {label}
                      </a>
                    ) : (
                      <span className="text-db-light break-all">{label}</span>
                    )}
                  </li>
                );
              })}
            </ul>
          </div>
        )}

        {sql && (
          <div className="mt-2 pt-2 border-t border-db-primary/30">
            <button
              onClick={() => setShowSql(!showSql)}
              className="text-xs text-db-muted hover:text-db-accent transition-colors flex items-center gap-1"
            >
              <span>{showSql ? '▾' : '▸'}</span>
              {showSql ? 'Ocultar SQL' : 'Ver SQL'}
            </button>
            {showSql && (
              <pre className="mt-2 bg-db-darker p-3 rounded-lg text-xs text-green-300 overflow-x-auto">
                <code>{sql}</code>
              </pre>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
