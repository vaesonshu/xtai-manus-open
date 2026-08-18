"use client"

import type { ToolRecord } from "@/lib/types"
import { ToolDetailView } from "@/components/task/tool-use-inline"
import {
  getToolPanelTitle,
  getToolStatusLabel,
  pickToolIcon,
} from "@/lib/tool-display"
import { Badge } from "@workspace/ui/components/badge"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@workspace/ui/components/card"
import { cn } from "@workspace/ui/lib/utils"
import { Terminal, Wrench } from "lucide-react"

interface ToolPanelProps {
  tools: ToolRecord[]
  focusedToolId?: string | null
  className?: string
}

/** 右侧工具工作区：聚焦当前/最近一次工具调用 */
export function ToolPanel({ tools, focusedToolId, className }: ToolPanelProps) {
  const activeTool =
    (focusedToolId ? tools.find((t) => t.id === focusedToolId) : undefined) ??
    tools.find((t) => t.status === "calling") ??
    tools[tools.length - 1]

  return (
    <div
      className={cn(
        "flex h-full min-h-0 flex-col overflow-hidden p-4",
        className
      )}
    >
      <Card className="flex h-full min-h-0 flex-1 flex-col gap-0 border-dashed py-0">
        <CardHeader className="shrink-0 border-b border-border/40 pt-(--card-spacing) pb-(--card-spacing)">
          <div className="flex items-center gap-2">
            <Terminal className="size-4 text-muted-foreground" />
            <CardTitle className="text-sm">Manus 工作区</CardTitle>
          </div>
          <CardDescription className="text-xs">
            实时展示 Agent 工具调用与执行结果
          </CardDescription>
        </CardHeader>

        <CardContent className="flex min-h-0 flex-1 flex-col px-(--card-spacing) pt-3 pb-(--card-spacing)">
          {!activeTool ? (
            <div className="flex flex-1 flex-col items-center justify-center gap-2 rounded-lg border border-dashed bg-muted/30 text-xs text-muted-foreground">
              <Wrench className="size-5 opacity-40" />
              等待工具调用…
            </div>
          ) : (
            <ActiveToolView tool={activeTool} />
          )}
        </CardContent>
      </Card>
    </div>
  )
}

function ActiveToolView({ tool }: { tool: ToolRecord }) {
  const Icon = pickToolIcon(tool.functionName)

  return (
    <div className="flex h-full min-h-0 flex-col gap-3">
      <div className="flex shrink-0 items-center justify-between gap-2">
        <div className="flex min-w-0 items-center gap-2">
          <Icon className="size-4 shrink-0 text-muted-foreground" />
          <span className="truncate text-sm font-semibold">
            {getToolPanelTitle(tool)}
          </span>
        </div>
        <Badge
          variant="outline"
          className={cn(
            "h-5 shrink-0 border-0 text-[10px]",
            tool.status === "calling"
              ? "bg-amber-500/15 text-amber-600"
              : "bg-emerald-500/15 text-emerald-600"
          )}
        >
          {getToolStatusLabel(tool.status)}
        </Badge>
      </div>

      <div className="min-h-0 flex-1 overflow-hidden">
        <ToolDetailView tool={tool} fillHeight />
      </div>
    </div>
  )
}
