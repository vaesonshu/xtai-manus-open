"use client"

import type { HealthResponse } from "@/lib/types"
import type { TaskUiState } from "@/lib/types"
import { TaskStatusBadge } from "@/components/task/task-status-badge"
import { Button } from "@workspace/ui/components/button"
import { Separator } from "@workspace/ui/components/separator"
import { SidebarTrigger } from "@workspace/ui/components/sidebar"
import { PanelRight, RefreshCw } from "lucide-react"

interface TaskHeaderProps {
  state: Pick<TaskUiState, "title" | "goal" | "status" | "isStreaming">
  health: HealthResponse | null
  showToolPanel: boolean
  onToggleToolPanel: () => void
  onRefreshHealth: () => void
}

/** 顶栏：任务标题 + 状态 + 面板切换 */
export function TaskHeader({
  state,
  health,
  showToolPanel,
  onToggleToolPanel,
  onRefreshHealth,
}: TaskHeaderProps) {
  const title = state.title || state.goal || "XTAI Manus"

  return (
    <header className="flex h-14 shrink-0 items-center gap-3 border-b px-4">
      <SidebarTrigger className="-ml-1" aria-label="展开/收起侧栏" />

      <div className="min-w-0 flex-1">
        <h2 className="truncate text-sm font-medium">{title}</h2>
        <div className="flex items-center gap-2 text-[11px] text-muted-foreground">
          <TaskStatusBadge
            status={state.status}
            className="h-4 px-1.5 text-[10px]"
          />
          {health?.service && (
            <>
              <span>·</span>
              <span className="truncate">{health.service}</span>
            </>
          )}
          {state.status === "waiting" && (
            <span className="text-amber-600 dark:text-amber-400">· 等待回复</span>
          )}
          {state.isStreaming && state.status !== "waiting" && (
            <span className="text-amber-600 dark:text-amber-400">
              · 流式接收中
            </span>
          )}
        </div>
      </div>

      <div className="flex items-center gap-1">
        <Button
          variant="ghost"
          size="icon-sm"
          onClick={onRefreshHealth}
          aria-label="刷新状态"
        >
          <RefreshCw className="size-3.5" />
        </Button>
        <Button
          variant={showToolPanel ? "secondary" : "ghost"}
          size="icon-sm"
          onClick={onToggleToolPanel}
          aria-label={showToolPanel ? "关闭工具工作区" : "打开工具工作区"}
          aria-pressed={showToolPanel}
        >
          <PanelRight className="size-4" />
        </Button>
      </div>

      <Separator orientation="vertical" className="hidden h-6 lg:block" />
    </header>
  )
}
