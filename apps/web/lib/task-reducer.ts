import type {
  StreamEvent,
  TaskPlan,
  TaskResponse,
  TaskStep,
  TaskStatus,
  TaskUiState,
  TimelineItem,
  ToolRecord,
  StepToolCall,
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

function upsertStep(
  steps: TaskStep[],
  step: TaskStep,
  plan: TaskPlan | null
): TaskStep[] {
  return mergePlanStep(steps, step, plan)
}

function upsertTool(tools: ToolRecord[], event: StreamEvent): ToolRecord[] {
  if (!event.tool_call_id) {
    return tools
  }

  const record: ToolRecord = {
    id: event.tool_call_id,
    stepId: event.step_id?.trim() || undefined,
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

function toolRecordToStepToolCall(tool: ToolRecord): StepToolCall {
  return {
    toolCallId: tool.id,
    toolName: tool.toolName,
    functionName: tool.functionName,
    status: tool.status,
    args: tool.args,
    result: tool.result,
    toolContent: tool.toolContent,
  }
}

function buildStepToolCall(event: StreamEvent): StepToolCall | null {
  if (!event.tool_call_id) {
    return null
  }

  return {
    toolCallId: event.tool_call_id,
    toolName: event.tool_name ?? "tool",
    functionName: event.function_name ?? "unknown",
    status: event.status === "called" ? "called" : "calling",
    args: event.function_args,
    result: event.function_result,
    toolContent: event.tool_content,
    createdAt: event.created_at,
  }
}

function mergeStepToolCalls(
  existing: StepToolCall[] | undefined,
  incoming: StepToolCall[]
): StepToolCall[] {
  const merged = new Map<string, StepToolCall>()
  for (const item of existing ?? []) {
    merged.set(item.toolCallId, item)
  }
  for (const item of incoming) {
    const previous = merged.get(item.toolCallId)
    merged.set(item.toolCallId, previous ? { ...previous, ...item } : item)
  }
  return Array.from(merged.values())
}

function stepToolCallsFromRecords(
  tools: ToolRecord[],
  stepId: string
): StepToolCall[] {
  return tools
    .filter((tool) => tool.stepId === stepId)
    .map(toolRecordToStepToolCall)
}

function isActiveStepItem(
  item: Extract<TimelineItem, { kind: "step" }>
): boolean {
  return (
    item.eventStatus === "started" ||
    item.step.status === "running" ||
    item.step.status === "started"
  )
}

/** 后端未带 step_id 时，回落到当前执行中的步骤，再回落到最近一张步骤卡片 */
function resolveStepIdForToolEvent(
  event: StreamEvent,
  timeline: TimelineItem[]
): string | undefined {
  const explicit = event.step_id?.trim()
  if (explicit) {
    return explicit
  }

  for (let i = timeline.length - 1; i >= 0; i -= 1) {
    const item = timeline[i]
    if (item?.kind === "step" && isActiveStepItem(item)) {
      return item.step.step_id
    }
  }

  for (let i = timeline.length - 1; i >= 0; i -= 1) {
    const item = timeline[i]
    if (item?.kind === "step") {
      return item.step.step_id
    }
  }

  return undefined
}

/** 将 state.tools 中已归属的工具同步回各步骤卡片 */
function syncStepToolCalls(
  timeline: TimelineItem[],
  tools: ToolRecord[]
): TimelineItem[] {
  return timeline.map((item) => {
    if (item.kind !== "step") {
      return item
    }

    const merged = mergeStepToolCalls(
      item.toolCalls,
      stepToolCallsFromRecords(tools, item.step.step_id)
    )

    if (merged.length === 0) {
      return item
    }

    return { ...item, toolCalls: merged }
  })
}

function attachToolToTimeline(
  timeline: TimelineItem[],
  event: StreamEvent,
  tools: ToolRecord[]
): TimelineItem[] {
  const toolCall = buildStepToolCall(event)
  if (!toolCall) {
    return timeline
  }

  const stepId = resolveStepIdForToolEvent(event, timeline)
  if (!stepId) {
    return timeline
  }

  const stepItemId = `step-${stepId}`
  const stepIndex = timeline.findIndex((entry) => entry.id === stepItemId)
  if (stepIndex === -1) {
    return timeline
  }

  const stepItem = timeline[stepIndex]
  if (stepItem?.kind !== "step") {
    return timeline
  }

  const next = [...timeline]
  next[stepIndex] = {
    ...stepItem,
    toolCalls: mergeStepToolCalls(stepItem.toolCalls, [toolCall]),
  }
  return syncStepToolCalls(next, tools)
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

/** 去掉与最终帧同 stream_id 的「生成中」气泡，避免卡住 partial */
function dropMatchingPartial(
  timeline: TimelineItem[],
  streamId: string
): TimelineItem[] {
  return timeline.filter(
    (entry) =>
      !(
        entry.kind === "message" &&
        entry.role === "assistant" &&
        entry.partial &&
        entry.id === streamId
      )
  )
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

  // 最终帧必须先清掉同 stream 的 partial，否则「生成中」会永远挂着
  const timeline = dropMatchingPartial(state.timeline, item.id)
  const content = item.content.trim()
  const last = findLastAssistantMessage(timeline)

  if (last) {
    const previous = last.content.trim()
    if (previous === content) {
      // 与已有最终消息重复：只丢弃本轮流式气泡，不叠第二条
      return timeline
    }
    // 最终汇总更长：替换上一条（常见于「请稍等」后被完整行程覆盖）
    if (content.length > previous.length && content.length >= 300) {
      const withoutLast = timeline.filter((entry) => entry.id !== last.id)
      return upsertTimelineItem(withoutLast, {
        ...last,
        content: item.content,
        id: item.id,
        partial: false,
        createdAt: item.createdAt ?? last.createdAt,
      })
    }
    // 汇总消息常包含上一条助手输出，用更长的一条替换而非再叠一条
    if (previous && content.includes(previous)) {
      const withoutLast = timeline.filter((entry) => entry.id !== last.id)
      return upsertTimelineItem(withoutLast, {
        ...last,
        content: item.content,
        id: item.id,
        partial: false,
        createdAt: item.createdAt ?? last.createdAt,
      })
    }
    // 短于上一条时：不覆盖长文；但短答案（如 4053）仍追加，空话收尾则丢弃
    if (
      previous.length > content.length * 2 &&
      content.length < 320 &&
      !previous.includes(content.slice(0, Math.min(40, content.length)))
    ) {
      const isCompactAnswer = content.length <= 80 && /\d/.test(content)
      const isHollowCloser =
        content.length < 80 &&
        /^(已完成|希望|祝您|如有|任务已|好的|完成了)/u.test(content)
      if (isHollowCloser && !isCompactAnswer) {
        return timeline
      }
      return upsertTimelineItem(timeline, {
        ...item,
        partial: false,
      })
    }
  }

  return upsertTimelineItem(timeline, {
    ...item,
    partial: false,
  })
}

/** 将 SSE 事件应用到 UI 状态 */
function applyStreamEvent(state: TaskUiState, event: StreamEvent): TaskUiState {
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
      const stepItemId = `step-${step.step_id}`
      const existingStep = state.timeline.find(
        (entry): entry is Extract<TimelineItem, { kind: "step" }> =>
          entry.id === stepItemId && entry.kind === "step"
      )
      const isActiveStep =
        eventStatus === "started" ||
        step.status === "running" ||
        step.status === "started"
      // 工具事件可能早于步骤卡片：把尚无归属的工具挂到当前步骤
      const tools = isActiveStep
        ? state.tools.map((tool) =>
            tool.stepId ? tool : { ...tool, stepId: step.step_id }
          )
        : state.tools
      const toolCalls = mergeStepToolCalls(
        existingStep?.toolCalls,
        stepToolCallsFromRecords(tools, step.step_id)
      )
      const timeline = syncStepToolCalls(
        upsertTimelineItem(state.timeline, {
          id: stepItemId,
          kind: "step",
          step,
          eventStatus,
          toolCalls,
          createdAt: existingStep?.createdAt ?? createdAt,
        }),
        tools
      )

      return {
        ...state,
        steps,
        tools,
        plan: state.plan ? { ...state.plan, steps } : state.plan,
        timeline,
        status: state.status === "waiting" ? state.status : "running",
      }
    }

    case "message": {
      const content = event.message ?? ""
      const role = event.role ?? "assistant"
      const isPartial = Boolean(event.partial)
      const streamId = event.stream_id ?? state.streamingMessageId ?? event.id

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
      const resolvedStepId = resolveStepIdForToolEvent(event, state.timeline)
      const normalizedEvent =
        resolvedStepId && !event.step_id?.trim()
          ? { ...event, step_id: resolvedStepId }
          : event
      const tools = upsertTool(state.tools, normalizedEvent)
      const timeline = attachToolToTimeline(
        state.timeline,
        normalizedEvent,
        tools
      )

      return {
        ...state,
        tools,
        timeline,
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
