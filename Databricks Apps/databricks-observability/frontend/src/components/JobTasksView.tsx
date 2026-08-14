import React, { useState, useEffect, useRef } from 'react';

interface TaskDef {
  task_key: string;
  task_type: string;
  depends_on: string[];
  description?: string;
}

interface JobDef {
  job_id: number;
  name: string;
  creator_user_name?: string;
  tasks: TaskDef[];
}

// Layout constants
const NODE_W = 170;
const NODE_H = 52;
const COL_GAP = 80;
const ROW_GAP = 16;
const COL_STRIDE = NODE_W + COL_GAP;
const ROW_STRIDE = NODE_H + ROW_GAP;
const PAD = 16;

const TASK_TYPE_BG: Record<string, { bg: string; border: string; text: string; dot: string }> = {
  notebook:      { bg: '#eef2ff', border: '#a5b4fc', text: '#4338ca', dot: '#6366f1' },
  spark_jar:     { bg: '#fff7ed', border: '#fdba74', text: '#c2410c', dot: '#f97316' },
  spark_python:  { bg: '#eff6ff', border: '#93c5fd', text: '#1d4ed8', dot: '#3b82f6' },
  python_wheel:  { bg: '#ecfeff', border: '#67e8f9', text: '#0e7490', dot: '#06b6d4' },
  dbt:           { bg: '#f0fdf4', border: '#86efac', text: '#15803d', dot: '#22c55e' },
  sql:           { bg: '#faf5ff', border: '#d8b4fe', text: '#7e22ce', dot: '#a855f7' },
  pipeline:      { bg: '#fefce8', border: '#fde047', text: '#a16207', dot: '#eab308' },
  run_job:       { bg: '#fdf4ff', border: '#f0abfc', text: '#a21caf', dot: '#d946ef' },
  spark_submit:  { bg: '#f8fafc', border: '#cbd5e1', text: '#475569', dot: '#94a3b8' },
  unknown:       { bg: '#f9fafb', border: '#d1d5db', text: '#6b7280', dot: '#9ca3af' },
};

/** Compute column (level) for each task via topological sort */
function computePositions(tasks: TaskDef[]): Map<string, { col: number; row: number }> {
  const levels = new Map<string, number>();

  function getLevel(key: string, stack = new Set<string>()): number {
    if (levels.has(key)) return levels.get(key)!;
    if (stack.has(key)) return 0;
    stack.add(key);
    const task = tasks.find(t => t.task_key === key);
    if (!task || task.depends_on.length === 0) { levels.set(key, 0); return 0; }
    const max = Math.max(...task.depends_on.map(d => getLevel(d, new Set(stack))));
    levels.set(key, max + 1);
    return max + 1;
  }

  tasks.forEach(t => getLevel(t.task_key));

  // Group tasks by level, preserve original order within each column
  const cols = new Map<number, string[]>();
  tasks.forEach(t => {
    const c = levels.get(t.task_key) ?? 0;
    if (!cols.has(c)) cols.set(c, []);
    cols.get(c)!.push(t.task_key);
  });

  const pos = new Map<string, { col: number; row: number }>();
  cols.forEach((keys, col) => keys.forEach((key, row) => pos.set(key, { col, row })));
  return pos;
}

