import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

export default function ChatMessage({ role, content, sql }) {
  const [showSql, setShowSql] = useState(false);
  const isUser = role === 'user';

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
