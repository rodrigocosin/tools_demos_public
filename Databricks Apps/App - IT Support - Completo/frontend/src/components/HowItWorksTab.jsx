import React, { useState } from 'react';

/**
 * "Como Funciona" — documentação técnica de como cada aba/solução se conecta.
 * Accordion: cada solução colapsa/expande de forma independente, para focar
 * apenas na que interessa.
 */

// --- Presentational helpers ---
const Code = ({ children }) => (
  <code className="px-1.5 py-0.5 rounded bg-db-darker text-db-accent text-[12px] break-all">{children}</code>
);

const Field = ({ label, children }) => (
  <div className="flex flex-col gap-1">
    <span className="text-[10px] font-semibold uppercase tracking-wider text-db-muted">{label}</span>
    <div className="text-sm text-db-light">{children}</div>
  </div>
);

const Section = ({ title, children }) => (
  <div className="mt-4">
    <h4 className="text-[11px] font-semibold uppercase tracking-wider text-db-muted mb-2">{title}</h4>
    {children}
  </div>
);

const Bullets = ({ items }) => (
  <ul className="space-y-1.5">
    {items.map((it, i) => (
      <li key={i} className="text-sm text-db-light/90 flex gap-2">
        <span className="text-db-accent mt-0.5 shrink-0">›</span>
        <span>{it}</span>
      </li>
    ))}
  </ul>
);

const Badge = ({ children, color }) => (
  <span
    className="text-[10px] font-semibold px-2 py-0.5 rounded-full border"
    style={{ color, borderColor: `${color}55`, background: `${color}18` }}
  >
    {children}
  </span>
);

