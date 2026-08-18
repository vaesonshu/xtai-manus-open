"use client"

import { TaskComposer } from "@/components/task/task-composer"
import { cn } from "@workspace/ui/lib/utils"
import { SparklesIcon } from "lucide-react"

const suggestions = [
  "用 echo 工具回复 hello",
  "调研三家竞品并输出对比表",
  "写一段 Python 脚本读取 CSV 并统计行数",
]

interface WelcomeScreenProps {
  loading?: boolean
  onSubmit: (goal: string) => void | Promise<void>
  className?: string
}

/** Manus 风格欢迎页：居中标题 + 建议 prompt */
export function WelcomeScreen({
  loading = false,
  onSubmit,
  className,
}: WelcomeScreenProps) {
  return (
    <div
      className={cn(
        "flex min-h-0 flex-1 flex-col items-center justify-center px-4 py-10",
        className
      )}
    >
      <div className="mb-8 flex max-w-2xl flex-col items-center text-center">
        <div className="bg-primary/10 text-primary mb-4 flex size-12 items-center justify-center rounded-2xl">
          <SparklesIcon className="size-6" />
        </div>
        <h1 className="text-2xl font-semibold tracking-tight">
          今天想完成什么？
        </h1>
        <p className="text-muted-foreground mt-2 max-w-lg text-sm leading-relaxed">
          描述你的目标，XTAI 会规划步骤、调用工具并实时推送执行过程。
        </p>
      </div>

      <div className="w-full max-w-2xl">
        <TaskComposer
          mode="create"
          loading={loading}
          onSubmit={onSubmit}
        />

        <div className="mt-4 flex flex-wrap justify-center gap-2">
          {suggestions.map((prompt) => (
            <button
              key={prompt}
              type="button"
              disabled={loading}
              onClick={() => void onSubmit(prompt)}
              className="bg-muted/40 hover:bg-muted text-muted-foreground rounded-full px-3 py-1.5 text-xs transition-colors"
            >
              {prompt}
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}
