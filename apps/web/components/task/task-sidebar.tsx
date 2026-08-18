"use client"

import Link from "next/link"
import { useRouter } from "next/navigation"
import { useCallback, useState } from "react"

import { removeTaskSession } from "@/lib/task-storage"
import type { TaskSessionMeta, TaskStatus } from "@/lib/types"
import { Badge } from "@workspace/ui/components/badge"
import { Button } from "@workspace/ui/components/button"
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuAction,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@workspace/ui/components/sidebar"
import { cn } from "@workspace/ui/lib/utils"
import { PlusIcon, SettingsIcon, Trash2Icon } from "lucide-react"

const statusLabel: Record<TaskStatus, string> = {
  created: "已创建",
  running: "执行中",
  waiting: "等待回复",
  completed: "已完成",
  failed: "失败",
  cancelled: "已取消",
}

interface TaskSidebarProps {
  sessions: TaskSessionMeta[]
  activeTaskId?: string | null
  onRefresh: () => void
}

/** 左侧任务历史侧栏 */
export function TaskSidebar({
  sessions,
  activeTaskId,
  onRefresh,
}: TaskSidebarProps) {
  const router = useRouter()

  const handleDelete = useCallback(
    (taskId: string) => {
      removeTaskSession(taskId)
      onRefresh()
      if (activeTaskId === taskId) {
        router.push("/")
      }
    },
    [activeTaskId, onRefresh, router]
  )

  return (
    <Sidebar collapsible="icon">
      <SidebarHeader className="border-b border-border/60 p-3">
        <div className="flex items-center justify-between gap-2">
          <div className="min-w-0">
            <p className="truncate text-sm font-semibold">XTAI Manus</p>
            <p className="text-muted-foreground truncate text-xs">
              自主智能体工作台
            </p>
          </div>
          <Button
            size="icon-sm"
            variant="outline"
            onClick={() => router.push("/")}
            aria-label="新建任务"
          >
            <PlusIcon />
          </Button>
        </div>
      </SidebarHeader>

      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel>任务历史</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {sessions.length === 0 ? (
                <p className="text-muted-foreground px-2 py-4 text-xs">
                  暂无任务，从首页创建第一个目标。
                </p>
              ) : (
                sessions.map((session) => (
                  <SidebarMenuItem key={session.taskId}>
                    <SidebarMenuButton
                      isActive={session.taskId === activeTaskId}
                      onClick={() => router.push(`/tasks/${session.taskId}`)}
                    >
                      <span className="truncate">{session.title}</span>
                    </SidebarMenuButton>
                    <SidebarMenuAction
                      showOnHover
                      onClick={() => handleDelete(session.taskId)}
                      aria-label="删除任务记录"
                    >
                      <Trash2Icon />
                    </SidebarMenuAction>
                  </SidebarMenuItem>
                ))
              )}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>

      <SidebarFooter className="border-t border-border/60 p-2">
        <Link href="/settings">
          <Button variant="ghost" className="w-full justify-start">
            <SettingsIcon />
            设置
          </Button>
        </Link>
      </SidebarFooter>
    </Sidebar>
  )
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
