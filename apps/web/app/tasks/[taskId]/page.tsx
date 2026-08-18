import { TaskPageClient } from "@/components/task/task-page-client"

interface TaskPageProps {
  params: Promise<{ taskId: string }>
}

/** 任务会话页：SSE 实时流 + 步骤/工具面板 */
export default async function TaskPage({ params }: TaskPageProps) {
  const { taskId } = await params
  return <TaskPageClient taskId={taskId} />
}
