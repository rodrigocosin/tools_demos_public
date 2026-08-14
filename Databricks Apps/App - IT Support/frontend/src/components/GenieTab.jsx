import React, { useState, useRef, useEffect } from 'react';
import ChatMessage from './ChatMessage';
import ChatInput from './ChatInput';
import SuggestedChips from './SuggestedChips';
import LoadingDots from './LoadingDots';

const SUGGESTIONS = [
  'Quais países têm mais tickets abertos?',
  'Qual o tempo médio de resolução por prioridade?',
  'Me mostre a distribuição de tickets por tópico',
  'Quantos tickets P1 foram abertos esse mês?',
  'Quais agentes têm melhor taxa de resolução?',
  'Qual o volume de tickets por canal de atendimento?',
];

export default function GenieTab() {
  const [messages, setMessages] = useState([]);
  const [conversationId, setConversationId] = useState(null);
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
      const body = { question };
      if (conversationId) body.conversation_id = conversationId;

      const resp = await fetch('/api/genie', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });

      if (!resp.ok) throw new Error(`Erro ${resp.status}: ${await resp.text()}`);
      const result = await resp.json();

      if (result.conversation_id) setConversationId(result.conversation_id);

      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: result.text || 'Sem resposta.', sql: result.sql || null },
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
            <div className="text-5xl mb-4">🧞</div>
            <h2 className="text-lg font-semibold text-white mb-2">Genie — Sala Chamados IT</h2>
            <p className="text-sm text-db-muted mb-6 max-w-md">
              Faça perguntas em linguagem natural sobre os dados de chamados de TI.
              O Genie gera consultas SQL automaticamente.
            </p>
            <SuggestedChips suggestions={SUGGESTIONS} onSelect={sendMessage} disabled={loading} />
          </div>
        )}

        {messages.map((msg, i) => (
          <ChatMessage key={i} role={msg.role} content={msg.content} sql={msg.sql} />
        ))}

        {loading && <LoadingDots />}
      </div>

      {messages.length > 0 && !loading && (
        <SuggestedChips suggestions={SUGGESTIONS} onSelect={sendMessage} disabled={loading} />
      )}

      <ChatInput onSend={sendMessage} disabled={loading} placeholder="Pergunte sobre os chamados de TI..." />
    </div>
  );
}
