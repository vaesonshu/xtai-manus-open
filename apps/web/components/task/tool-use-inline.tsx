"use client"

import type { ToolRecord } from "@/lib/types"
import {
  formatToolArgs,
  formatToolResultSummary,
  getFriendlyToolLabel,
  getStepToolLabel,
  getToolPanelTitle,
  getToolStatusLabel,
  isSearchTool,
  parseSearchToolResult,
  pickToolIcon,
  type SearchResultItem,
} from "@/lib/tool-display"
import { Badge } from "@workspace/ui/components/badge"
import { cn } from "@workspace/ui/lib/utils"
import { ExternalLink, Loader2 } from "lucide-react"

export interface ToolUseInlineProps {
  tool: ToolRecord
  onClick?: () => void
  selected?: boolean
}

function ToolBadge({
  icon: Icon,
  label,
  loading,
  selected,
  onClick,
}: {
  icon: ReturnType<typeof pickToolIcon>
  label: string
  loading?: boolean
  selected?: boolean
  onClick?: () => void
}) {
  return (
    <div
      role={onClick ? "button" : undefined}
      tabIndex={onClick ? 0 : undefined}
      onClick={onClick}
      onKeyDown={
        onClick
          ? (e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault()
                onClick()
              }
            }
          : undefined
      }
      className={cn(
        "inline-flex w-fit max-w-full min-w-0 items-center gap-1.5 rounded-lg border bg-muted/60 px-2.5 py-1 text-sm",
        onClick && "cursor-pointer transition-colors hover:bg-muted",
        loading && "border-amber-500/40",
        selected && "border-primary/50 bg-primary/5 ring-2 ring-primary/25"
      )}
    >
      <span className="shrink-0 text-muted-foreground">
        {loading ? (
          <Loader2 size={16} className="animate-spin" />
        ) : (
          <Icon size={16} />
        )}
      </span>
      <span className="max-w-[480px] truncate">{label}</span>
    </div>
  )
}

/** 时间线内联工具调用展示 */
export function ToolUseInline({ tool, onClick, selected }: ToolUseInlineProps) {
  const Icon = pickToolIcon(tool.functionName)
  const label = getFriendlyToolLabel(tool)
  return (
    <ToolBadge
      icon={Icon}
      label={label}
      loading={tool.status === "calling"}
      selected={selected}
      onClick={onClick}
    />
  )
}

/** 步骤卡片内工具行：只展示工具名称，点击在右侧面板查看结果 */
export function StepToolUseInline({
  tool,
  onClick,
  selected,
}: {
  tool: ToolRecord
  onClick?: () => void
  selected?: boolean
}) {
  const Icon = pickToolIcon(tool.functionName)
  const loading = tool.status === "calling"

  return (
    <button
      type="button"
      onClick={onClick}
      disabled={!onClick}
      className={cn(
        "flex min-w-0 items-center gap-1.5 rounded-md px-1 py-0.5 text-left text-xs transition-colors",
        onClick && "cursor-pointer hover:bg-muted/60",
        selected && "bg-primary/5 ring-1 ring-primary/25",
        !onClick && "cursor-default"
      )}
    >
      <span className="shrink-0 text-muted-foreground">
        {loading ? (
          <Loader2 size={14} className="animate-spin text-amber-600" />
        ) : (
          <Icon size={14} />
        )}
      </span>
      <span
        className={cn(
          "truncate",
          loading
            ? "text-amber-700 dark:text-amber-300"
            : "text-muted-foreground"
        )}
      >
        {getStepToolLabel(tool)}
      </span>
    </button>
  )
}

/** 工具面板：参数与结果详情 */
export function ToolDetailView({
  tool,
  fillHeight = false,
}: {
  tool: ToolRecord
  fillHeight?: boolean
}) {
  return (
    <div
      className={cn(
        fillHeight ? "flex h-full min-h-0 flex-col gap-3" : "space-y-3"
      )}
    >
      <div
        className={cn(
          "rounded-lg border bg-muted/30 p-3",
          fillHeight && "max-h-[28%] shrink-0 overflow-auto"
        )}
      >
        <p className="mb-1 text-[10px] font-medium tracking-wide text-muted-foreground uppercase">
          参数
        </p>
        <pre className="font-sans text-sm break-all whitespace-pre-wrap">
          {formatToolArgs(tool)}
        </pre>
      </div>

      {tool.status === "calling" && (
        <div className="flex flex-1 items-center justify-center gap-2 text-sm text-amber-600 dark:text-amber-400">
          <Loader2 className="size-4 animate-spin" />
          执行中…
        </div>
      )}

      {tool.status === "called" && (
        <div
          className={cn(
            fillHeight ? "flex min-h-0 flex-1 flex-col gap-2" : "space-y-2"
          )}
        >
          <p className="shrink-0 text-[10px] font-medium tracking-wide text-muted-foreground uppercase">
            结果
          </p>
          <div
            className={cn(
              fillHeight &&
                "min-h-0 flex-1 overflow-auto rounded-lg border bg-muted/20 p-1"
            )}
          >
            <ToolResultBody tool={tool} fillHeight={fillHeight} />
          </div>
        </div>
      )}
    </div>
  )
}

