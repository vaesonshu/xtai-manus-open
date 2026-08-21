"use client"

import { useMemo } from "react"

import { MarkdownContent } from "@/components/task/markdown-content"
import { StepToolUseInline } from "@/components/task/tool-use-inline"
import type { StepToolCall, TimelineItem, ToolRecord } from "@/lib/types"
import { Badge } from "@workspace/ui/components/badge"
import { cn } from "@workspace/ui/lib/utils"
import { AlertCircle, Bot, CheckIcon, Info } from "lucide-react"

export interface TaskMessageProps {
  className?: string
  item: TimelineItem
  tools?: ToolRecord[]
  onToolClick?: (tool: ToolRecord) => void
  selectedToolId?: string | null
}

function mergeStepDisplayTools(
  stepCalls: StepToolCall[],
  stepId: string,
  allTools: ToolRecord[],
  includeOrphans: boolean
): StepToolCall[] {
  const merged = new Map<string, StepToolCall>()

  for (const item of stepCalls) {
    merged.set(item.toolCallId, item)
  }

  for (const tool of allTools) {
    const belongsToStep = tool.stepId === stepId
    const orphanWhileRunning = includeOrphans && !tool.stepId
    if (!belongsToStep && !orphanWhileRunning) {
      continue
    }

    const next: StepToolCall = {
      toolCallId: tool.id,
      toolName: tool.toolName,
      functionName: tool.functionName,
      status: tool.status,
      args: tool.args,
      result: tool.result,
      toolContent: tool.toolContent,
    }
    const previous = merged.get(tool.id)
    merged.set(tool.id, previous ? { ...previous, ...next } : next)
  }

  return Array.from(merged.values())
}

function resolveStepToolRecord(
  tool: StepToolCall,
  allTools: ToolRecord[]
): ToolRecord {
  const full = allTools.find((entry) => entry.id === tool.toolCallId)
  if (full) {
    return full
  }

  return {
    id: tool.toolCallId,
    toolName: tool.toolName,
    functionName: tool.functionName,
    status: tool.status,
    args: tool.args,
    result: tool.result,
    toolContent: tool.toolContent,
  }
}

/** 按时间线条目类型渲染不同 UI */
export function TaskMessage({
  className,
  item,
  tools = [],
  onToolClick,
  selectedToolId,
}: TaskMessageProps) {
  if (item.kind === "message" && item.role === "user") {
    return (
      <div
        className={cn(
          "group mt-3 flex w-full flex-col items-end justify-end gap-1",
          className
        )}
      >
        <div className="relative flex max-w-[90%] flex-col items-end gap-2">
          <div className="flex items-center overflow-hidden rounded-2xl rounded-tr-sm bg-primary px-4 py-2.5 text-sm text-primary-foreground">
            {item.content}
          </div>
        </div>
      </div>
    )
  }

  if (item.kind === "message" && item.role === "assistant") {
    return (
      <div className={cn("group mt-3 flex w-full flex-col gap-2", className)}>
        <div className="flex h-7 items-center gap-2">
          <Bot className="size-4 text-muted-foreground" />
          <Badge className="h-5 border-0 bg-muted px-2 text-[10px] font-medium text-muted-foreground">
            助手
            {item.partial ? " · 生成中" : ""}
          </Badge>
        </div>
        <div
          className={cn(
            "max-w-none rounded-2xl rounded-tl-sm border bg-muted/60 px-4 py-2.5",
            item.partial && "animate-pulse"
          )}
        >
          {item.content ? (
            <MarkdownContent content={item.content} />
          ) : item.partial ? (
            <span className="text-sm text-muted-foreground">正在输入…</span>
          ) : null}
        </div>
      </div>
    )
  }

  if (item.kind === "tool") {
    return null
  }

  if (item.kind === "step") {
    return (
      <StepBlock
        stepItem={item}
        className={className}
        tools={tools}
        onToolClick={onToolClick}
        selectedToolId={selectedToolId}
      />
    )
  }

  if (item.kind === "system") {
    const isError = item.variant === "error"
    return (
      <div
        className={cn(
          "mt-3 flex items-start gap-2 rounded-lg border px-4 py-3 text-sm",
          isError
            ? "border-destructive/30 bg-destructive/5 text-destructive"
            : "border-dashed bg-muted/30 text-muted-foreground",
          className
        )}
      >
        {isError ? (
          <AlertCircle className="mt-0.5 size-4 shrink-0" />
        ) : (
          <Info className="mt-0.5 size-4 shrink-0" />
        )}
        <span>{item.content}</span>
      </div>
    )
  }

  return null
}

function StepBlock({
  stepItem,
  className,
  tools,
  onToolClick,
  selectedToolId,
}: {
  stepItem: Extract<TimelineItem, { kind: "step" }>
  className?: string
  tools: ToolRecord[]
  onToolClick?: (tool: ToolRecord) => void
  selectedToolId?: string | null
}) {
  const { step, eventStatus, toolCalls = [] } = stepItem
  const isRunning =
    eventStatus === "started" ||
    step.status === "running" ||
    step.status === "started"
  const isFailed = step.status === "failed" || eventStatus === "failed"
  const hasError = Boolean(step.error?.trim())
  const displayTools = useMemo(
    () => mergeStepDisplayTools(toolCalls, step.step_id, tools, isRunning),
    [toolCalls, step.step_id, tools, isRunning]
  )
  const hasToolCalls = displayTools.length > 0
  const showToolArea = hasToolCalls || isRunning

  return (
    <div className={cn("mt-3 flex flex-col", className)}>
      <div className="flex w-full items-center justify-between gap-2 text-sm">
        <div className="flex min-w-0 flex-1 items-center gap-2">
          <div
            className={cn(
              "flex h-4 w-4 shrink-0 items-center justify-center rounded-full border",
              isFailed
                ? "border-destructive bg-destructive"
                : isRunning
                  ? "border-amber-500 bg-amber-500/20"
                  : "border-muted-foreground/40 bg-muted-foreground/30"
            )}
          >
            {!isRunning && !isFailed && (
              <CheckIcon className="size-2.5 text-background" />
            )}
          </div>
          <div className="min-w-0 truncate font-medium">{step.description}</div>
        </div>
        {isRunning && (
          <Badge
            variant="outline"
            className="h-5 shrink-0 border-amber-500/40 text-[10px] text-amber-600"
          >
            执行中
          </Badge>
        )}
      </div>

      {showToolArea ? (
        <div className="ml-3 flex min-w-0 flex-col gap-1.5 border-l-2 border-border/70 py-1.5 pl-3">
          {displayTools.map((tool) => {
            const record = resolveStepToolRecord(tool, tools)
            return (
              <StepToolUseInline
                key={tool.toolCallId}
                tool={record}
                selected={tool.toolCallId === selectedToolId}
                onClick={onToolClick ? () => onToolClick(record) : undefined}
              />
            )
          })}
          {isRunning && !hasToolCalls ? (
            <p className="text-xs text-muted-foreground">等待工具调用…</p>
          ) : null}
        </div>
      ) : null}

      {hasError ? (
        <div className="mt-2 rounded-lg border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm text-destructive">
          {step.error}
        </div>
      ) : null}
    </div>
  )
}
