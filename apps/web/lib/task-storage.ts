import type { TaskSessionMeta, TaskStatus } from "@/lib/types"

const STORAGE_KEY = "xtai:tasks:v1"

/** 读取本地任务列表（按更新时间倒序） */
export function loadTaskSessions(): TaskSessionMeta[] {
  if (typeof window === "undefined") {
    return []
  }

  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) {
      return []
    }
    const parsed = JSON.parse(raw) as TaskSessionMeta[]
    return [...parsed].sort(
      (a, b) =>
        new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime()
    )
  } catch {
    return []
  }
}

/** 写入或更新任务元数据 */
export function upsertTaskSession(
  meta: TaskSessionMeta,
  options?: { bumpUpdatedAt?: boolean }
): void {
  if (typeof window === "undefined") {
    return
  }

  const sessions = loadTaskSessions()
  const existing = sessions.find((item) => item.taskId === meta.taskId)
  const filtered = sessions.filter((item) => item.taskId !== meta.taskId)

  const bumpUpdatedAt = options?.bumpUpdatedAt ?? true
  const updatedAt = bumpUpdatedAt
    ? meta.updatedAt || new Date().toISOString()
    : existing?.updatedAt || meta.updatedAt || new Date().toISOString()

  const merged: TaskSessionMeta = {
    ...meta,
    updatedAt,
  }

  // 不在此处 unshift：顺序由 updatedAt 决定，避免仅查看任务时被顶到最前
  filtered.push(merged)

  const limited = filtered
    .sort(
      (a, b) =>
        new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime()
    )
    .slice(0, 50)

  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(limited))
  } catch {
    // 隐私模式或配额不足时静默失败
  }
}

/** 删除本地任务记录 */
export function removeTaskSession(taskId: string): void {
  if (typeof window === "undefined") {
    return
  }

  const sessions = loadTaskSessions().filter((item) => item.taskId !== taskId)

  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(sessions))
  } catch {
    // ignore
  }
}

/** 构造任务元数据 */
export function buildTaskMeta(input: {
  taskId: string
  goal: string
  title?: string
  status: TaskStatus
}): TaskSessionMeta {
  return {
    taskId: input.taskId,
    goal: input.goal,
    title: input.title || input.goal.slice(0, 40),
    status: input.status,
    updatedAt: new Date().toISOString(),
  }
}