// --- Content per solution ---
const SOLUTIONS = [
  {
    id: 'dashboard',
    title: 'Dashboard',
    subtitle: 'AI/BI (Lakeview) embutido',
    color: '#FF3621',
    auth: 'Sessão do usuário (cookie SSO)',
    kind: 'Embed (iframe) · sem backend',
    body: (
      <>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <Field label="Tipo">Embed via <Code>&lt;iframe&gt;</Code>, sem backend</Field>
          <Field label="Autenticação">Cookie SSO do Databricks — roda como o usuário logado</Field>
          <Field label="URL"><Code>/embed/dashboardsv3/01f124531fa91f9b9039abc401106002</Code></Field>
          <Field label="Arquivo"><Code>frontend/src/components/DashboardTab.jsx</Code></Field>
        </div>
        <Section title="Como conecta">
          <Bullets items={[
            <>A rota <Code>/embed/dashboardsv3/&lt;id&gt;</Code> tem <Code>frame-ancestors *</Code>, então pode ser embutida em qualquer domínio (inclusive o do app).</>,
            'O navegador do usuário carrega o iframe usando a sessão/cookie do Databricks — não passa pelo backend do app.',
            'Portanto o dashboard é renderizado pela própria Databricks, com os dados e permissões do usuário logado.',
          ]} />
        </Section>
      </>
    ),
  },
  {
    id: 'genie',
    title: 'Genie · Dados',
    subtitle: 'Sala Genie clássica embutida',
    color: '#22c55e',
    auth: 'Sessão do usuário (cookie SSO)',
    kind: 'Embed (iframe) · sem backend',
    body: (
      <>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <Field label="Tipo">Embed via <Code>&lt;iframe&gt;</Code>, sem backend</Field>
          <Field label="Autenticação">Cookie SSO — roda como o usuário logado</Field>
          <Field label="Genie Space">"Sala Chamados IT" · <Code>01f124528653102d8b5ea6443c331153</Code></Field>
          <Field label="URL"><Code>/embed/genie/rooms/&lt;space_id&gt;</Code></Field>
        </div>
        <Section title="Como conecta">
          <Bullets items={[
            <>Rota de embed com <Code>frame-ancestors *</Code> → embutível no domínio do app.</>,
            'É a experiência clássica da sala Genie: histórico e feedback nativos aparecem dentro do próprio iframe.',
            <>Arquivo: <Code>frontend/src/components/GenieTab.jsx</Code>.</>,
          ]} />
        </Section>
      </>
    ),
  },
  {
    id: 'genieone',
    title: 'Genie One · MCP',
    subtitle: 'Genie One agêntico via MCP (host MCP Apps)',
    color: '#a855f7',
    auth: 'On-behalf-of-user (OBO) · escopos genie + sql',
    kind: 'Host MCP Apps · backend relay + bridge no navegador',
    body: (
      <>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <Field label="Endpoint MCP"><Code>POST /api/2.0/mcp/genie</Code> (server <Code>genie_chat</Code>)</Field>
          <Field label="Protocolo">MCP · JSON-RPC 2.0 sobre HTTP streamable · sessão em <Code>mcp-session-id</Code></Field>
          <Field label="Autenticação">OBO: token do usuário via header <Code>x-forwarded-access-token</Code> (User authorization com escopos <Code>genie</Code> + <Code>sql</Code>) — roda como o usuário logado</Field>
          <Field label="Arquivos"><Code>GenieOneTab.jsx</Code>, <Code>server/genie_mcp.py</Code>, <Code>server/history.py</Code></Field>
        </div>
        <Section title="Destravando o view_ask (MCP Apps)">
          <Bullets items={[
            <>No <Code>initialize</Code>, o cliente declara a capability <Code>capabilities.extensions."io.modelcontextprotocol/ui"</Code>. Isso faz o servidor expor as tools <Code>view_ask</Code>, <Code>view_poll_response</Code>, <Code>view_fetch_query_results</Code>.</>,
            <>A tool <Code>view_ask</Code> aponta para um recurso de UI: <Code>ui://genie/mcp-app.html</Code> (HTML self-contained da Databricks).</>,
          ]} />
        </Section>
        <Section title="Fluxo (host MCP Apps)">
          <Bullets items={[
            <>1. Backend abre sessão MCP e chama <Code>view_ask</Code> (a tool é <em>model-visibility</em>, iniciada pelo host).</>,
            <>2. Lê o recurso <Code>ui://genie/mcp-app.html</Code> e renderiza num <Code>&lt;iframe sandbox&gt;</Code>.</>,
            <>3. Ponte <Code>postMessage</Code> (JSON-RPC): o iframe manda <Code>ui/initialize</Code> → o host responde com <Code>hostCapabilities.serverTools/serverResources</Code> → o host envia <Code>ui/notifications/tool-result</Code>.</>,
            <>4. O iframe chama <Code>tools/call</Code> (<Code>view_poll_response</Code>) e <Code>resources/read</Code> de volta; o host encaminha ao MCP na mesma sessão.</>,
            <>5. Relay do backend: <Code>POST /api/genie-mcp/rpc</Code> repassa cada mensagem JSON-RPC ao Genie One com o token OBO + <Code>mcp-session-id</Code>.</>,
          ]} />
        </Section>
        <Section title="Histórico durável">
          <Bullets items={[
            <>O Genie One nativo não tem API pública para listar threads — então o app guarda as conversas que ele cria.</>,
            <>Tabela UC <Code>cosin_aws_serverless_catalog.it_support.genie_one_history</Code>, indexada pelo e-mail do usuário (<Code>x-forwarded-email</Code>), via SQL Statement Execution API.</>,
            <>Reabrir uma conversa re-renderiza cada resposta chamando <Code>view_poll_response</Code> (=<Code>genie_poll_response</Code>) pelo <Code>conversation_id</Code> + <Code>response_id</Code> guardados.</>,
          ]} />
        </Section>
      </>
    ),
  },
  {
    id: 'knowledge',
    title: 'Base de Conhecimento',
    subtitle: 'Knowledge Agent (RAG) via serving endpoint',
    color: '#3b82f6',
    auth: 'Service principal (M2M OAuth2)',
    kind: 'Backend → Model Serving endpoint',
    body: (
      <>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <Field label="Endpoint"><Code>POST /serving-endpoints/ka-1a0b7165-endpoint/invocations</Code></Field>
          <Field label="Resource (app.yaml)"><Code>ka-it-support</Code> · permissão <Code>CAN_QUERY</Code></Field>
          <Field label="Autenticação">Service principal do app (client_credentials, escopo <Code>all-apis</Code>)</Field>
          <Field label="Rotas"><Code>/api/knowledge</Code> e <Code>/api/knowledge/stream</Code></Field>
        </div>
        <Section title="Como conecta">
          <Bullets items={[
            <>Payload no formato Agent Framework: <Code>{'{ input: [{ role: "user", content }] }'}</Code>.</>,
            <>A resposta traz o texto em <Code>output[].content[].text</Code> e as fontes em <Code>annotations</Code> do tipo <Code>url_citation</Code> (título + página).</>,
            'Robustez: tenta até 4x com backoff até obter uma resposta com fontes (tolera 429 do retrieval interno).',
            <>Arquivos: <Code>KnowledgeTab.jsx</Code>, <Code>server/knowledge.py</Code>.</>,
          ]} />
        </Section>
      </>
    ),
  },
  {
    id: 'supervisor',
    title: 'Agente Supervisor',
    subtitle: 'Multi-Agent Supervisor (Genie + Conhecimento)',
    color: '#f59e0b',
    auth: 'Service principal (M2M OAuth2)',
    kind: 'Backend → Model Serving endpoint',
    body: (
      <>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <Field label="Endpoint"><Code>POST /serving-endpoints/mas-3754ad3f-endpoint/invocations</Code></Field>
          <Field label="Resource (app.yaml)"><Code>mas-supervisor</Code> · permissão <Code>CAN_QUERY</Code></Field>
          <Field label="Autenticação">Service principal do app</Field>
          <Field label="Rota"><Code>/api/supervisor</Code></Field>
        </div>
        <Section title="Como conecta">
          <Bullets items={[
            'Orquestra dois agentes: Genie (dados estruturados) + Knowledge Agent (normas/documentos).',
            <>Payload <Code>{'{ input: [{ role: "user", content }] }'}</Code>; a resposta final é a última mensagem <Code>assistant</Code>.</>,
            <>O parser ignora marcadores internos de roteamento (<Code>&lt;name&gt;...&lt;/name&gt;</Code>) e retorna só a resposta final.</>,
            <>Arquivos: <Code>SupervisorTab.jsx</Code>, <Code>server/supervisor.py</Code>.</>,
          ]} />
        </Section>
      </>
    ),
  },
];

