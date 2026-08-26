import React, { useState, useRef, useEffect, useCallback } from 'react';
import ChatInput from './ChatInput';
import SuggestedChips from './SuggestedChips';

/**
 * Genie One interactive View — an MCP Apps host.
 *
 * We act as the "MCP Apps client" that the Genie MCP server offers `view_ask`
 * to. The `ui://genie/mcp-app.html` resource is a single-turn View, so — like
 * a chat host (Claude, ChatGPT) — we render ONE View per question and stack
 * them in a scroll, preserving the in-session history. All turns share the
 * same MCP session and Genie conversation, so context carries across turns.
 *
 * Auth is on-behalf-of the logged-in user (the app forwards the user token),
 * so conversations belong to that user and also appear in native Genie One —
 * we surface the deep link for full history + feedback.
 */

const UI_RESOURCE_URI = 'ui://genie/mcp-app.html';
const UI_EXTENSION = 'io.modelcontextprotocol/ui';

const SUGGESTIONS = [
  'Quantos chamados existem no total?',
  'Liste a quantidade de chamados por prioridade',
  'Quais os 5 tipos de chamado mais frequentes?',
  'Qual o tempo médio de resolução por prioridade?',
  'Quantos chamados violaram o SLA?',
];

const HOST_CAPABILITIES = {
  serverTools: { listChanged: true },
  serverResources: { listChanged: true },
  openLinks: {},
  logging: {},
};

/** One Genie One View instance (a single view_ask turn) in its own iframe. */
function ViewFrame({ html, question, viewAskResult, callServer, onFollowUp }) {
  const iframeRef = useRef(null);
  const [height, setHeight] = useState(360);

  const post = useCallback((msg) => {
    const win = iframeRef.current?.contentWindow;
    if (win) win.postMessage(msg, '*');
  }, []);

  const deliverResult = useCallback(() => {
    post({
      jsonrpc: '2.0', method: 'ui/notifications/tool-input',
      params: { arguments: { question } },
    });
    post({
      jsonrpc: '2.0', method: 'ui/notifications/tool-result',
      params: {
        content: viewAskResult.content || [],
        structuredContent: viewAskResult.structuredContent || {},
      },
    });
  }, [post, question, viewAskResult]);

  useEffect(() => {
    const handler = async (event) => {
      const win = iframeRef.current?.contentWindow;
      if (!win || event.source !== win) return; // only this frame's messages
      const msg = event.data;
      if (!msg || msg.jsonrpc !== '2.0' || !msg.method) return;

      const respond = (result) => post({ jsonrpc: '2.0', id: msg.id, result });
      const respondError = (message) =>
        post({ jsonrpc: '2.0', id: msg.id, error: { code: -32000, message } });

      try {
        switch (msg.method) {
          case 'ui/initialize':
            respond({
              protocolVersion: '2026-01-26',
              hostCapabilities: HOST_CAPABILITIES,
              hostInfo: { name: 'IT Support Workshop', version: '1.0' },
              hostContext: { theme: 'dark', displayMode: 'inline' },
            });
            break;

          case 'ui/notifications/initialized':
            deliverResult();
            break;

          case 'tools/call':
          case 'resources/read': {
            const reply = await callServer(msg);
            if (reply && (reply.result !== undefined || reply.error !== undefined)) post(reply);
            else respond({});
            break;
          }

          case 'ui/message': {
            respond({});
            const c = msg.params?.content;
            const text = typeof c === 'string'
              ? c
              : (Array.isArray(c) ? c.map((x) => x.text || '').join(' ').trim() : (msg.params?.text || ''));
            if (text && onFollowUp) onFollowUp(text);
            break;
          }

          case 'ui/open-link':
            if (msg.params?.url) window.open(msg.params.url, '_blank', 'noopener');
            respond({});
            break;

          case 'ui/request-display-mode':
            respond({ mode: msg.params?.mode || 'inline' });
            break;

          case 'ui/update-model-context':
            respond({});
            break;

          case 'ping':
            respond({});
            break;

          case 'ui/notifications/size-changed': {
            const h = msg.params?.height ?? msg.params?.size?.height;
            if (typeof h === 'number' && h > 0) setHeight(Math.max(180, Math.ceil(h)));
            break;
          }

          case 'notifications/message':
            break;

          default:
            if (msg.id !== undefined) respondError(`Método não suportado: ${msg.method}`);
        }
      } catch (e) {
        if (msg.id !== undefined) respondError(e.message || String(e));
      }
    };

    window.addEventListener('message', handler);
    return () => window.removeEventListener('message', handler);
  }, [callServer, post, deliverResult, onFollowUp]);

  return (
    <iframe
      ref={iframeRef}
      title="Genie One View"
      srcDoc={html}
      style={{ height }}
      className="w-full border border-db-primary/20 rounded-lg bg-white"
      sandbox="allow-scripts allow-same-origin allow-popups allow-forms allow-downloads"
    />
  );
}

