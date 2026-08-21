"use client"

import { useCallback, useEffect, useReducer, useRef, useState } from "react"

import {
  createTask,
  getTask,
  replyTask,
  subscribeTaskStream,
} from "@/lib/api-client"
import {
  buildTaskMeta,
  loadTaskSessions,
  upsertTaskSession,
} from "@/lib/task-storage"
import { initialTaskUiState, taskReducer } from "@/lib/task-reducer"
import type { StreamEvent, TaskSessionMeta } from "@/lib/types"

/** 任务会话 hook：封装创建、SSE 订阅、回复与本地持久化 */
export function useTaskSession(taskId: string | null) {
  const [state, dispatch] = useReducer(taskReducer, initialTaskUiState)
  const [sessions, setSessions] = useState<TaskSessionMeta[]>([])
  const [sessionTaskId, setSessionTaskId] = useState<string | null>(null)
  const [isPendingCreate, setIsPendingCreate] = useState(false)
  const streamGeneration = useRef(0)
  const streamCloseRef = useRef<(() => void) | null>(null)

  // 路由 taskId 与新建任务时的本地 id 合并，避免首页提交后被 RESET 清掉乐观状态
  const resolvedTaskId = taskId ?? sessionTaskId

  const refreshSessions = useCallback(() => {
    setSessions(loadTaskSessions())
  }, [])

  const persistMeta = useCallback(
    (
      next: {
        taskId: string
        goal: string
        title?: string
        status: typeof state.status
      },
      options?: { bumpUpdatedAt?: boolean }
    ) => {
      upsertTaskSession(buildTaskMeta(next), {
        bumpUpdatedAt: options?.bumpUpdatedAt ?? true,
      })
      refreshSessions()
    },
    [refreshSessions]
  )

  const connectStream = useCallback((id: string) => {
    streamCloseRef.current?.()
    streamGeneration.current += 1
    const generation = streamGeneration.current

    dispatch({ type: "SET_STREAMING", value: true })

    const close = subscribeTaskStream(
      id,
      (raw) => {
        if (generation !== streamGeneration.current) {
          return
        }
        dispatch({ type: "APPLY_EVENT", event: raw as StreamEvent })
      },
      () => {
        if (generation === streamGeneration.current) {
          dispatch({ type: "SET_STREAMING", value: false })
        }
      }
    )

    streamCloseRef.current = close
    return close
  }, [])

  /** 路由切换时同步 sessionTaskId，避免返回首页后仍挂着旧任务流 */
  useEffect(() => {
    if (taskId) {
      setSessionTaskId(taskId)
    } else {
      setSessionTaskId(null)
    }
  }, [taskId])

  /** 加载已有任务：先连 SSE，再并行 hydrate，避免等 GET 阻塞实时展示 */
  useEffect(() => {
    if (!resolvedTaskId) {
      if (isPendingCreate) {
        return
      }
      dispatch({ type: "RESET" })
      return
    }

    let cancelled = false
    const closeStream = connectStream(resolvedTaskId)

    void (async () => {
      try {
        const task = await getTask(resolvedTaskId)
        if (cancelled) {
          return
        }

        dispatch({ type: "HYDRATE_TASK", task })
      } catch {
        if (!cancelled) {
          dispatch({
            type: "APPLY_EVENT",
            event: {
              id: "load-error",
              type: "error",
              created_at: new Date().toISOString(),
              error: "无法加载任务，请确认后端已启动",
            },
          })
        }
      }
    })()

    return () => {
      cancelled = true
      closeStream()
      streamCloseRef.current = null
    }
  }, [resolvedTaskId, isPendingCreate, connectStream, persistMeta])

  /** 状态变化时同步本地列表（仅在有实质更新或执行中时提升排序） */
  useEffect(() => {
    if (!state.taskId) {
      return
    }

    const existing = loadTaskSessions().find(
      (item) => item.taskId === state.taskId
    )
    const metadataChanged =
      existing != null &&
      (existing.status !== state.status ||
        (state.title && existing.title !== state.title))

    persistMeta(
      {
        taskId: state.taskId,
        goal: state.goal,
        title: state.title,
        status: state.status,
      },
      {
        bumpUpdatedAt: state.isStreaming || metadataChanged,
      }
    )
  }, [
    state.taskId,
    state.goal,
    state.title,
    state.status,
    state.isStreaming,
    persistMeta,
  ])

  const startTask = useCallback(
    async (goal: string) => {
      dispatch({ type: "START_TASK", goal })
      setIsPendingCreate(true)

      try {
        const task = await createTask(goal)
        dispatch({
          type: "TASK_CREATED",
          taskId: task.task_id,
          status: task.status,
        })
        setSessionTaskId(task.task_id)
        persistMeta(
          {
            taskId: task.task_id,
            goal: task.goal,
            status: task.status,
          },
          { bumpUpdatedAt: true }
        )
        return task.task_id
      } catch (error) {
        dispatch({
          type: "APPLY_EVENT",
          event: {
            id: "create-error",
            type: "error",
            created_at: new Date().toISOString(),
            error:
              error instanceof Error ? error.message : "创建任务失败，请重试",
          },
        })
        throw error
      } finally {
        setIsPendingCreate(false)
      }
    },
    [persistMeta]
  )

  const sendReply = useCallback(
    async (content: string) => {
      if (!resolvedTaskId) {
        return
      }

      dispatch({ type: "ADD_USER_MESSAGE", content })
      // 先连 SSE 再 POST reply，避免执行期间错过实时事件
      connectStream(resolvedTaskId)
      await replyTask(resolvedTaskId, content)
    },
    [resolvedTaskId, connectStream]
  )

  return {
    state,
    sessions,
    sessionTaskId: resolvedTaskId,
    refreshSessions,
    startTask,
    sendReply,
  }
}
