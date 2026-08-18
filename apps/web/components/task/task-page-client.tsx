"use client"

import { TaskShell } from "@/components/task/task-shell"

/** 任务详情页客户端容器 */
export function TaskPageClient({ taskId }: { taskId: string }) {
  return <TaskShell taskId={taskId} />
}