function TaskGraph({ tasks }: { tasks: TaskDef[] }) {
  const positions = computePositions(tasks);

  const maxCol = Math.max(...Array.from(positions.values()).map(p => p.col));
  const maxRow = Math.max(...Array.from(positions.values()).map(p => p.row));

  const svgW = PAD + (maxCol + 1) * COL_STRIDE - COL_GAP + PAD;
  const svgH = PAD + (maxRow + 1) * ROW_STRIDE - ROW_GAP + PAD;

  // Build edges
  const edges: { x1: number; y1: number; x2: number; y2: number }[] = [];
  tasks.forEach(task => {
    const to = positions.get(task.task_key);
    if (!to) return;
    const tx = PAD + to.col * COL_STRIDE + NODE_W / 2;
    const ty = PAD + to.row * ROW_STRIDE + NODE_H / 2;
    task.depends_on.forEach(dep => {
      const from = positions.get(dep);
      if (!from) return;
      const fx = PAD + from.col * COL_STRIDE + NODE_W;
      const fy = PAD + from.row * ROW_STRIDE + NODE_H / 2;
      edges.push({ x1: fx, y1: fy, x2: PAD + to.col * COL_STRIDE, y2: ty });
    });
  });

  return (
    <div className="overflow-x-auto">
      <div style={{ position: 'relative', width: svgW, height: svgH, minWidth: svgW }}>
        {/* SVG edges layer */}
        <svg
          style={{ position: 'absolute', top: 0, left: 0, width: svgW, height: svgH, overflow: 'visible', pointerEvents: 'none' }}
        >
          <defs>
            <marker id="arrow" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto">
              <path d="M0,0 L0,6 L8,3 z" fill="#94a3b8" />
            </marker>
          </defs>
          {edges.map((e, i) => {
            const cx = (e.x1 + e.x2) / 2;
            return (
              <path
                key={i}
                d={`M ${e.x1} ${e.y1} C ${cx} ${e.y1}, ${cx} ${e.y2}, ${e.x2} ${e.y2}`}
                fill="none"
                stroke="#94a3b8"
                strokeWidth="1.5"
                markerEnd="url(#arrow)"
              />
            );
          })}
        </svg>

        {/* Task nodes */}
        {tasks.map(task => {
          const pos = positions.get(task.task_key);
          if (!pos) return null;
          const x = PAD + pos.col * COL_STRIDE;
          const y = PAD + pos.row * ROW_STRIDE;
          const style = TASK_TYPE_BG[task.task_type] || TASK_TYPE_BG.unknown;

          return (
            <div
              key={task.task_key}
              title={task.description || task.task_key}
              style={{
                position: 'absolute',
                left: x,
                top: y,
                width: NODE_W,
                height: NODE_H,
                background: style.bg,
                border: `1.5px solid ${style.border}`,
                borderRadius: 8,
                padding: '6px 10px',
                boxSizing: 'border-box',
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'center',
                gap: 2,
                boxShadow: '0 1px 3px rgba(0,0,0,0.07)',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, overflow: 'hidden' }}>
                <span style={{ width: 8, height: 8, borderRadius: '50%', background: style.dot, flexShrink: 0 }} />
                <span style={{
                  fontSize: 12,
                  fontWeight: 600,
                  color: '#1e293b',
                  fontFamily: 'monospace',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap',
                }}>
                  {task.task_key}
                </span>
              </div>
              <span style={{
                fontSize: 10,
                color: style.text,
                fontWeight: 500,
                marginLeft: 14,
                lineHeight: 1,
              }}>
                {task.task_type}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

const TASK_TYPE_COLORS: Record<string, string> = {
  notebook: 'bg-indigo-100 text-indigo-700 border-indigo-200',
  spark_jar: 'bg-orange-100 text-orange-700 border-orange-200',
  spark_python: 'bg-blue-100 text-blue-700 border-blue-200',
  python_wheel: 'bg-cyan-100 text-cyan-700 border-cyan-200',
  dbt: 'bg-green-100 text-green-700 border-green-200',
  sql: 'bg-purple-100 text-purple-700 border-purple-200',
  pipeline: 'bg-yellow-100 text-yellow-700 border-yellow-200',
  run_job: 'bg-pink-100 text-pink-700 border-pink-200',
  spark_submit: 'bg-gray-100 text-gray-700 border-gray-200',
  unknown: 'bg-gray-100 text-gray-500 border-gray-200',
};

function JobTaskCard({ job }: { job: JobDef }) {
  const [expanded, setExpanded] = useState(false);
  const hasDepTree = job.tasks.some(t => t.depends_on.length > 0);

  return (
    <div className="border border-gray-200 rounded-lg overflow-hidden">
      <div
        className="flex items-center justify-between px-4 py-3 cursor-pointer hover:bg-gray-50 transition-colors"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center gap-3 flex-1 min-w-0">
          <span className={`text-gray-400 transition-transform inline-block flex-shrink-0 ${expanded ? 'rotate-90' : ''}`}>
            &#9654;
          </span>
          <div>
            <div className="font-medium text-gray-900">{job.name}</div>
            <div className="text-xs text-gray-400">
              Job ID: {job.job_id}
              {job.creator_user_name && <span className="ml-3">by {job.creator_user_name}</span>}
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          <span className="text-xs text-gray-500 bg-gray-100 px-2 py-0.5 rounded-full">
            {job.tasks.length} task{job.tasks.length !== 1 ? 's' : ''}
          </span>
          {hasDepTree && (
            <span className="text-xs text-blue-500 bg-blue-50 px-2 py-0.5 rounded-full border border-blue-100">
              pipeline
            </span>
          )}
        </div>
      </div>

      {expanded && (
        <div className="border-t border-gray-100 bg-gray-50 p-4">
          {job.tasks.length === 0 ? (
            <div className="text-sm text-gray-400 italic py-2">No tasks defined</div>
          ) : (
            <TaskGraph tasks={job.tasks} />
          )}
        </div>
      )}
    </div>
  );
}

export default function JobTasksView({ refreshKey }: { refreshKey?: number }) {
  const [jobs, setJobs] = useState<JobDef[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');

  useEffect(() => {
    setLoading(true);
    fetch('/api/jobs/tasks')
      .then(r => r.json())
      .then(data => { setJobs(data.jobs || []); setLoading(false); })
      .catch(() => setLoading(false));
  }, [refreshKey]);

  const filtered = jobs.filter(j => {
    if (!search) return true;
    const q = search.toLowerCase();
    return (
      j.name.toLowerCase().includes(q) ||
      String(j.job_id).includes(q) ||
      j.tasks.some(t => t.task_key.toLowerCase().includes(q) || t.task_type.toLowerCase().includes(q))
    );
  });

  const sorted = [...filtered].sort((a, b) => b.tasks.length - a.tasks.length);

  if (loading) {
    return (
      <div className="space-y-3">
        {[1, 2, 3, 4].map(i => (
          <div key={i} className="h-14 bg-gray-100 animate-pulse rounded-lg" />
        ))}
      </div>
    );
  }

  // Aggregate task type counts
  const typeCounts = jobs
    .flatMap(j => j.tasks)
    .reduce((acc, t) => { acc[t.task_type] = (acc[t.task_type] || 0) + 1; return acc; }, {} as Record<string, number>);

  return (
    <div>
      <div className="mb-4 flex items-center gap-3">
        <input
          type="text"
          placeholder="Filtrar por job, task key ou tipo..."
          value={search}
          onChange={e => setSearch(e.target.value)}
          className="w-full max-w-lg px-4 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        />
        <span className="text-sm text-gray-500 ml-auto whitespace-nowrap">
          {sorted.length} de {jobs.length} job{jobs.length !== 1 ? 's' : ''}
        </span>
      </div>

      <div className="mb-4 flex flex-wrap gap-3">
        <div className="bg-white border border-gray-200 rounded-lg px-4 py-2 text-sm">
          <span className="font-semibold text-gray-900">{jobs.length}</span>
          <span className="text-gray-500 ml-1">jobs</span>
        </div>
        <div className="bg-white border border-gray-200 rounded-lg px-4 py-2 text-sm">
          <span className="font-semibold text-gray-900">{jobs.reduce((s, j) => s + j.tasks.length, 0)}</span>
          <span className="text-gray-500 ml-1">tasks</span>
        </div>
        {Object.entries(typeCounts)
          .sort((a, b) => b[1] - a[1])
          .slice(0, 5)
          .map(([type, count]) => (
            <div key={type} className={`border rounded-lg px-3 py-2 text-xs font-medium ${TASK_TYPE_COLORS[type] || TASK_TYPE_COLORS.unknown}`}>
              {type}: {count}
            </div>
          ))}
      </div>

      <div className="space-y-2">
        {sorted.map(job => <JobTaskCard key={job.job_id} job={job} />)}
        {sorted.length === 0 && (
          <div className="text-center py-12 text-gray-400">No jobs found</div>
        )}
      </div>
    </div>
  );
}
