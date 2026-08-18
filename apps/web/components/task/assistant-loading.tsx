"use client"

import { Avatar, AvatarFallback } from "@workspace/ui/components/avatar"
import { cn } from "@workspace/ui/lib/utils"
import { Bot, Loader2 } from "lucide-react"

interface AssistantLoadingProps {
  hint?: string
  className?: string
}

/** AI 回复等待态 */
export function AssistantLoading({
  hint = "正在规划并执行任务…",
  className,
}: AssistantLoadingProps) {
  return (
    <div className={cn("flex gap-3", className)}>
      <Avatar className="size-8 shrink-0">
        <AvatarFallback className="bg-muted">
          <Bot className="size-4" />
        </AvatarFallback>
      </Avatar>

      <div className="flex flex-col gap-1.5">
        <div className="flex items-center gap-2.5 rounded-2xl rounded-tl-sm border bg-muted/60 px-4 py-3">
          <Loader2 className="size-4 shrink-0 animate-spin text-muted-foreground" />
          <span className="text-sm text-muted-foreground">{hint}</span>
          <span className="inline-flex gap-0.5 pb-0.5" aria-hidden>
            {[0, 1, 2].map((i) => (
              <span
                key={i}
                className="size-1 animate-bounce rounded-full bg-muted-foreground/60"
                style={{ animationDelay: `${i * 150}ms` }}
              />
            ))}
          </span>
        </div>
      </div>
    </div>
  )
}
