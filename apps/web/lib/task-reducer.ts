import type {
  StreamEvent,
  TaskPlan,
  TaskResponse,
  TaskStep,
  TaskStatus,
  TaskUiState,
  TimelineItem,
  ToolRecord,
} from "@/lib/types"

export const initialTaskUiState: TaskUiState = {
  taskId: null,
  goal: "",
  title: "",
  status: "created",
  plan: null,
  steps: [],
  timeline: [],
  tools: [],
  waitQuestion: null,
  waitReason: null,
  error: null,
  isStreaming: false,
}

export type TaskAction =
  | { type: "HYDRATE_TASK"; task: TaskResponse }
  | { type: "SET_STREAMING"; value: boolean }
  | { type: "APPLY_EVENT"; event: StreamEvent }
  | { type: "ADD_USER_MESSAGE"; content: string }
  | { type: "RESET" }

function upsertStep(steps: TaskStep[], step: TaskStep): TaskStep[] {
  const index = steps.findIndex((item) => item.step_id === step.step_id)
  if (index === -1) {
    return [...steps, step]
  }
  const next = [...steps]
  next[index] = { ...next[index], ...step }
  return next
}

function upsertTool(tools: ToolRecord[], event: StreamEvent): ToolRecord[] {
  if (!event.tool_call_id) {
    return tools
  }

  const record: ToolRecord = {
    id: event.tool_call_id,
    toolName: event.tool_name ?? "tool",
    functionName: event.function_name ?? "unknown",
    status: event.status === "called" ? "called" : "calling",
    args: event.function_args,
    result: event.function_result,
  }

  const index = tools.findIndex((item) => item.id === record.id)
  if (index === -1) {
    return [...tools, record]
  }

  const next = [...tools]
  next[index] = { ...next[index], ...record }
  return next
}

function upsertTimelineItem(
  timeline: TimelineItem[],
  item: TimelineItem
): TimelineItem[] {
  const index = timeline.findIndex((entry) => entry.id === item.id)
  if (index === -1) {
    return [...timeline, item]
  }

  const next = [...timeline]
  next[index] = item
  return next
}

/** 将 SSE 事件应用到 UI 状态 */
function applyStreamEvent(
  state: TaskUiState,
  event: StreamEvent
): TaskUiState {
  const createdAt = event.created_at

  switch (event.type) {
    case "title":
      return {
        ...state,
        title: event.title ?? state.title,
      }

    case "plan": {
      const plan = event.plan as TaskPlan | undefined
      if (!plan) {
        return state
      }
      return {
        ...state,
        plan,
        steps: plan.steps,
        title: plan.title || state.title,
      }
    }

    case "step": {
      const step = event.step
      if (!step) {
        return state
      }

      const steps = upsertStep(state.steps, step)
      const timeline = upsertTimelineItem(state.timeline, {
        id: `step-${step.step_id}-${event.status ?? "update"}`,
        kind: "step",
        step,
        eventStatus: event.status ?? step.status,
        createdAt,
      })

      return {
        ...state,
        steps,
        plan: state.plan ? { ...state.plan, steps } : state.plan,
        timeline,
        status: state.status === "waiting" ? state.status : "running",
      }
    }

    case "message": {
      const content = event.message ?? ""
      const role = event.role ?? "assistant"
      const messageId = event.id || `message-${state.timeline.length}`

      return {
        ...state,
        timeline: upsertTimelineItem(state.timeline, {
          id: messageId,
          kind: "message",
          role,
          content,
          createdAt,
        }),
      }
    }

    case "tool": {
      const tools = upsertTool(state.tools, event)
      const toolItem: TimelineItem = {
        id: `tool-${event.tool_call_id}`,
        kind: "tool",
        toolCallId: event.tool_call_id ?? "",
        toolName: event.tool_name ?? "tool",
        functionName: event.function_name ?? "unknown",
        status: event.status === "called" ? "called" : "calling",
        args: event.function_args,
        result: event.function_result,
        createdAt,
      }

      return {
        ...state,
        tools,
        timeline: upsertTimelineItem(state.timeline, toolItem),
      }
    }

    case "wait":
      return {
        ...state,
        status: "waiting",
        isStreaming: false,
        waitQuestion: event.question ?? null,
        waitReason: event.reason ?? null,
        timeline: upsertTimelineItem(state.timeline, {
          id: event.id,
          kind: "system",
          content: event.question || event.reason || "等待你的回复",
          variant: "info",
          createdAt,
        }),
      }

    case "error":
      return {
        ...state,
        status: "failed",
        isStreaming: false,
        error: event.error ?? "任务执行失败",
        timeline: upsertTimelineItem(state.timeline, {
          id: event.id,
          kind: "system",
          content: event.error ?? "任务执行失败",
          variant: "error",
          createdAt,
        }),
      }

    case "done":
      return {
        ...state,
        status:
          state.status === "failed" ? "failed" : ("completed" as TaskStatus),
        isStreaming: false,
        waitQuestion: null,
        waitReason: null,
      }

    default:
      return state
  }
}

/** Task UI 状态 reducer */
export function taskReducer(
  state: TaskUiState,
  action: TaskAction
): TaskUiState {
  switch (action.type) {
    case "RESET":
      return { ...initialTaskUiState }

    case "SET_STREAMING":
      return { ...state, isStreaming: action.value }

    case "HYDRATE_TASK": {
      const { task } = action
      return {
        ...state,
        taskId: task.task_id,
        goal: task.goal,
        title: task.plan?.title ?? state.title,
        status: task.status,
        plan: task.plan ?? null,
        steps: task.plan?.steps ?? [],
        error: task.error ?? null,
      }
    }

    case "ADD_USER_MESSAGE":
      return {
        ...state,
        timeline: [
          ...state.timeline,
          {
            id: `local-user-${Date.now()}`,
            kind: "message",
            role: "user",
            content: action.content,
          },
        ],
        waitQuestion: null,
        waitReason: null,
        status: "running",
        isStreaming: true,
      }

    case "APPLY_EVENT":
      return applyStreamEvent(state, action.event)

    default:
      return state
  }
}
