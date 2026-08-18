"use client"

import { useState } from "react"

import {
  InputGroup,
  InputGroupAddon,
  InputGroupButton,
  InputGroupTextarea,
} from "@workspace/ui/components/input-group"
import { Spinner } from "@workspace/ui/components/spinner"
import { cn } from "@workspace/ui/lib/utils"
import { ArrowUpIcon } from "lucide-react"

interface TaskComposerProps {
  mode: "create" | "reply"
  disabled?: boolean
  loading?: boolean
  placeholder?: string
  onSubmit: (value: string) => void | Promise<void>
  className?: string
}

/** 任务输入框：创建目标或 waiting 状态下回复 */
export function TaskComposer({
  mode,
  disabled = false,
  loading = false,
  placeholder,
  onSubmit,
  className,
}: TaskComposerProps) {
  const [value, setValue] = useState("")

  const handleSubmit = async () => {
    const trimmed = value.trim()
    if (!trimmed || disabled || loading) {
      return
    }

    await onSubmit(trimmed)
    setValue("")
  }

  const defaultPlaceholder =
    mode === "create"
      ? "描述你想完成的任务，例如：用 echo 工具回复 hello"
      : "输入你的回复…"

  return (
    <div className={cn("px-4 pb-4 pt-2", className)}>
      <div className="mx-auto max-w-3xl">
        <InputGroup className="min-h-24 items-end rounded-2xl px-2 py-2">
          <InputGroupTextarea
            value={value}
            onChange={(event) => setValue(event.target.value)}
            placeholder={placeholder ?? defaultPlaceholder}
            disabled={disabled || loading}
            rows={3}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault()
                void handleSubmit()
              }
            }}
          />
          <InputGroupAddon align="block-end" className="justify-end">
            <InputGroupButton
              size="icon-sm"
              variant="default"
              disabled={disabled || loading || !value.trim()}
              onClick={() => void handleSubmit()}
              aria-label={mode === "create" ? "创建任务" : "发送回复"}
            >
              {loading ? <Spinner /> : <ArrowUpIcon />}
            </InputGroupButton>
          </InputGroupAddon>
        </InputGroup>
      </div>
    </div>
  )
}