function SearchResultView({
  result,
  fillHeight = false,
}: {
  result: unknown
  fillHeight?: boolean
}) {
  const parsed = parseSearchToolResult(result)

  if (!parsed.success) {
    return (
      <p className="rounded-lg border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm text-destructive">
        {parsed.message || "搜索失败"}
      </p>
    )
  }

  if (parsed.usedBaiduFallback) {
    return (
      <div
        className={cn(
          "space-y-2",
          fillHeight && "flex h-full min-h-0 flex-col"
        )}
      >
        <p className="shrink-0 rounded-md border border-amber-500/30 bg-amber-500/10 px-2.5 py-1.5 text-xs text-amber-700 dark:text-amber-300">
          DuckDuckGo 不可用，已自动改用百度搜索
        </p>
        <div className={cn(fillHeight && "min-h-0 flex-1 overflow-auto")}>
          <SearchResultBody parsed={parsed} fillHeight={fillHeight} />
        </div>
      </div>
    )
  }

  return <SearchResultBody parsed={parsed} fillHeight={fillHeight} />
}

function SearchResultBody({
  parsed,
  fillHeight = false,
}: {
  parsed: ReturnType<typeof parseSearchToolResult>
  fillHeight?: boolean
}) {
  if (parsed.items.length > 0) {
    return (
      <ul
        className={cn(
          "space-y-2 pr-1",
          fillHeight ? "min-h-0" : "max-h-64 overflow-auto"
        )}
      >
        {parsed.items.map((item, index) => (
          <SearchResultCard key={`${item.url}-${index}`} item={item} />
        ))}
      </ul>
    )
  }

  if (parsed.rawText) {
    return (
      <pre
        className={cn(
          "overflow-auto rounded-lg border bg-muted/40 p-3 text-sm break-all whitespace-pre-wrap",
          fillHeight ? "min-h-full" : "max-h-64"
        )}
      >
        {parsed.rawText}
      </pre>
    )
  }

  return (
    <p className="text-sm text-muted-foreground">
      {parsed.message || "无搜索结果"}
    </p>
  )
}

function SearchResultCard({ item }: { item: SearchResultItem }) {
  return (
    <li className="rounded-lg border bg-background p-3 text-sm">
      <div className="mb-1 flex items-start justify-between gap-2">
        <p className="leading-snug font-medium">{item.title}</p>
        {item.url ? (
          <a
            href={item.url}
            target="_blank"
            rel="noreferrer"
            className="shrink-0 text-muted-foreground hover:text-primary"
            aria-label="打开链接"
          >
            <ExternalLink className="size-3.5" />
          </a>
        ) : null}
      </div>
      {item.url ? (
        <p className="mb-1 truncate text-xs text-primary/80">{item.url}</p>
      ) : null}
      {item.snippet ? (
        <p className="line-clamp-3 text-xs leading-relaxed text-muted-foreground">
          {item.snippet}
        </p>
      ) : null}
    </li>
  )
}

export { getToolPanelTitle, getToolStatusLabel, pickToolIcon }

/** 工具结果区：优先结构化 toolContent，回退 function_result 解析 */
function ToolResultBody({
  tool,
  fillHeight = false,
}: {
  tool: ToolRecord
  fillHeight?: boolean
}) {
  const content = tool.toolContent
  const summary = formatToolResultSummary(tool)

  if (content?.type === "browser") {
    if (content.screenshot) {
      return (
        <img
          src={
            content.screenshot.startsWith("data:")
              ? content.screenshot
              : `data:image/png;base64,${content.screenshot}`
          }
          alt="浏览器截图"
          className={cn(
            "rounded-lg border bg-background object-contain",
            fillHeight ? "max-h-full w-full" : "max-h-64 w-full"
          )}
        />
      )
    }
    if (content.content) {
      return (
        <pre
          className={cn(
            "overflow-auto rounded-lg border bg-muted/40 p-3 text-sm break-all whitespace-pre-wrap",
            fillHeight ? "min-h-full" : "max-h-64"
          )}
        >
          {content.content}
        </pre>
      )
    }
  }

  if (content?.type === "file") {
    return (
      <div
        className={cn(
          "space-y-2",
          fillHeight && "flex h-full min-h-0 flex-col"
        )}
      >
        {content.path ? (
          <p className="shrink-0 truncate text-xs text-muted-foreground">
            {content.path}
          </p>
        ) : null}
        <pre
          className={cn(
            "overflow-auto rounded-lg border bg-muted/40 p-3 font-mono text-xs break-all whitespace-pre-wrap",
            fillHeight ? "min-h-0 flex-1" : "max-h-64"
          )}
        >
          {content.content || summary || "(无内容)"}
        </pre>
      </div>
    )
  }

  if (isSearchTool(tool.functionName)) {
    return <SearchResultView result={tool.result} fillHeight={fillHeight} />
  }

  if (summary) {
    return (
      <p className="rounded-lg border bg-emerald-500/5 px-3 py-2 text-sm text-emerald-700 dark:text-emerald-300">
        {summary}
      </p>
    )
  }

  return (
    <pre
      className={cn(
        "overflow-auto rounded-lg bg-zinc-950 p-3 font-mono text-xs break-all whitespace-pre-wrap text-emerald-400",
        fillHeight ? "min-h-full" : "max-h-48"
      )}
    >
      {JSON.stringify(tool.result, null, 2)}
    </pre>
  )
}
