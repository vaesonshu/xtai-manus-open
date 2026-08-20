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
import { mergePlanStep } from "@/lib/plan-steps"

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
  streamingMessageId: null,
  /** 已处理的 SSE 事件 id，避免重连回放重复渲染 */
  seenEventIds: {},
}

export type TaskAction =
  | { type: "HYDRATE_TASK"; task: TaskResponse }
  | { type: "SET_STREAMING"; value: boolean }
  | { type: "APPLY_EVENT"; event: StreamEvent }
  | { type: "ADD_USER_MESSAGE"; content: string }
  | { type: "START_TASK"; goal: string }
  | { type: "TASK_CREATED"; taskId: string; status?: TaskStatus }
  | { type: "RESET" }

function upsertStep(steps: TaskStep[], step: TaskStep, plan: TaskPlan | null): TaskStep[] {
  return mergePlanStep(steps, step, plan)
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
    toolContent: event.tool_content,
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

/** 标记 SSE 事件已处理，防止重连时重复写入时间线 */
function markEventSeen(
  state: TaskUiState,
  eventId: string | undefined
): TaskUiState | null {
  if (!eventId) {
    return state
  }
  if (state.seenEventIds[eventId]) {
    return null
  }
  return {
    ...state,
    seenEventIds: { ...state.seenEventIds, [eventId]: true },
  }
}

/** 查找时间线中最后一条非 partial 的助手消息 */
function findLastAssistantMessage(
  timeline: TimelineItem[]
): (TimelineItem & { kind: "message"; role: "assistant" }) | null {
  for (let i = timeline.length - 1; i >= 0; i -= 1) {
    const item = timeline[i]
    if (
      item?.kind === "message" &&
      item.role === "assistant" &&
      !item.partial
    ) {
      return item as TimelineItem & { kind: "message"; role: "assistant" }
    }
  }
  return null
}

/** 合并或追加助手消息，避免逐步执行 + 汇总时重复气泡 */
function appendAssistantMessage(
  state: TaskUiState,
  item: TimelineItem & {
    kind: "message"
    role: "assistant"
    content: string
    partial?: boolean
  }
): TimelineItem[] {
  if (item.partial) {
    return upsertTimelineItem(state.timeline, item)
  }

  const content = item.content.trim()
  const last = findLastAssistantMessage(state.timeline)

    if (last) {
    const previous = last.content.trim()
    if (previous === content) {
      return state.timeline
    }
    // 最终汇总更长：替换上一条（常见于「请稍等」后被完整行程覆盖）
    if (content.length > previous.length && content.length >= 300) {
      return upsertTimelineItem(state.timeline, {
        ...last,
        content: item.content,
        id: item.id,
        partial: false,
        createdAt: item.createdAt ?? last.createdAt,
      })
    }
    // 汇总消息常包含上一条助手输出，用更长的一条替换而非再叠一条
    if (previous && content.includes(previous)) {
      return upsertTimelineItem(state.timeline, {
        ...last,
        content: item.content,
        id: item.id,
        partial: false,
        createdAt: item.createdAt ?? last.createdAt,
      })
    }
    // 新的汇总比已有交付物短很多：视为空洞收尾，不覆盖完整正文
    if (
      previous.length > content.length * 2 &&
      content.length < 320 &&
      !previous.includes(content.slice(0, Math.min(40, content.length)))
    ) {
      return state.timeline
    }
  }

  return upsertTimelineItem(state.timeline, {
    ...item,
    partial: false,
  })
}

/** 将 SSE 事件应用到 UI 状态 */
function applyStreamEvent(
  state: TaskUiState,
  event: StreamEvent
): TaskUiState {
  const marked = markEventSeen(state, event.id)
  if (marked === null) {
    return state
  }
  state = marked

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

      const steps = upsertStep(state.steps, step, state.plan)
      const eventStatus = event.status ?? step.status
      // 同一步骤只保留一张卡片，started → completed 原地更新，避免重复块
      const timeline = upsertTimelineItem(state.timeline, {
        id: `step-${step.step_id}`,
        kind: "step",
        step,
        eventStatus,
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
      const isPartial = Boolean(event.partial)
      const streamId =
        event.stream_id ?? state.streamingMessageId ?? event.id

      if (role === "assistant" && isPartial) {
        if (
          state.streamingMessageId === streamId &&
          state.timeline.some(
            (item) =>
              item.kind === "message" &&
              item.id === streamId &&
              item.content === content &&
              item.partial
          )
        ) {
          return state
        }

        return {
          ...state,
          streamingMessageId: streamId,
          timeline: upsertTimelineItem(state.timeline, {
            id: streamId,
            kind: "message",
            role: "assistant",
            content,
            partial: true,
            createdAt,
          }),
        }
      }

      const messageId =
        role === "assistant" && event.stream_id
          ? event.stream_id
          : event.id || `message-${state.timeline.length}`

      const messageItem: TimelineItem = {
        id: messageId,
        kind: "message",
        role,
        content,
        partial: false,
        createdAt,
      }

      return {
        ...state,
        streamingMessageId: null,
        timeline:
          role === "assistant"
            ? appendAssistantMessage(
                state,
                messageItem as TimelineItem & {
                  kind: "message"
                  role: "assistant"
                  content: string
                }
              )
            : upsertTimelineItem(state.timeline, messageItem),
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
        streamingMessageId: null,
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
        streamingMessageId: null,
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
        streamingMessageId: null,
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

    case "START_TASK":
      return {
        ...initialTaskUiState,
        goal: action.goal,
        status: "running",
        isStreaming: true,
        seenEventIds: {},
        timeline: [
          {
            id: `local-user-${Date.now()}`,
            kind: "message",
            role: "user",
            content: action.goal,
          },
        ],
      }

    case "TASK_CREATED":
      return {
        ...state,
        taskId: action.taskId,
        status: action.status ?? "running",
        isStreaming: true,
      }

    case "APPLY_EVENT":
      return applyStreamEvent(state, action.event)

    default:
      return state
  }
}
