import type { TaskPlan, TaskStep } from "@/lib/types"

/** 步骤是否在 UI 中展示（跳过的旧步骤由重规划产生，不应占进度条） */
export function isVisiblePlanStep(step: TaskStep): boolean {
  return step.status !== "skipped"
}

/** 底部进度条 / 计划列表：只展示有效步骤 */
export function getVisiblePlanSteps(steps: TaskStep[]): TaskStep[] {
  return steps.filter(isVisiblePlanStep)
}

/**
 * 将单步 SSE 更新合并进规划步骤列表。
 * 已有 plan 时以 plan.steps 为权威来源，避免 step 事件把列表越叠越长。
 */
export function mergePlanStep(
  steps: TaskStep[],
  step: TaskStep,
  plan: TaskPlan | null
): TaskStep[] {
  const base = plan?.steps?.length ? plan.steps : steps
  const index = base.findIndex((item) => item.step_id === step.step_id)

  if (index === -1) {
    // 规划已下发后，忽略不在 plan 内的 stray step 事件
    if (plan?.steps?.length) {
      return base
    }
    return [...base, step]
  }

  const next = [...base]
  next[index] = { ...next[index], ...step }
  return next
}

/** 步骤状态中文标签（进度条副标题用，不展示 result 正文避免与聊天重复） */
export function getStepStatusLabel(status: string): string {
  switch (status) {
    case "pending":
      return "待执行"
    case "running":
    case "started":
      return "执行中"
    case "completed":
      return "已完成"
    case "failed":
      return "失败"
    case "skipped":
      return "已跳过"
    default:
      return status
  }
}
