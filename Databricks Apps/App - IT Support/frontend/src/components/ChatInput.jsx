import React, { useState } from 'react';

export default function ChatInput({ onSend, disabled, placeholder }) {
  const [text, setText] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    const trimmed = text.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setText('');
  };

  return (
    <form onSubmit={handleSubmit} className="flex gap-2 px-4 py-3 border-t border-db-primary/30 bg-db-dark">
      <input
        type="text"
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder={placeholder || 'Digite sua pergunta...'}
        disabled={disabled}
        className="flex-1 bg-db-surface border border-db-primary/30 rounded-xl px-4 py-2.5 text-sm
                   text-white placeholder-db-muted focus:outline-none focus:border-db-accent/60
                   disabled:opacity-50 transition-colors"
      />
      <button
        type="submit"
        disabled={disabled || !text.trim()}
        className="bg-db-accent hover:bg-red-600 text-white rounded-xl px-5 py-2.5 text-sm font-medium
                   transition-colors disabled:opacity-40 disabled:cursor-not-allowed shrink-0"
      >
        Enviar
      </button>
    </form>
  );
}
