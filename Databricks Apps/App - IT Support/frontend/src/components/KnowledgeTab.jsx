import React, { useState, useRef, useEffect } from 'react';
import ChatMessage from './ChatMessage';
import ChatInput from './ChatInput';
import SuggestedChips from './SuggestedChips';
import LoadingDots from './LoadingDots';

const SUGGESTIONS = [
  'Qual é o SLA para tickets críticos (P1)?',
  'Como funciona o processo de escalação N1 para N2?',
  'Quais são os requisitos de segurança para reset de senha?',
  'Quais KPIs são usados para medir a qualidade do atendimento?',
  'O que acontece se o SLA for violado?',
  'Quais dados pessoais são protegidos pela LGPD no atendimento?',
];

export default function KnowledgeTab() {
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
      const resp = await fetch('/api/knowledge', {
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
            <div className="text-5xl mb-4">📚</div>
            <h2 className="text-lg font-semibold text-white mb-2">Base de Conhecimento IT</h2>
            <p className="text-sm text-db-muted mb-6 max-w-md">
              Consulte as normas e documentos de suporte de TI.
              Respostas baseadas nos documentos internos via RAG.
            </p>
            <SuggestedChips suggestions={SUGGESTIONS} onSelect={sendMessage} disabled={loading} />
          </div>
        )}

        {messages.map((msg, i) => (
          <ChatMessage key={i} role={msg.role} content={msg.content} />
        ))}

        {loading && <LoadingDots />}
      </div>

      {messages.length > 0 && !loading && (
        <SuggestedChips suggestions={SUGGESTIONS} onSelect={sendMessage} disabled={loading} />
      )}

      <ChatInput onSend={sendMessage} disabled={loading} placeholder="Pergunte sobre as normas de TI..." />
    </div>
  );
}
