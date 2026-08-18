"use client"

import type { TaskUiState } from "@/lib/types"
import { Alert, AlertDescription, AlertTitle } from "@workspace/ui/components/alert"
import { cn } from "@workspace/ui/lib/utils"
import { AlertCircleIcon, CheckCircle2Icon, MessageCircleIcon } from "lucide-react"

interface StatusBannerProps {
  state: Pick<
    TaskUiState,
    "status" | "error" | "waitQuestion" | "waitReason"
  >
  className?: string
}

/** 等待回复 / 完成 / 错误 状态横幅 */
export function StatusBanner({ state, className }: StatusBannerProps) {
  if (state.status === "waiting") {
    return (
      <Alert className={cn("mx-auto max-w-3xl", className)}>
        <MessageCircleIcon />
        <AlertTitle>等待你的回复</AlertTitle>
        <AlertDescription>
          {state.waitQuestion ||
            state.waitReason ||
            "智能体需要你补充信息后才能继续。"}
        </AlertDescription>
      </Alert>
    )
  }

  if (state.status === "failed" && state.error) {
    return (
      <Alert variant="destructive" className={cn("mx-auto max-w-3xl", className)}>
        <AlertCircleIcon />
        <AlertTitle>任务失败</AlertTitle>
        <AlertDescription>{state.error}</AlertDescription>
      </Alert>
    )
  }

  if (state.status === "completed") {
    return (
      <Alert className={cn("mx-auto max-w-3xl border-emerald-500/30", className)}>
        <CheckCircle2Icon className="text-emerald-500" />
        <AlertTitle>任务已完成</AlertTitle>
        <AlertDescription>所有步骤已执行完毕。</AlertDescription>
      </Alert>
    )
  }

  return null
}
