"use client"

import { useState } from "react"

import { MarkdownContent } from "@/components/task/markdown-content"
import { ToolUseInline } from "@/components/task/tool-use-inline"
import type { TimelineItem, ToolRecord } from "@/lib/types"
import { Badge } from "@workspace/ui/components/badge"
import { cn } from "@workspace/ui/lib/utils"
import {
  AlertCircle,
  Bot,
  CheckIcon,
  ChevronDown,
  Info,
} from "lucide-react"

export interface TaskMessageProps {
  className?: string
  item: TimelineItem
  onToolClick?: (tool: ToolRecord) => void
  selectedToolId?: string | null
}

function timelineToolToRecord(
  item: Extract<TimelineItem, { kind: "tool" }>
): ToolRecord {
  return {
    id: item.toolCallId,
    toolName: item.toolName,
    functionName: item.functionName,
    status: item.status,
    args: item.args,
    result: item.result,
  }
}

/** 按时间线条目类型渲染不同 UI */
export function TaskMessage({
  className,
  item,
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
    const tool = timelineToolToRecord(item)
    return (
      <div className={cn("mt-3 flex w-full min-w-0 items-center", className)}>
        <ToolUseInline
          tool={tool}
          selected={item.toolCallId === selectedToolId}
          onClick={onToolClick ? () => onToolClick(tool) : undefined}
        />
      </div>
    )
  }

  if (item.kind === "step") {
    return (
      <StepBlock stepItem={item} className={className} />
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
}: {
  stepItem: Extract<TimelineItem, { kind: "step" }>
  className?: string
}) {
  const [expanded, setExpanded] = useState(true)
  const { step, eventStatus } = stepItem
  const isRunning = eventStatus === "started" || step.status === "running"
  const isFailed = step.status === "failed" || eventStatus === "failed"
  const displayResult = step.result?.trim() ?? ""
  const hasResult = Boolean(displayResult)
  const hasError = Boolean(step.error?.trim())
  const hasBody = hasResult || hasError || isRunning

  return (
    <div className={cn("mt-3 flex flex-col", className)}>
      <button
        type="button"
        aria-expanded={expanded}
        onClick={() => setExpanded((v) => !v)}
        className="group/header flex w-full cursor-pointer items-center justify-between gap-2 rounded-md text-sm outline-none transition-colors hover:bg-muted/50 focus-visible:ring-2 focus-visible:ring-ring"
      >
        <div className="flex min-w-0 flex-1 flex-row items-center justify-start gap-2">
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
          <div className="min-w-0 truncate text-left font-medium">
            {step.description}
          </div>
          {hasBody && (
            <ChevronDown
              className={cn(
                "size-4 shrink-0 text-muted-foreground transition-transform duration-200",
                expanded && "rotate-180"
              )}
            />
          )}
        </div>
        {isRunning && (
          <Badge
            variant="outline"
            className="h-5 shrink-0 border-amber-500/40 text-[10px] text-amber-600"
          >
            执行中
          </Badge>
        )}
      </button>

      {hasBody && (
        <div
          className={cn(
            "grid transition-[grid-template-rows] duration-200 ease-out",
            expanded ? "grid-rows-[1fr]" : "grid-rows-[0fr]"
          )}
        >
          <div className="overflow-hidden">
            <div className="flex pt-2">
              <div className="flex min-w-0 flex-1 flex-col gap-3">
                {isRunning && !hasResult && (
                  <p className="text-xs text-muted-foreground">等待工具调用…</p>
                )}

                {hasResult && (
                  <div
                    className={cn(
                      "rounded-lg border bg-muted/40 px-3 py-2 text-sm",
                      isRunning && "animate-pulse"
                    )}
                  >
                    <MarkdownContent content={displayResult} />
                  </div>
                )}

                {hasError && (
                  <div className="rounded-lg border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm text-destructive">
                    {step.error}
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