function fmtDate(ts) {
  if (!ts) return '';
  try {
    return new Date(ts).toLocaleString('pt-BR', {
      day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit',
    });
  } catch { return ''; }
}

/** Build a synthetic view_ask result so the View re-renders a past response
 *  (it polls view_poll_response with these ids through the host bridge). */
function replayResult(conversationId, responseId) {
  const sc = { conversation_id: conversationId, response_id: responseId, status: 'in_progress' };
  return { content: [{ type: 'text', text: JSON.stringify(sc) }], structuredContent: sc };
}

export default function GenieOneTab() {
  // turns: {id, mode: 'view'|'history', question, viewAskResult?, text?, sql?}
  const [turns, setTurns] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [conversations, setConversations] = useState([]);
  const [activeConvId, setActiveConvId] = useState(null);
  const [historyOpen, setHistoryOpen] = useState(true);

  const sessionIdRef = useRef(null);
  const convIdRef = useRef(null);
  const htmlRef = useRef(null);
  const turnSeq = useRef(0);
  const scrollRef = useRef(null);

  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [turns, loading]);

  // Durable, per-user history persisted server-side (UC table, keyed by the
  // logged-in user's email). The native Genie One thread store has no public
  // list API, so we track the conversations WE start via view_ask and reopen
  // them in the interactive View. Survives reloads, incognito and devices.
  const loadHistory = useCallback(async () => {
    try {
      const resp = await fetch('/api/genie-mcp/history');
      if (!resp.ok) return;
      const data = await resp.json();
      setConversations(data.conversations || []);
    } catch { /* ignore */ }
  }, []);

  const saveTurn = useCallback(async (conversationId, question, responseId, title) => {
    try {
      await fetch('/api/genie-mcp/history', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ conversation_id: conversationId, response_id: responseId, question, title }),
      });
    } catch { /* ignore */ }
    loadHistory();
  }, [loadHistory]);

  useEffect(() => { loadHistory(); }, [loadHistory]);

  const callServer = useCallback(async (body) => {
    const resp = await fetch('/api/genie-mcp/rpc', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionIdRef.current, body }),
    });
    if (!resp.ok) throw new Error(`Relay ${resp.status}: ${await resp.text()}`);
    const data = await resp.json();
    if (data.session_id) sessionIdRef.current = data.session_id;
    return data.body;
  }, []);

  const ensureSession = useCallback(async () => {
    if (sessionIdRef.current) return;
    await callServer({
      jsonrpc: '2.0', id: 1, method: 'initialize',
      params: {
        protocolVersion: '2025-06-18',
        capabilities: { extensions: { [UI_EXTENSION]: { mimeTypes: ['text/html;profile=mcp-app'] } } },
        clientInfo: { name: 'it-support-workshop', version: '1.0' },
      },
    });
    // fire-and-forget initialized notification
    fetch('/api/genie-mcp/rpc', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionIdRef.current, body: { jsonrpc: '2.0', method: 'notifications/initialized' } }),
    }).catch(() => {});
  }, [callServer]);

  const loadResource = useCallback(async () => {
    if (htmlRef.current) return htmlRef.current;
    const res = await callServer({
      jsonrpc: '2.0', id: 2, method: 'resources/read', params: { uri: UI_RESOURCE_URI },
    });
    const html = (res?.result?.contents || []).find((c) => (c.text || '').length)?.text;
    if (!html) throw new Error('Recurso da View do Genie não retornou HTML.');
    htmlRef.current = html;
    return html;
  }, [callServer]);

  const runViewAsk = useCallback(async (question) => {
    const resp = await callServer({
      jsonrpc: '2.0', id: 10, method: 'tools/call',
      params: {
        name: 'view_ask',
        arguments: { question, ...(convIdRef.current ? { conversation_id: convIdRef.current } : {}) },
      },
    });
    const result = resp?.result || {};
    const sc = result.structuredContent || {};
    if (sc.conversation_id) convIdRef.current = sc.conversation_id;
    return { result, responseId: sc.response_id || null };
  }, [callServer]);

  const ask = useCallback(async (question) => {
    setError(null);
    setLoading(true);
    try {
      await ensureSession();
      await loadResource();
      const { result, responseId } = await runViewAsk(question);
      turnSeq.current += 1;
      setTurns((prev) => [...prev, { id: turnSeq.current, question, viewAskResult: result }]);
      const convId = convIdRef.current;
      setActiveConvId(convId);
      if (convId && responseId) saveTurn(convId, question, responseId);
    } catch (e) {
      setError(e.message || String(e));
    } finally {
      setLoading(false);
    }
  }, [ensureSession, loadResource, runViewAsk, saveTurn]);

  const openConversation = useCallback(async (conv) => {
    setError(null);
    setLoading(true);
    try {
      await ensureSession();
      await loadResource();
      const items = (conv.turns || []).map((t) => {
        turnSeq.current += 1;
        return {
          id: turnSeq.current,
          question: t.question,
          viewAskResult: replayResult(conv.conversationId, t.responseId),
        };
      });
      setTurns(items);
      convIdRef.current = conv.conversationId; // follow-ups continue this thread
      setActiveConvId(conv.conversationId);
    } catch (e) {
      setError(e.message || String(e));
    } finally {
      setLoading(false);
    }
  }, [ensureSession, loadResource]);

  const reset = () => {
    convIdRef.current = null;
    turnSeq.current = 0;
    setTurns([]);
    setActiveConvId(null);
    setError(null);
    setLoading(false);
  };

  return (
    <div className="h-full flex min-w-0">
      {/* History sidebar */}
      {historyOpen && (
        <aside className="w-60 shrink-0 border-r border-db-border/40 flex flex-col bg-db-sidebar/40">
          <div className="px-3 py-3 flex items-center justify-between border-b border-db-border/40">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-db-muted">Histórico</span>
            <button
              onClick={reset}
              className="text-[11px] text-db-accent hover:underline"
              title="Iniciar nova conversa"
            >
              + Nova
            </button>
          </div>
          <div className="flex-1 overflow-y-auto py-2">
            {conversations.length === 0 && (
              <p className="px-3 text-[11px] text-db-muted/70">Nenhuma conversa ainda.</p>
            )}
            {conversations.map((c) => {
              const active = c.conversationId === activeConvId;
              return (
                <button
                  key={c.conversationId}
                  onClick={() => openConversation(c)}
                  disabled={loading}
                  className={`w-full text-left px-3 py-2 transition-colors disabled:opacity-50
                    ${active ? 'bg-db-surface' : 'hover:bg-db-surface/40'}`}
                >
                  <p className="text-xs text-db-light truncate">{c.title}</p>
                  <p className="text-[10px] text-db-muted/70">{fmtDate(c.ts)}</p>
                </button>
              );
            })}
          </div>
        </aside>
      )}

      {/* Main chat */}
      <div className="flex-1 flex flex-col min-w-0">
        <div className="px-3 pt-2">
          <button
            onClick={() => setHistoryOpen((v) => !v)}
            className="text-[11px] text-db-muted hover:text-db-accent transition-colors"
          >
            {historyOpen ? '‹ Ocultar histórico' : '› Mostrar histórico'}
          </button>
        </div>

        <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 space-y-4">
          {turns.length === 0 && !loading && (
            <div className="flex flex-col items-center justify-center h-full text-center">
              <div className="text-5xl mb-4">🧞</div>
              <h2 className="text-lg font-semibold text-white mb-2">Genie One · Sala Chamados IT</h2>
              <p className="text-sm text-db-muted mb-6 max-w-md">
                A experiência interativa do <strong className="text-db-light">Genie One</strong> via
                MCP (<code className="text-db-accent">view_ask</code>): progresso, visualizações e
                resposta final renderizados no app. Suas conversas ficam no histórico ao lado.
              </p>
              <SuggestedChips suggestions={SUGGESTIONS} onSelect={ask} disabled={loading} />
            </div>
          )}

          {turns.map((t) => (
            <div key={t.id} className="space-y-2">
              <div className="flex justify-end">
                <div className="max-w-[85%] rounded-2xl rounded-br-md px-4 py-2.5 bg-db-primary text-white">
                  <p className="text-sm leading-relaxed">{t.question}</p>
                </div>
              </div>
              <ViewFrame
                html={htmlRef.current}
                question={t.question}
                viewAskResult={t.viewAskResult}
                callServer={callServer}
                onFollowUp={ask}
              />
            </div>
          ))}

          {loading && <div className="text-db-muted text-sm px-1">Genie One está pensando…</div>}

          {error && (
            <div className="text-sm text-red-300 break-words px-1">
              Erro: {error}{' '}
              <button onClick={reset} className="text-db-accent hover:underline ml-1">recomeçar</button>
            </div>
          )}
        </div>

        {turns.length > 0 && (
          <div className="px-4 pt-1">
            <SuggestedChips suggestions={SUGGESTIONS} onSelect={ask} disabled={loading} />
          </div>
        )}

        <ChatInput onSend={ask} disabled={loading} placeholder="Pergunte ao Genie One sobre os chamados de TI..." />
      </div>
    </div>
  );
}
