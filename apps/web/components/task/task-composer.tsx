"use client"

import { useCallback, useState } from "react"

import { Button } from "@workspace/ui/components/button"
import { Textarea } from "@workspace/ui/components/textarea"
import { cn } from "@workspace/ui/lib/utils"
import { ArrowUp, Loader2, Square } from "lucide-react"

interface TaskComposerProps {
  mode: "create" | "reply"
  disabled?: boolean
  loading?: boolean
  placeholder?: string
  onSubmit: (value: string) => void | Promise<void>
  onStop?: () => void
  className?: string
}

/** 底部输入区：多行输入 + 发送 */
export function TaskComposer({
  mode,
  disabled = false,
  loading = false,
  placeholder,
  onSubmit,
  onStop,
  className,
}: TaskComposerProps) {
  const [value, setValue] = useState("")

  const busy = loading

  const submit = useCallback(() => {
    const trimmed = value.trim()
    if (!trimmed || busy || disabled) return
    void onSubmit(trimmed)
    setValue("")
  }, [value, busy, disabled, onSubmit])

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      submit()
    }
  }

  const defaultPlaceholder =
    mode === "create"
      ? "描述你的任务，Enter 发送，Shift+Enter 换行"
      : "Agent 等待你的回复…"

  return (
    <div
      className={cn(
        "border-t bg-background/80 p-4 backdrop-blur-sm",
        className
      )}
    >
      <div className="mx-auto max-w-3xl">
        <div
          className={cn(
            "relative rounded-2xl border bg-card shadow-sm transition-shadow",
            "focus-within:border-primary/40 focus-within:ring-2 focus-within:ring-ring/20"
          )}
        >
          <Textarea
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={placeholder ?? defaultPlaceholder}
            disabled={disabled || busy}
            rows={1}
            className="max-h-40 min-h-[52px] resize-none border-0 bg-transparent px-4 pt-4 pb-12 shadow-none focus-visible:ring-0"
          />

          <div className="absolute right-2 bottom-2 left-2 flex items-center justify-end">
            {busy && onStop ? (
              <Button
                size="icon-sm"
                variant="outline"
                onClick={onStop}
                aria-label="停止"
              >
                <Square className="size-3.5 fill-current" />
              </Button>
            ) : (
              <Button
                size="icon-sm"
                onClick={submit}
                disabled={disabled || busy || !value.trim()}
                aria-label={mode === "create" ? "创建任务" : "发送回复"}
              >
                <ArrowUp className="size-4" />
              </Button>
            )}
          </div>
        </div>

        <p className="mt-2 text-center text-[11px] text-muted-foreground">
          {busy ? (
            <span className="inline-flex items-center gap-1.5">
              <Loader2 className="size-3 animate-spin" />
              {mode === "reply" ? "Agent 正在思考…" : "正在创建任务…"}
            </span>
          ) : (
            "XTAI Manus 可能产生错误，请核实重要信息"
          )}
        </p>
      </div>
    </div>
  )
}
