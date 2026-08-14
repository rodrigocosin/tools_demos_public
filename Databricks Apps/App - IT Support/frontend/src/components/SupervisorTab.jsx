import React, { useState, useRef, useEffect } from 'react';
import ChatMessage from './ChatMessage';
import ChatInput from './ChatInput';
import LoadingDots from './LoadingDots';

const SUGGESTIONS = [
  { text: 'Quantos tickets foram abertos por país?', tag: '🧞 Genie' },
  { text: 'Qual o tempo médio de resolução dos tickets críticos?', tag: '🧞 Genie' },
  { text: 'Qual é o prazo de SLA para chamados P1?', tag: '📚 Knowledge Agent' },
  { text: 'Como funciona a escalação entre N1, N2 e N3?', tag: '📚 Knowledge Agent' },
  { text: 'Quantos tickets P1 estouraram o SLA? E qual deveria ser o prazo?', tag: '🤝 Colaboração' },
  { text: 'Quais países têm mais tickets fora do SLA? E quais ações a política recomenda?', tag: '🤝 Colaboração' },
  { text: 'Qual o tempo médio de primeira resposta e o que a política diz sobre isso?', tag: '🤝 Colaboração' },
];

const TAG_COLORS = {
  '🧞 Genie': 'border-purple-500/40 text-purple-300',
  '📚 Knowledge Agent': 'border-blue-500/40 text-blue-300',
  '🤝 Colaboração': 'border-green-500/40 text-green-300',
};

function SuggestionCards({ onSelect, disabled, compact }) {
  if (compact) {
    return (
      <div className="flex gap-2 px-4 py-2 overflow-x-auto scrollbar-hide">
        {SUGGESTIONS.map((s, i) => (
          <button
            key={i}
            onClick={() => onSelect(s.text)}
            disabled={disabled}
            className="flex-none flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-db-surface border border-db-primary/20
                       hover:border-db-accent/50 hover:bg-db-surface/80 transition-all
                       disabled:opacity-40 disabled:cursor-not-allowed whitespace-nowrap"
          >
            <span className={`text-[10px] font-medium border rounded-full px-1.5 py-0.5 ${TAG_COLORS[s.tag] || 'border-db-primary/30 text-db-muted'}`}>
              {s.tag}
            </span>
            <span className="text-xs text-white">{s.text}</span>
          </button>
        ))}
      </div>
    );
  }

  return (
    <div className="flex flex-wrap gap-2 px-4 py-3 justify-center max-w-4xl mx-auto w-full">
      {SUGGESTIONS.map((s, i) => (
        <button
          key={i}
          onClick={() => onSelect(s.text)}
          disabled={disabled}
          className="text-left px-3 py-2 rounded-lg bg-db-surface border border-db-primary/20
                     hover:border-db-accent/50 hover:bg-db-surface/80 transition-all
                     disabled:opacity-40 disabled:cursor-not-allowed max-w-xs"
        >
          <span className={`text-[10px] font-medium border rounded-full px-2 py-0.5 mb-1 inline-block ${TAG_COLORS[s.tag] || 'border-db-primary/30 text-db-muted'}`}>
            {s.tag}
          </span>
          <p className="text-xs text-white leading-snug">{s.text}</p>
        </button>
      ))}
    </div>
  );
}

export default function SupervisorTab() {
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const scrollRef = useRef(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, loading]);

  const sendMessage = async (question) => {
    setMessages((prev) => [...prev, { role: 'user', content: question }]);
    setLoading(true);

    try {
      const resp = await fetch('/api/supervisor', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question }),
      });

      if (!resp.ok) throw new Error(`Erro ${resp.status}: ${await resp.text()}`);
      const result = await resp.json();

      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: result.answer || 'Sem resposta.' },
      ]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: `Erro: ${err.message}` },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="h-full flex flex-col">
      <div ref={scrollRef} className="flex-1 overflow-y-auto p-4">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <div className="text-5xl mb-4">🤖</div>
            <h2 className="text-lg font-semibold text-white mb-2">Agente Supervisor</h2>
            <p className="text-sm text-db-muted mb-6 max-w-md">
              Agente inteligente que combina análise de dados (Genie) e
              base de conhecimento (RAG) para responder qualquer dúvida sobre o suporte de TI.
            </p>
            <SuggestionCards onSelect={sendMessage} disabled={loading} />
          </div>
        )}

        {messages.map((msg, i) => (
          <ChatMessage key={i} role={msg.role} content={msg.content} />
        ))}

        {loading && <LoadingDots />}
      </div>

      {messages.length > 0 && !loading && (
        <SuggestionCards onSelect={sendMessage} disabled={loading} compact />
      )}

      <ChatInput onSend={sendMessage} disabled={loading} placeholder="Pergunte qualquer coisa sobre o suporte de TI..." />
    </div>
  );
}
