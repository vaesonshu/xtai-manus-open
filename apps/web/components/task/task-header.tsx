"use client"

import type { HealthResponse } from "@/lib/types"
import type { TaskUiState } from "@/lib/types"
import { TaskStatusBadge } from "@/components/task/task-sidebar"
import { Badge } from "@workspace/ui/components/badge"
import { Button } from "@workspace/ui/components/button"
import { SidebarTrigger } from "@workspace/ui/components/sidebar"
import { cn } from "@workspace/ui/lib/utils"
import {
  ActivityIcon,
  PanelRightIcon,
  RefreshCwIcon,
} from "lucide-react"

interface TaskHeaderProps {
  state: Pick<TaskUiState, "title" | "goal" | "status" | "isStreaming">
  health: HealthResponse | null
  showToolPanel: boolean
  onToggleToolPanel: () => void
  onRefreshHealth: () => void
}

/** 顶栏：标题、状态、健康检查与工具面板开关 */
export function TaskHeader({
  state,
  health,
  showToolPanel,
  onToggleToolPanel,
  onRefreshHealth,
}: TaskHeaderProps) {
  const title = state.title || state.goal || "新任务"

  return (
    <header className="flex h-14 shrink-0 items-center gap-2 border-b border-border/60 px-3">
      <SidebarTrigger />

      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <h1 className="truncate text-sm font-medium">{title}</h1>
          <TaskStatusBadge status={state.status} />
          {state.isStreaming ? (
            <Badge variant="outline" className="text-[10px]">
              流式接收中
            </Badge>
          ) : null}
        </div>
        {state.goal && state.title ? (
          <p className="text-muted-foreground truncate text-xs">
            {state.goal}
          </p>
        ) : null}
      </div>

      <div className="flex items-center gap-1">
        <Button
          type="button"
          size="icon-sm"
          variant="ghost"
          onClick={onRefreshHealth}
          aria-label="刷新健康状态"
        >
          <RefreshCwIcon />
        </Button>

        <Badge
          variant={health?.status === "ok" ? "secondary" : "outline"}
          className={cn(
            "hidden gap-1 sm:inline-flex",
            health?.status !== "ok" && "text-amber-600"
          )}
        >
          <ActivityIcon className="size-3" />
          {health?.status === "ok" ? "服务正常" : "服务异常"}
        </Badge>

        <Button
          type="button"
          size="icon-sm"
          variant={showToolPanel ? "secondary" : "ghost"}
          onClick={onToggleToolPanel}
          aria-label="切换工具面板"
        >
          <PanelRightIcon />
        </Button>
      </div>
    </header>
  )
}
