"use client"

import { useState } from "react"

import type { TaskStep } from "@/lib/types"
import { getStepStatusLabel, getVisiblePlanSteps } from "@/lib/plan-steps"
import { Badge } from "@workspace/ui/components/badge"
import { Button } from "@workspace/ui/components/button"
import { Progress } from "@workspace/ui/components/progress"
import { cn } from "@workspace/ui/lib/utils"
import {
  CheckCircle2Icon,
  ChevronDownIcon,
  Loader2Icon,
  XCircleIcon,
} from "lucide-react"

function countCompleted(steps: TaskStep[]): number {
  return steps.filter(
    (step) => step.status === "completed" || step.success
  ).length
}

function StepIcon({ step, index }: { step: TaskStep; index: number }) {
  if (step.status === "completed" || step.success) {
    return <CheckCircle2Icon className="size-3.5 text-emerald-500" />
  }
  if (step.status === "failed") {
    return <XCircleIcon className="size-3.5 text-destructive" />
  }
  if (step.status === "running") {
    return <Loader2Icon className="size-3.5 animate-spin text-amber-500" />
  }
  return (
    <span className="text-muted-foreground flex size-3.5 items-center justify-center text-[9px] font-medium">
      {index + 1}
    </span>
  )
}

interface PlanStepsBarProps {
  title: string
  steps: TaskStep[]
  className?: string
}

/** 输入框上方的可折叠步骤进度条 */
export function PlanStepsBar({ title, steps, className }: PlanStepsBarProps) {
  const [expanded, setExpanded] = useState(true)
  const visibleSteps = getVisiblePlanSteps(steps)

  const total = visibleSteps.length
  const done = countCompleted(visibleSteps)
  const pct = total ? Math.round((done / total) * 100) : 0

  if (total === 0 && !title) {
    return null
  }

  return (
    <div className={cn("px-4 pb-1 pt-2", className)}>
      <div className="mx-auto max-w-3xl overflow-hidden rounded-lg border border-border/50 bg-muted/15">
        <Button
          type="button"
          variant="ghost"
          className="h-8 w-full justify-between rounded-none px-2.5 hover:bg-muted/25"
          onClick={() => setExpanded((value) => !value)}
          aria-expanded={expanded}
        >
          <span className="flex min-w-0 items-center gap-2">
            <ChevronDownIcon
              className={cn(
                "text-muted-foreground size-3.5 shrink-0 transition-transform",
                expanded && "rotate-180"
              )}
            />
            <span className="truncate text-xs font-medium">
              {title || "任务计划"}
            </span>
          </span>
          <Badge variant="outline" className="text-[9px]">
            {done}/{total || 0}
          </Badge>
        </Button>

        {expanded ? (
          <div className="space-y-2 px-3 pb-3">
            <Progress value={pct} className="h-1" />
            <ul className="space-y-1.5">
              {visibleSteps.map((step, index) => (
                <li
                  key={step.step_id}
                  className="flex items-start gap-2 text-xs"
                >
                  <StepIcon step={step} index={index} />
                  <div className="min-w-0 flex-1">
                    <p className="font-medium">{step.description}</p>
                    <p className="text-muted-foreground">
                      {step.agent_role} · {getStepStatusLabel(step.status)}
                    </p>
                  </div>
                </li>
              ))}
            </ul>
          </div>
        ) : null}
      </div>
    </div>
  )
}
