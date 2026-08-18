"use client"

import {
  Bot,
  ListTodo,
  Map,
  Sparkles,
  TrendingUp,
} from "lucide-react"

import { TaskComposer } from "@/components/task/task-composer"
import { cn } from "@workspace/ui/lib/utils"

const suggestions = [
  {
    icon: Map,
    title: "规划旅行",
    prompt: "帮我规划一份北京 3 日游行程，包含每日亮点和交通建议。",
  },
  {
    icon: TrendingUp,
    title: "数据分析",
    prompt: "分析一下 2024 年新能源汽车市场趋势，给出 3 条关键结论。",
  },
  {
    icon: ListTodo,
    title: "任务拆解",
    prompt: "我要在一周内上线一个 MVP 产品，请帮我拆解执行步骤。",
  },
  {
    icon: Sparkles,
    title: "快速问答",
    prompt: "用 echo 工具回复 hello，并简要介绍你能做什么。",
  },
]

interface WelcomeScreenProps {
  loading?: boolean
  onSubmit: (goal: string) => void | Promise<void>
  className?: string
}

/** Manus 风格欢迎页：居中引导 + 任务模板卡片 */
export function WelcomeScreen({
  loading = false,
  onSubmit,
  className,
}: WelcomeScreenProps) {
  return (
    <div
      className={cn(
        "flex min-h-0 flex-1 flex-col overflow-hidden",
        className
      )}
    >
      <div className="flex flex-1 flex-col items-center justify-center px-6 py-12">
        <div className="mb-8 flex size-14 items-center justify-center rounded-2xl border bg-card shadow-sm">
          <Bot className="size-7 text-primary" />
        </div>
        <h1 className="mb-2 text-center text-2xl font-semibold tracking-tight">
          给 XTAI Manus 一个任务
        </h1>
        <p className="mb-10 max-w-md text-center text-sm leading-relaxed text-muted-foreground">
          自主规划、调用工具、分步执行。实时查看任务进度与工具调用过程。
        </p>

        <div className="grid w-full max-w-2xl gap-3 sm:grid-cols-2">
          {suggestions.map((item) => (
            <button
              key={item.title}
              type="button"
              disabled={loading}
              onClick={() => void onSubmit(item.prompt)}
              className={cn(
                "group rounded-xl border bg-card p-4 text-left transition-colors",
                "hover:border-primary/30 hover:bg-accent/40",
                "disabled:pointer-events-none disabled:opacity-50"
              )}
            >
              <item.icon className="mb-3 size-4 text-muted-foreground transition-colors group-hover:text-primary" />
              <div className="mb-1 text-sm font-medium">{item.title}</div>
              <p className="line-clamp-2 text-xs leading-relaxed text-muted-foreground">
                {item.prompt}
              </p>
            </button>
          ))}
        </div>

        <p className="mt-8 text-xs text-muted-foreground">
          或在下方输入框直接描述你的任务
        </p>
      </div>

      <TaskComposer mode="create" loading={loading} onSubmit={onSubmit} />
    </div>
  )
}
