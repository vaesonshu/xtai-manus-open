"use client"

import Link from "next/link"
import { useRouter } from "next/navigation"
import { useCallback } from "react"

import { TaskStatusBadge } from "@/components/task/task-status-badge"
import { removeTaskSession } from "@/lib/task-storage"
import type { TaskSessionMeta } from "@/lib/types"
import { Button } from "@workspace/ui/components/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@workspace/ui/components/dropdown-menu"
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@workspace/ui/components/sidebar"
import { Bot, MoreHorizontal, Plus, Settings, Trash2 } from "lucide-react"

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
    <Sidebar collapsible="offcanvas" className="border-r">
      <SidebarHeader className="border-b px-3 py-3">
        <div className="flex items-center gap-2 px-1">
          <div className="flex size-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
            <Bot className="size-4" />
          </div>
          <div>
            <p className="text-sm font-semibold">XTAI Manus</p>
            <p className="text-[11px] text-muted-foreground">LangGraph Agent</p>
          </div>
        </div>
        <Button
          className="mt-3 w-full justify-start gap-2"
          size="sm"
          onClick={() => router.push("/")}
        >
          <Plus className="size-4" />
          新建任务
        </Button>
      </SidebarHeader>

      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel>历史任务</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {sessions.length === 0 ? (
                <p className="px-3 py-2 text-xs text-muted-foreground">
                  暂无历史，开始第一个任务吧
                </p>
              ) : (
                sessions.map((session) => (
                  <SessionMenuItem
                    key={session.taskId}
                    session={session}
                    isActive={session.taskId === activeTaskId}
                    onSelect={() => router.push(`/tasks/${session.taskId}`)}
                    onDelete={() => handleDelete(session.taskId)}
                  />
                ))
              )}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>

      <SidebarFooter className="space-y-2 border-t p-3">
        <Link href="/settings">
          <Button variant="ghost" className="w-full justify-start gap-2">
            <Settings className="size-4" />
            设置
          </Button>
        </Link>
        <p className="text-[10px] leading-relaxed text-muted-foreground">
          按 <kbd className="rounded bg-muted px-1">D</kbd> 切换主题 ·{" "}
          <kbd className="rounded bg-muted px-1">Ctrl+B</kbd> 切换侧栏
        </p>
      </SidebarFooter>
    </Sidebar>
  )
}

function SessionMenuItem({
  session,
  isActive,
  onSelect,
  onDelete,
}: {
  session: TaskSessionMeta
  isActive: boolean
  onSelect: () => void
  onDelete: () => void
}) {
  return (
    <SidebarMenuItem>
      <div className="flex w-full min-w-0 items-stretch gap-0.5">
        <SidebarMenuButton
          isActive={isActive}
          onClick={onSelect}
          className="h-auto min-h-9 min-w-0 flex-1 py-2"
        >
          <div className="flex min-w-0 flex-1 flex-col gap-1">
            <span className="truncate text-left text-sm leading-none">
              {session.title}
            </span>
            <TaskStatusBadge
              status={session.status}
              className="h-4 w-fit px-1.5 text-[9px]"
            />
          </div>
        </SidebarMenuButton>

        <DropdownMenu>
          <DropdownMenuTrigger
            render={
              <Button
                variant="ghost"
                size="icon-xs"
                className="mt-1 shrink-0 text-muted-foreground opacity-70 hover:opacity-100"
                onClick={(e) => e.stopPropagation()}
                aria-label="任务操作"
              >
                <MoreHorizontal className="size-3.5" />
              </Button>
            }
          />
          <DropdownMenuContent align="end">
            <DropdownMenuItem
              variant="destructive"
              onClick={(e) => {
                e.stopPropagation()
                onDelete()
              }}
            >
              <Trash2 className="size-3.5" />
              删除
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </SidebarMenuItem>
  )
}
