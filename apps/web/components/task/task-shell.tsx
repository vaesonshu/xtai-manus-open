"use client"

import { useCallback, useEffect, useState } from "react"

import { PlanStepsBar } from "@/components/task/plan-steps-bar"
import { StatusBanner } from "@/components/task/status-banner"
import { TaskComposer } from "@/components/task/task-composer"
import { TaskHeader } from "@/components/task/task-header"
import { TaskSidebar } from "@/components/task/task-sidebar"
import { TaskTimeline, ToolPanel } from "@/components/task/task-timeline"
import { WelcomeScreen } from "@/components/task/welcome-screen"
import { fetchHealth } from "@/lib/api-client"
import type { HealthResponse } from "@/lib/types"
import { useTaskSession } from "@/hooks/use-task-session"
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@workspace/ui/components/sheet"
import { SidebarInset, SidebarProvider } from "@workspace/ui/components/sidebar"
import { useIsMobile } from "@workspace/ui/hooks/use-mobile"
import { cn } from "@workspace/ui/lib/utils"

const TOOL_PANEL_WIDTH = "420px"

interface TaskShellProps {
  taskId?: string | null
  onTaskCreated?: (taskId: string) => void
}

/** Manus 风格主界面：侧栏 + 聊天区 + 工具工作区 */
export function TaskShell({ taskId = null, onTaskCreated }: TaskShellProps) {
  const isMobile = useIsMobile()
  const { state, sessions, refreshSessions, startTask, sendReply } =
    useTaskSession(taskId)

  const [health, setHealth] = useState<HealthResponse | null>(null)
  const [showToolPanel, setShowToolPanel] = useState(false)
  const [selectedToolId, setSelectedToolId] = useState<string | null>(null)
  const [creating, setCreating] = useState(false)

  const callingToolId =
    state.tools.find((tool) => tool.status === "calling")?.id ?? null

  const focusedToolId =
    selectedToolId ??
    callingToolId ??
    state.tools[state.tools.length - 1]?.id ??
    null

  useEffect(() => {
    refreshSessions()
  }, [refreshSessions])

  useEffect(() => {
    if (callingToolId) {
      setSelectedToolId(callingToolId)
      setShowToolPanel(true)
    }
  }, [callingToolId])

  useEffect(() => {
    setSelectedToolId(null)
    setShowToolPanel(false)
  }, [taskId])

  const refreshHealth = useCallback(async () => {
    try {
      setHealth(await fetchHealth())
    } catch {
      setHealth(null)
    }
  }, [])

  useEffect(() => {
    void refreshHealth()
  }, [refreshHealth])

  const handleCreate = useCallback(
    async (goal: string) => {
      setCreating(true)
      try {
        const newTaskId = await startTask(goal)
        onTaskCreated?.(newTaskId)
      } finally {
        setCreating(false)
      }
    },
    [onTaskCreated, startTask]
  )

  const handleReply = useCallback(
    async (content: string) => {
      await sendReply(content)
    },
    [sendReply]
  )

  const isWaiting = state.status === "waiting"
  const canReply = Boolean(taskId) && isWaiting
  const showPlanBar = state.steps.length > 0 || Boolean(state.title)

  return (
    <SidebarProvider defaultOpen>
      <TaskSidebar
        sessions={sessions}
        activeTaskId={taskId}
        onRefresh={refreshSessions}
      />

      <SidebarInset className="flex h-svh flex-col overflow-hidden">
        <TaskHeader
          state={state}
          health={health}
          showToolPanel={showToolPanel}
          onToggleToolPanel={() => setShowToolPanel((value) => !value)}
          onRefreshHealth={() => void refreshHealth()}
        />

        <div className="flex min-h-0 flex-1 overflow-hidden">
          <main className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden">
            {!taskId ? (
              <WelcomeScreen loading={creating} onSubmit={handleCreate} />
            ) : (
              <>
                <div className="min-h-0 flex-1 overflow-hidden">
                  <div className="space-y-3 px-4 pt-3">
                    <StatusBanner state={state} />
                  </div>
                  <TaskTimeline
                    className="h-[calc(100%-0.5rem)]"
                    timeline={state.timeline}
                    isStreaming={state.isStreaming}
                    selectedToolId={focusedToolId}
                    onToolSelect={(toolId) => {
                      setSelectedToolId(toolId)
                      setShowToolPanel(true)
                    }}
                  />
                </div>

                <div className="shrink-0">
                  {showPlanBar ? (
                    <PlanStepsBar title={state.title} steps={state.steps} />
                  ) : null}

                  {canReply ? (
                    <TaskComposer
                      mode="reply"
                      loading={state.isStreaming}
                      onSubmit={handleReply}
                    />
                  ) : null}
                </div>
              </>
            )}
          </main>

          {!isMobile && showToolPanel ? (
            <div
              className="hidden shrink-0 md:block"
              style={{ width: TOOL_PANEL_WIDTH }}
            >
              <ToolPanel tools={state.tools} focusedToolId={focusedToolId} />
            </div>
          ) : null}
        </div>
      </SidebarInset>

      {isMobile ? (
        <Sheet open={showToolPanel} onOpenChange={setShowToolPanel}>
          <SheetContent side="right" className="w-full p-0 sm:max-w-md">
            <SheetHeader className="border-b border-border/60 p-4">
              <SheetTitle>工具工作区</SheetTitle>
            </SheetHeader>
            <ToolPanel
              tools={state.tools}
              focusedToolId={focusedToolId}
              className={cn("border-0")}
            />
          </SheetContent>
        </Sheet>
      ) : null}
    </SidebarProvider>
  )
}
