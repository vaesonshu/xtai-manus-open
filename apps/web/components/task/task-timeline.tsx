"use client"

import { useCallback } from "react"

import { AssistantLoading } from "@/components/task/assistant-loading"
import { StatusBanner } from "@/components/task/status-banner"
import { TaskMessage } from "@/components/task/task-message"
import { useScrollToBottom } from "@/hooks/use-scroll-to-bottom"
import type { TaskUiState, ToolRecord } from "@/lib/types"
import { ScrollArea } from "@workspace/ui/components/scroll-area"

interface TaskTimelineProps {
  state: Pick<
    TaskUiState,
    | "timeline"
    | "tools"
    | "status"
    | "error"
    | "waitQuestion"
    | "waitReason"
    | "isStreaming"
    | "streamingMessageId"
  >
  onToolSelect?: (tool: ToolRecord) => void
  selectedToolId?: string | null
  className?: string
}

/** 提取时间线末尾内容长度，用于触发滚动 */
function getTimelineScrollFingerprint(
  timeline: TaskUiState["timeline"]
): string {
  const last = timeline[timeline.length - 1]
  if (!last) return ""

  if (last.kind === "message") {
    return `${last.content}|${last.partial ? 1 : 0}`
  }
  if (last.kind === "step") {
    return `${last.step.step_id}:${last.step.result ?? ""}|${last.step.status}`
  }
  return `${last.kind}`
}

/** 任务时间线：消息 / 步骤 / 工具混排 */
export function TaskTimeline({
  state,
  onToolSelect,
  selectedToolId,
  className,
}: TaskTimelineProps) {
  const { timeline, tools, isStreaming } = state
  const scrollFingerprint = getTimelineScrollFingerprint(timeline)
  // 已有 plan/step/工具/助手消息时不再显示「正在思考」，避免 SSE 已推送但 UI 仍空白
  const hasAssistantActivity = timeline.some(
    (item) =>
      item.kind === "step" ||
      item.kind === "tool" ||
      (item.kind === "message" && item.role === "assistant")
  )
  const showAssistantLoading = isStreaming && !hasAssistantActivity

  const { rootRef, contentRef } = useScrollToBottom<HTMLDivElement>(
    [timeline.length, scrollFingerprint, isStreaming],
    { streaming: isStreaming }
  )

  const handleToolClick = useCallback(
    (tool: ToolRecord) => {
      onToolSelect?.(tool)
    },
    [onToolSelect]
  )

  return (
    <div ref={rootRef} className={className}>
      <ScrollArea className="h-full px-4 md:px-6 [&_[data-slot=scroll-area-scrollbar]]:hidden [&_[data-slot=scroll-area-viewport]]:[-ms-overflow-style:none] [&_[data-slot=scroll-area-viewport]]:[scrollbar-width:none] [&_[data-slot=scroll-area-viewport]]:[&::-webkit-scrollbar]:hidden">
        <div ref={contentRef} className="mx-auto max-w-3xl space-y-2 py-6">
          <StatusBanner state={state} />

          {timeline.length === 0 ? (
            <div className="flex min-h-[240px] items-center justify-center text-sm text-muted-foreground">
              等待智能体开始规划与执行…
            </div>
          ) : (
            timeline
              .filter((item) => item.kind !== "tool")
              .map((item) => (
                <TaskMessage
                  key={item.id}
                  item={item}
                  tools={tools}
                  onToolClick={handleToolClick}
                  selectedToolId={selectedToolId}
                />
              ))
          )}

          {showAssistantLoading ? (
            <AssistantLoading hint="智能体正在思考…" />
          ) : null}
        </div>
      </ScrollArea>
    </div>
  )
}