// --- Architecture diagram ---
const AUTH = {
  cookie: { label: 'Sessão / cookie', color: '#14b8a6' },
  obo: { label: 'OBO (token do usuário)', color: '#a855f7' },
  sp: { label: 'Service principal', color: '#3b82f6' },
};

function Node({ title, sub, color }) {
  return (
    <div className="rounded-lg border px-3 py-2 bg-db-darker/60"
      style={{ borderColor: color ? `${color}55` : 'rgba(120,120,140,0.3)' }}>
      <div className="text-[12px] font-semibold text-db-light leading-tight">{title}</div>
      {sub && <div className="text-[10px] text-db-muted mt-0.5 leading-tight">{sub}</div>}
    </div>
  );
}

function Layer({ label, children }) {
  return (
    <div className="w-full rounded-xl border border-db-border/50 bg-db-surface/30 p-3">
      <div className="text-[10px] font-semibold uppercase tracking-wider text-db-muted mb-2">{label}</div>
      {children}
    </div>
  );
}

function Down({ label }) {
  return (
    <div className="flex flex-col items-center text-db-muted py-1">
      {label && <span className="text-[10px]">{label}</span>}
      <span className="text-lg leading-none">↓</span>
    </div>
  );
}

function ArchitectureDiagram() {
  return (
    <div>
      {/* Diagram */}
      <Layer label="1 · Usuário">
        <Node title="Navegador do usuário" sub="Autenticado pelo SSO do Databricks Apps" />
      </Layer>
      <Down label="HTTPS · sessão autenticada" />

      <Layer label="2 · Databricks App — it-support-workshop (roda como o SP app-mivm82)">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div className="space-y-2">
            <div className="text-[10px] text-db-muted">Frontend · React (Vite + Tailwind), servido estático</div>
            <Node title="SPA — abas" sub="Dashboard · Genie · Genie One · Conhecimento · Supervisor · Como Funciona" />
          </div>
          <div className="space-y-2">
            <div className="text-[10px] text-db-muted">Backend · FastAPI (app.py + server/*.py)</div>
            <Node title="Rotas /api/*" sub="genie · genie-mcp · genie-mcp/rpc · genie-mcp/history · knowledge(+stream) · supervisor · whoami · health" />
          </div>
        </div>
      </Layer>
      <Down label="3 modos de autenticação (veja a legenda)" />

      <Layer label="3 · Plataforma Databricks">
        <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
          <Node title="AI/BI Dashboard" sub="dashboardsv3 · embed" color={AUTH.cookie.color} />
          <Node title="Genie Space (clássico)" sub="Sala Chamados IT · embed" color={AUTH.cookie.color} />
          <Node title="Genie One MCP" sub="/api/2.0/mcp/genie · view_ask" color={AUTH.obo.color} />
          <Node title="KA Serving endpoint" sub="ka-1a0b7165-endpoint (RAG)" color={AUTH.sp.color} />
          <Node title="MAS Serving endpoint" sub="mas-3754ad3f-endpoint" color={AUTH.sp.color} />
          <Node title="SQL Warehouse" sub="0c2def7684630e5e" color={AUTH.obo.color} />
          <Node title="UC · tickets_clean" sub="it_support (dados dos chamados)" />
          <Node title="UC · genie_one_history" sub="it_support (histórico por usuário)" color={AUTH.sp.color} />
        </div>
      </Layer>

      {/* Auth legend */}
      <div className="mt-3 flex flex-wrap gap-3">
        {Object.values(AUTH).map((a) => (
          <span key={a.label} className="flex items-center gap-1.5 text-[11px] text-db-light">
            <span className="w-3 h-3 rounded-sm" style={{ background: `${a.color}33`, border: `1px solid ${a.color}` }} />
            {a.label}
          </span>
        ))}
      </div>

      {/* Mapping table */}
      <Section title="Aba → autenticação → destino">
        <div className="overflow-x-auto rounded-lg border border-db-border/40">
          <table className="w-full text-[12px]">
            <thead>
              <tr className="bg-db-darker/60 text-db-muted">
                <th className="text-left font-semibold px-3 py-2">Aba</th>
                <th className="text-left font-semibold px-3 py-2">Como conecta</th>
                <th className="text-left font-semibold px-3 py-2">Auth</th>
                <th className="text-left font-semibold px-3 py-2">Destino Databricks</th>
              </tr>
            </thead>
            <tbody className="text-db-light/90">
              {[
                ['Dashboard', 'iframe embed', AUTH.cookie, 'AI/BI dashboard'],
                ['Genie · Dados', 'iframe embed', AUTH.cookie, 'Genie Space (sala clássica)'],
                ['Genie One · MCP', 'backend relay + bridge', AUTH.obo, 'Genie One MCP + Warehouse + UC history'],
                ['Base de Conhecimento', 'backend → invocations', AUTH.sp, 'KA serving endpoint'],
                ['Agente Supervisor', 'backend → invocations', AUTH.sp, 'MAS endpoint (→ Genie + KA)'],
              ].map((r, i) => (
                <tr key={i} className={i % 2 ? 'bg-db-surface/20' : ''}>
                  <td className="px-3 py-2 whitespace-nowrap font-medium">{r[0]}</td>
                  <td className="px-3 py-2 whitespace-nowrap">{r[1]}</td>
                  <td className="px-3 py-2 whitespace-nowrap">
                    <span className="inline-flex items-center gap-1.5">
                      <span className="w-2.5 h-2.5 rounded-sm" style={{ background: `${r[2].color}33`, border: `1px solid ${r[2].color}` }} />
                      {r[2].label}
                    </span>
                  </td>
                  <td className="px-3 py-2">{r[3]}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Section>

      <Section title="Persistência · histórico de conversas do Genie One">
        <Bullets items={[
          <>Há uma tabela no Unity Catalog — <Code>cosin_aws_serverless_catalog.it_support.genie_one_history</Code> — que <strong className="text-db-light">guarda o histórico de conversas do Genie One</strong> criadas pelo app.</>,
          <>Cada pergunta grava uma linha com <Code>user_email</Code>, <Code>conversation_id</Code>, <Code>question</Code>, <Code>response_id</Code> e <Code>turn_ts</Code>, indexada pelo e-mail do usuário logado (<Code>x-forwarded-email</Code>).</>,
          <>É necessária porque o Genie One nativo não expõe API pública para listar as threads. Assim o histórico fica <strong className="text-db-light">durável e por usuário</strong> (sobrevive a reload, guia anônima e outros dispositivos), diferente de armazenar no navegador.</>,
          <>Leitura/escrita via SQL Statement Execution API no SQL Warehouse; reabrir uma conversa re-renderiza cada resposta com <Code>view_poll_response</Code> usando o <Code>conversation_id</Code>+<Code>response_id</Code> guardados.</>,
        ]} />
      </Section>

      <Section title="Deploy & execução">
        <Bullets items={[
          <>Empacotado como <strong className="text-db-light">Databricks App</strong> (nome <Code>it-support-workshop</Code>); o backend FastAPI também serve o build do frontend (<Code>frontend/dist</Code>).</>,
          <>O app roda como o <strong className="text-db-light">service principal</strong> <Code>app-mivm82</Code>; os recursos (Genie Space, endpoints KA/MAS) são concedidos via <Code>app.yaml</Code>.</>,
          <>Para o Genie One, a <strong className="text-db-light">User authorization</strong> está habilitada (escopos <Code>genie</Code> + <Code>sql</Code>), permitindo o encaminhamento do token do usuário (OBO).</>,
          <>Dados dos chamados em <Code>cosin_aws_serverless_catalog.it_support.tickets_clean</Code>, consultados via SQL Warehouse.</>,
        ]} />
      </Section>
    </div>
  );
}

function ChevronIcon({ open }) {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
      strokeLinecap="round" strokeLinejoin="round"
      className={`transition-transform ${open ? 'rotate-90' : ''}`}>
      <polyline points="9 6 15 12 9 18" />
    </svg>
  );
}

export default function HowItWorksTab() {
  const [open, setOpen] = useState(() => new Set());
  const allIds = ['arch', ...SOLUTIONS.map((s) => s.id), 'auth'];

  const toggle = (id) => {
    setOpen((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  };

  return (
    <div className="h-full overflow-y-auto p-4 sm:p-6">
      <div className="max-w-3xl mx-auto">
        <div className="mb-5">
          <h2 className="text-lg font-semibold text-white">Como cada solução se conecta</h2>
          <p className="text-sm text-db-muted mt-1">
            Detalhes técnicos de integração de cada aba. Clique num item para expandir apenas o que interessa.
          </p>
          <div className="mt-3 flex gap-2">
            <button onClick={() => setOpen(new Set(allIds))}
              className="text-xs text-db-muted hover:text-db-accent transition-colors">Expandir tudo</button>
            <span className="text-db-muted/40">·</span>
            <button onClick={() => setOpen(new Set())}
              className="text-xs text-db-muted hover:text-db-accent transition-colors">Recolher tudo</button>
          </div>
        </div>

        <div className="space-y-3">
          {/* Architecture overview */}
          <div
            className="rounded-xl border border-db-border/50 bg-db-surface/40 overflow-hidden"
            style={{ borderLeft: '3px solid #cbd5e1' }}
          >
            <button
              onClick={() => toggle('arch')}
              className="w-full flex items-center gap-3 px-4 py-3.5 text-left hover:bg-db-surface/60 transition-colors"
            >
              <span style={{ color: '#cbd5e1' }}><ChevronIcon open={open.has('arch')} /></span>
              <span className="flex-1 min-w-0">
                <span className="text-sm font-semibold text-white">Arquitetura geral do app</span>
                <span className="block text-[12px] text-db-muted mt-0.5">Camadas, recursos Databricks e fluxos de autenticação</span>
              </span>
            </button>
            {open.has('arch') && (
              <div className="px-4 pb-4 pt-3 border-t border-db-border/30">
                <ArchitectureDiagram />
              </div>
            )}
          </div>

          {SOLUTIONS.map((s) => {
            const isOpen = open.has(s.id);
            return (
              <div
                key={s.id}
                className="rounded-xl border border-db-border/50 bg-db-surface/40 overflow-hidden"
                style={{ borderLeft: `3px solid ${s.color}` }}
              >
                <button
                  onClick={() => toggle(s.id)}
                  className="w-full flex items-center gap-3 px-4 py-3.5 text-left hover:bg-db-surface/60 transition-colors"
                >
                  <span style={{ color: s.color }}><ChevronIcon open={isOpen} /></span>
                  <span className="flex-1 min-w-0">
                    <span className="flex items-center gap-2 flex-wrap">
                      <span className="text-sm font-semibold text-white">{s.title}</span>
                      <Badge color={s.color}>{s.auth}</Badge>
                    </span>
                    <span className="block text-[12px] text-db-muted mt-0.5">{s.subtitle} · {s.kind}</span>
                  </span>
                </button>
                {isOpen && (
                  <div className="px-4 pb-4 pt-1 border-t border-db-border/30">
                    {s.body}
                  </div>
                )}
              </div>
            );
          })}

          {/* Auth model (collapsible) */}
          <div
            className="rounded-xl border border-db-border/50 bg-db-surface/40 overflow-hidden"
            style={{ borderLeft: '3px solid #cbd5e1' }}
          >
            <button
              onClick={() => toggle('auth')}
              className="w-full flex items-center gap-3 px-4 py-3.5 text-left hover:bg-db-surface/60 transition-colors"
            >
              <span style={{ color: '#cbd5e1' }}><ChevronIcon open={open.has('auth')} /></span>
              <span className="flex-1 min-w-0">
                <span className="text-sm font-semibold text-white">Modelo de autenticação (resumo)</span>
                <span className="block text-[12px] text-db-muted mt-0.5">SP, OBO e sessão/cookie - e onde cada um é usado</span>
              </span>
            </button>
            {open.has('auth') && (
              <div className="px-4 pb-4 pt-3 border-t border-db-border/30">
                <Bullets items={[
                  <><strong className="text-db-light">Service principal (SP)</strong>: usado hoje por Base de Conhecimento e Agente Supervisor. O app obtém um token M2M (OAuth2 client_credentials, escopo all-apis) a partir de <Code>DATABRICKS_CLIENT_ID/SECRET</Code> injetados pelo Databricks Apps.</>,
                  <><strong className="text-db-light">On-behalf-of-user (OBO)</strong>: usado pelo Genie One (obrigatório - o MCP não aceita SP). O app encaminha o token do usuário logado (<Code>x-forwarded-access-token</Code>) com os escopos <Code>genie</Code> + <Code>sql</Code>; as consultas rodam com a identidade do usuário.</>,
                  <><strong className="text-db-light">Sessão/cookie</strong>: usado pelos embeds (Dashboard e Genie · Dados); o iframe usa a sessão do Databricks direto no navegador.</>,
                ]} />
                <div className="mt-3 rounded-lg border border-db-primary/30 bg-db-primary/10 p-3">
                  <p className="text-[11px] font-semibold uppercase tracking-wider text-db-accent mb-1.5">Poderia ser OBO também</p>
                  <Bullets items={[
                    <>Base de Conhecimento e Agente Supervisor <strong className="text-db-light">poderiam usar OBO</strong> em vez de SP: os endpoints de Model Serving aceitam o token do usuário. Bastaria adicionar o escopo <Code>model-serving</Code> na User authorization e encaminhar o <Code>x-forwarded-access-token</Code> (com fallback para SP).</>,
                    <>Benefício: a chamada passa a ser feita e <strong className="text-db-light">auditada como o usuário</strong>, e só quem tem <Code>CAN_QUERY</Code> nos endpoints consegue usar (least-privilege).</>,
                    <>Custo: cada usuário (ou grupo) precisa de <Code>CAN_QUERY</Code> nos endpoints. E o acesso interno do agente aos dados normalmente continua com a identidade do próprio endpoint, não do usuário.</>,
                  ]} />
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
