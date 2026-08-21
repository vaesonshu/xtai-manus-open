"use client"

import { useCallback, useEffect, useRef, useState } from "react"

import { PlanStepsBar } from "@/components/task/plan-steps-bar"
import { TaskComposer } from "@/components/task/task-composer"
import { TaskHeader } from "@/components/task/task-header"
import { TaskSidebar } from "@/components/task/task-sidebar"
import { TaskTimeline } from "@/components/task/task-timeline"
import { ToolPanel } from "@/components/task/tool-panel"
import { WelcomeScreen } from "@/components/task/welcome-screen"
import { fetchHealth } from "@/lib/api-client"
import type { HealthResponse, ToolRecord } from "@/lib/types"
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

/** 右侧工具工作区宽度（桌面端） */
const TOOL_PANEL_WIDTH = "600px"

interface TaskShellProps {
  taskId?: string | null
  onTaskCreated?: (taskId: string) => void
}

/** Manus 风格主界面：侧栏 + 聊天区 + 工具工作区 */
export function TaskShell({ taskId = null, onTaskCreated }: TaskShellProps) {
  const isMobile = useIsMobile()
  const {
    state,
    sessions,
    sessionTaskId,
    refreshSessions,
    startTask,
    sendReply,
  } = useTaskSession(taskId)

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

  const toolActivityKey = state.tools
    .map((tool) => `${tool.id}:${tool.status}`)
    .join("|")
  const toolsRef = useRef(state.tools)
  toolsRef.current = state.tools

  useEffect(() => {
    refreshSessions()
  }, [refreshSessions])

  useEffect(() => {
    const tools = toolsRef.current
    if (tools.length === 0) {
      return
    }

    const callingTool = tools.find((tool) => tool.status === "calling")
    if (callingTool) {
      setSelectedToolId(callingTool.id)
      setShowToolPanel(true)
      return
    }

    // 已有工具则打开面板；用户点选过的工具保持选中，实现左右一一对应
    setShowToolPanel(true)
    setSelectedToolId((prev) => {
      if (prev && tools.some((tool) => tool.id === prev)) {
        return prev
      }
      return tools[tools.length - 1]?.id ?? null
    })
    // 只依赖固定长度的字符串，避免 React Compiler 把 tools[] 展开进 deps
  }, [toolActivityKey])

  useEffect(() => {
    setSelectedToolId(null)
    setShowToolPanel(false)
  }, [sessionTaskId])

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

  const handleToolSelect = useCallback((tool: ToolRecord) => {
    setSelectedToolId(tool.id)
    setShowToolPanel(true)
  }, [])

  const canReply = Boolean(sessionTaskId) && state.status === "waiting"
  // 任务结束后允许继续输入（创建新任务），仅执行中禁用
  const canStartFollowUp =
    Boolean(sessionTaskId) &&
    (state.status === "completed" ||
      state.status === "failed" ||
      state.status === "cancelled")
  const composerDisabled =
    Boolean(sessionTaskId) && !canReply && !canStartFollowUp
  const showPlanBar = state.steps.length > 0 || Boolean(state.title)
  const showWelcome = !sessionTaskId && state.timeline.length === 0 && !creating

  const toolPanelContent = (
    <ToolPanel tools={state.tools} focusedToolId={focusedToolId} />
  )

  return (
    <SidebarProvider defaultOpen>
      <TaskSidebar
        sessions={sessions}
        activeTaskId={sessionTaskId}
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
            {showWelcome ? (
              <WelcomeScreen loading={creating} onSubmit={handleCreate} />
            ) : (
              <>
                <div className="min-h-0 flex-1 overflow-hidden">
                  <TaskTimeline
                    className="h-full"
                    state={state}
                    selectedToolId={focusedToolId}
                    onToolSelect={handleToolSelect}
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
                  ) : (
                    <TaskComposer
                      mode={
                        canStartFollowUp || !sessionTaskId ? "create" : "reply"
                      }
                      loading={creating || state.isStreaming}
                      disabled={composerDisabled}
                      placeholder={
                        canStartFollowUp
                          ? "任务已结束，描述新任务继续…"
                          : composerDisabled
                            ? "Agent 正在执行任务，等待向你提问时可在此回复"
                            : undefined
                      }
                      onSubmit={
                        canStartFollowUp || !sessionTaskId
                          ? handleCreate
                          : handleReply
                      }
                    />
                  )}
                </div>
              </>
            )}
          </main>

          {!isMobile && (
            <aside
              aria-hidden={!showToolPanel}
              style={{ width: showToolPanel ? TOOL_PANEL_WIDTH : 0 }}
              className={cn(
                "hidden h-full min-h-0 shrink-0 overflow-hidden border-l bg-sidebar/30 transition-[width,border-color] duration-300 ease-in-out lg:flex",
                showToolPanel ? "border-border" : "border-transparent"
              )}
            >
              <div
                className="h-full shrink-0"
                style={{ width: TOOL_PANEL_WIDTH }}
              >
                <div
                  className={cn(
                    "h-full transition-opacity duration-200 ease-in-out",
                    showToolPanel
                      ? "opacity-100 delay-100"
                      : "pointer-events-none opacity-0"
                  )}
                >
                  {toolPanelContent}
                </div>
              </div>
            </aside>
          )}
        </div>
      </SidebarInset>

      {isMobile ? (
        <Sheet open={showToolPanel} onOpenChange={setShowToolPanel}>
          <SheetContent side="right" className="w-full p-0 sm:max-w-2xl">
            <SheetHeader className="border-b px-4 py-3">
              <SheetTitle className="text-sm">工具工作区</SheetTitle>
            </SheetHeader>
            <div className="h-[calc(100%-3.5rem)] min-h-0 overflow-hidden">
              {toolPanelContent}
            </div>
          </SheetContent>
        </Sheet>
      ) : null}
    </SidebarProvider>
  )
}
