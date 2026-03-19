export interface Job {
  job_id: number;
  name: string;
  created_time?: number;
  creator_user_name?: string;
  latest_run?: {
    state: string;
    run_id: number;
    start_time?: number;
    params?: Record<string, unknown>;
  };
}

export interface Task {
  task_key: string;
  state: string;
  start_time?: number;
  end_time?: number;
  duration_ms?: number;
  attempt_number?: number;
  description?: string;
}

export interface Run {
  run_id: number;
  job_id: number;
  run_name?: string;
  state: string;
  state_message?: string;
  start_time?: number;
  end_time?: number;
  duration_ms?: number;
  params: Record<string, unknown>;
  tasks: Task[];
  run_page_url?: string;
  trigger?: string;
}

export interface Stats {
  total_jobs: number;
  total_runs: number;
  running: number;
  failed: number;
  success: number;
  pending: number;
}
