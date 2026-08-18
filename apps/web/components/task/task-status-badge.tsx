"use client"

import type { TaskStatus } from "@/lib/types"
import { Badge } from "@workspace/ui/components/badge"
import { cn } from "@workspace/ui/lib/utils"

const statusLabel: Record<TaskStatus, string> = {
  created: "已创建",
  running: "执行中",
  waiting: "等待回复",
  completed: "已完成",
  failed: "失败",
  cancelled: "已取消",
}

/** 任务状态徽章 */
export function TaskStatusBadge({
  status,
  className,
}: {
  status: TaskStatus
  className?: string
}) {
  const variant =
    status === "failed"
      ? "destructive"
      : status === "completed"
        ? "secondary"
        : status === "waiting"
          ? "outline"
          : "default"

  return (
    <Badge variant={variant} className={cn("text-[10px]", className)}>
      {statusLabel[status] ?? status}
    </Badge>
  )
}
