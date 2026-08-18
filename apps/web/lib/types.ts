/** 与后端 presentation/api/schemas.py 对齐的前端类型 */

export type TaskStatus =
  | "created"
  | "running"
  | "waiting"
  | "completed"
  | "failed"
  | "cancelled"

export type StreamEventType =
  | "plan"
  | "step"
  | "message"
  | "tool"
  | "title"
  | "wait"
  | "error"
  | "done"

export interface TaskStep {
  step_id: string
  description: string
  agent_role: string
  status: string
  result?: string | null
  error?: string | null
  success?: boolean
  attachments?: unknown[]
}

export interface TaskPlan {
  plan_id: string
  title: string
  goal: string
  message: string
  status: string
  steps: TaskStep[]
}

export interface TaskResponse {
  task_id: string
  goal: string
  status: TaskStatus
  plan?: TaskPlan | null
  plan_versions?: unknown[]
  result?: Record<string, unknown>
  error?: string | null
}

export interface StreamEvent {
  id: string
  type: StreamEventType
  created_at: string
  status?: string
  plan?: TaskPlan
  step?: TaskStep
  role?: "user" | "assistant"
  message?: string
  title?: string
  error?: string
  reason?: string
  question?: string
  tool_call_id?: string
  tool_name?: string
  function_name?: string
  function_args?: Record<string, unknown>
  function_result?: unknown
  attachments?: unknown[]
}

export interface HealthResponse {
  status: string
  service: string
  env: string
  redis: string
  database: string
}

export interface LlmConfigResponse {
  config_id: string
  provider: string
  model: string
  base_url: string
  temperature: number
  max_tokens: number | null
  timeout_seconds: number
  api_key_masked: string
  has_api_key: boolean
}

export interface UpdateLlmConfigRequest {
  provider?: string
  model?: string
  api_key?: string
  base_url?: string
  temperature?: number
  max_tokens?: number | null
  timeout_seconds?: number
  clear_max_tokens?: boolean
}

export interface AgentRunResponse {
  run_id: string
  goal: string
  status: string
  result: Record<string, unknown>
  error: string | null
}

/** 本地任务列表元数据 */
export interface TaskSessionMeta {
  taskId: string
  goal: string
  title: string
  status: TaskStatus
  updatedAt: string
}

/** 时间线条目：混排消息、步骤、工具 */
export type TimelineItem =
  | {
      id: string
      kind: "message"
      role: "user" | "assistant"
      content: string
      createdAt?: string
    }
  | {
      id: string
      kind: "step"
      step: TaskStep
      eventStatus: string
      createdAt?: string
    }
  | {
      id: string
      kind: "tool"
      toolCallId: string
      toolName: string
      functionName: string
      status: "calling" | "called"
      args?: Record<string, unknown>
      result?: unknown
      createdAt?: string
    }
  | {
      id: string
      kind: "system"
      content: string
      variant?: "info" | "error"
      createdAt?: string
    }

export interface ToolRecord {
  id: string
  toolName: string
  functionName: string
  status: "calling" | "called"
  args?: Record<string, unknown>
  result?: unknown
}

export interface TaskUiState {
  taskId: string | null
  goal: string
  title: string
  status: TaskStatus
  plan: TaskPlan | null
  steps: TaskStep[]
  timeline: TimelineItem[]
  tools: ToolRecord[]
  waitQuestion: string | null
  waitReason: string | null
  error: string | null
  isStreaming: boolean
}
