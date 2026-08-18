"use client"

import { useRouter } from "next/navigation"

import { TaskShell } from "@/components/task/task-shell"

/** 首页：新建任务入口 */
export function HomePageClient() {
  const router = useRouter()

  return (
    <TaskShell
      onTaskCreated={(taskId) => {
        router.push(`/tasks/${taskId}`)
      }}
    />
  )
}
