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
import {
  initialTaskUiState,
  taskReducer,
} from "@/lib/task-reducer"
import type { StreamEvent, TaskSessionMeta } from "@/lib/types"

/** 任务会话 hook：封装创建、SSE 订阅、回复与本地持久化 */
export function useTaskSession(taskId: string | null) {
  const [state, dispatch] = useReducer(taskReducer, initialTaskUiState)
  const [sessions, setSessions] = useState<TaskSessionMeta[]>([])
  const streamGeneration = useRef(0)

  const refreshSessions = useCallback(() => {
    setSessions(loadTaskSessions())
  }, [])

  const persistMeta = useCallback(
    (next: {
      taskId: string
      goal: string
      title?: string
      status: typeof state.status
    }) => {
      upsertTaskSession(buildTaskMeta(next))
      refreshSessions()
    },
    [refreshSessions]
  )

  const connectStream = useCallback((id: string) => {
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

    return close
  }, [])

  /** 加载已有任务并订阅 SSE */
  useEffect(() => {
    if (!taskId) {
      dispatch({ type: "RESET" })
      return
    }

    let cancelled = false
    let closeStream: (() => void) | undefined

    void (async () => {
      try {
        const task = await getTask(taskId)
        if (cancelled) {
          return
        }

        dispatch({ type: "HYDRATE_TASK", task })
        persistMeta({
          taskId: task.task_id,
          goal: task.goal,
          title: task.plan?.title,
          status: task.status,
        })

        closeStream = connectStream(taskId)
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
      closeStream?.()
    }
  }, [taskId, connectStream, persistMeta])

  /** 状态变化时同步本地列表 */
  useEffect(() => {
    if (!state.taskId) {
      return
    }

    persistMeta({
      taskId: state.taskId,
      goal: state.goal,
      title: state.title,
      status: state.status,
    })
  }, [state.taskId, state.goal, state.title, state.status, persistMeta])

  const startTask = useCallback(
    async (goal: string) => {
      const task = await createTask(goal)
      persistMeta({
        taskId: task.task_id,
        goal: task.goal,
        status: task.status,
      })
      return task.task_id
    },
    [persistMeta]
  )

  const sendReply = useCallback(
    async (content: string) => {
      if (!taskId) {
        return
      }

      dispatch({ type: "ADD_USER_MESSAGE", content })

      await replyTask(taskId, content)
      connectStream(taskId)
    },
    [taskId, connectStream]
  )

  return {
    state,
    sessions,
    refreshSessions,
    startTask,
    sendReply,
  }
}
