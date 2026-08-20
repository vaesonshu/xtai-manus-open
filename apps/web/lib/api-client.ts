import type {
  AgentRunResponse,
  HealthResponse,
  LlmConfigResponse,
  TaskResponse,
  UpdateLlmConfigRequest,
} from "@/lib/types"

/** 浏览器侧 API 根路径：优先 env，否则走 Next 同源代理 */
export function getApiBase(): string {
  const fromEnv = process.env.NEXT_PUBLIC_API_URL?.trim()
  if (fromEnv) {
    return fromEnv.replace(/\/$/, "")
  }
  return "/api"
}

/**
 * SSE 订阅专用 API 根路径。
 * Next.js rewrite 代理在 dev 环境会缓冲 text/event-stream，导致事件整批到达；
 * 本地开发时直连 FastAPI，保证 plan / message 等事件实时渲染。
 */
export function getStreamApiBase(): string {
  const fromEnv = process.env.NEXT_PUBLIC_API_URL?.trim()
  if (fromEnv) {
    return fromEnv.replace(/\/$/, "")
  }
  if (typeof window !== "undefined") {
    const { hostname } = window.location
    if (hostname === "localhost" || hostname === "127.0.0.1") {
      return "http://127.0.0.1:8000"
    }
  }
  return getApiBase()
}

class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly body?: unknown
  ) {
    super(message)
    this.name = "ApiError"
  }
}

async function request<T>(
  path: string,
  init?: RequestInit
): Promise<T> {
  const response = await fetch(`${getApiBase()}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
  })

  if (!response.ok) {
    let body: unknown
    try {
      body = await response.json()
    } catch {
      body = undefined
    }
    const message =
      typeof body === "object" &&
      body !== null &&
      "error" in body &&
      typeof (body as { error?: { message?: string } }).error?.message ===
        "string"
        ? (body as { error: { message: string } }).error.message
        : `Request failed (${response.status})`
    throw new ApiError(message, response.status, body)
  }

  if (response.status === 204) {
    return undefined as T
  }

  return (await response.json()) as T
}

/** 健康检查 */
export function fetchHealth(): Promise<HealthResponse> {
  return request<HealthResponse>("/health")
}

/** 创建任务 */
export function createTask(goal: string): Promise<TaskResponse> {
  return request<TaskResponse>("/v1/tasks", {
    method: "POST",
    body: JSON.stringify({ goal }),
  })
}

/** 查询任务 */
export function getTask(taskId: string): Promise<TaskResponse> {
  return request<TaskResponse>(`/v1/tasks/${taskId}`)
}

/** 等待状态下用户回复 */
export function replyTask(
  taskId: string,
  content: string
): Promise<TaskResponse> {
  return request<TaskResponse>(`/v1/tasks/${taskId}/reply`, {
    method: "POST",
    body: JSON.stringify({ content }),
  })
}

/** 获取 LLM 配置 */
export function fetchLlmConfig(): Promise<LlmConfigResponse> {
  return request<LlmConfigResponse>("/v1/llm/config")
}

/** 更新 LLM 配置 */
export function updateLlmConfig(
  payload: UpdateLlmConfigRequest
): Promise<LlmConfigResponse> {
  return request<LlmConfigResponse>("/v1/llm/config", {
    method: "PUT",
    body: JSON.stringify(payload),
  })
}

/** 发起 Agent Run（旧版接口） */
export function startAgentRun(goal: string): Promise<AgentRunResponse> {
  return request<AgentRunResponse>("/v1/agents/runs", {
    method: "POST",
    body: JSON.stringify({ goal }),
  })
}

/** 查询 Agent Run */
export function getAgentRun(runId: string): Promise<AgentRunResponse> {
  return request<AgentRunResponse>(`/v1/agents/runs/${runId}`)
}

/** 订阅任务 SSE 流 */
export function subscribeTaskStream(
  taskId: string,
  onEvent: (event: unknown) => void,
  onError?: (error: Event) => void
): () => void {
  const source = new EventSource(
    `${getStreamApiBase()}/v1/tasks/${taskId}/stream`
  )

  source.onmessage = (message) => {
    try {
      onEvent(JSON.parse(message.data))
    } catch {
      // 忽略无法解析的事件
    }
  }

  source.onerror = (error) => {
    onError?.(error)
    source.close()
  }

  return () => source.close()
}

export { ApiError }
