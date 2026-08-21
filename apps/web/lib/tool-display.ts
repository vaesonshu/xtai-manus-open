import type { ToolRecord } from "@/lib/types"
import {
  BookOpen,
  Calculator,
  Clock,
  Globe,
  Languages,
  Search,
  SquareChevronRight,
  type LucideIcon,
} from "lucide-react"

/** 搜索类工具名称 */
export const SEARCH_TOOL_NAMES = new Set([
  "search_web",
  "duckduckgo_search",
  "search_web_zh",
  "search_web_en",
])

export interface SearchResultItem {
  title: string
  url: string
  snippet: string
}

export interface ParsedSearchToolResult {
  success: boolean
  message: string
  query?: string
  items: SearchResultItem[]
  rawText?: string
  usedBaiduFallback?: boolean
}

interface ToolDisplayMeta {
  title: string
  provider: string
  callingVerb: string
  calledVerb: string
}

const TOOL_META: Record<string, ToolDisplayMeta> = {
  search_web: {
    title: "网络搜索",
    provider: "搜索引擎",
    callingVerb: "正在搜索",
    calledVerb: "搜索完成",
  },
  read_file: {
    title: "读取文件",
    provider: "文件",
    callingVerb: "正在读取",
    calledVerb: "读取完成",
  },
  write_file: {
    title: "写入文件",
    provider: "文件",
    callingVerb: "正在写入",
    calledVerb: "写入完成",
  },
  shell_execute: {
    title: "执行命令",
    provider: "Shell",
    callingVerb: "正在执行",
    calledVerb: "执行完成",
  },
  duckduckgo_search: {
    title: "网络搜索",
    provider: "DuckDuckGo",
    callingVerb: "正在搜索",
    calledVerb: "搜索完成",
  },
  search_web_zh: {
    title: "中文搜索",
    provider: "百度",
    callingVerb: "正在中文检索",
    calledVerb: "中文检索完成",
  },
  search_web_en: {
    title: "英文搜索",
    provider: "Bing",
    callingVerb: "正在英文检索",
    calledVerb: "英文检索完成",
  },
  calculate: {
    title: "数学计算",
    provider: "内置",
    callingVerb: "正在计算",
    calledVerb: "计算完成",
  },
  get_current_time: {
    title: "获取时间",
    provider: "内置",
    callingVerb: "正在获取时间",
    calledVerb: "已获取时间",
  },
  echo: {
    title: "回声测试",
    provider: "内置",
    callingVerb: "正在回显",
    calledVerb: "回显完成",
  },
}

function getMeta(functionName: string): ToolDisplayMeta | null {
  return TOOL_META[functionName] ?? null
}

/** 步骤下展示的工具名称（不含参数与结果） */
export function getToolDisplayName(functionName: string): string {
  return getMeta(functionName)?.title ?? functionName
}

/** 步骤卡片内工具行：只说明正在/已使用何种工具 */
export function getStepToolLabel(tool: ToolRecord): string {
  const name = getToolDisplayName(tool.functionName)
  return tool.status === "calling" ? `正在使用 ${name}` : name
}

function getQuery(args: Record<string, unknown> | undefined): string {
  const query = args?.query
  return typeof query === "string" ? query.trim() : ""
}

function truncate(text: string, max = 48): string {
  if (text.length <= max) return text
  return `${text.slice(0, max)}…`
}

/** 是否为搜索类工具 */
export function isSearchTool(functionName: string): boolean {
  return SEARCH_TOOL_NAMES.has(functionName)
}

/** 根据工具名选择图标 */
export function pickToolIcon(name: string): LucideIcon {
  if (name === "calculate") return Calculator
  if (name === "get_current_time") return Clock
  if (name === "search_web" || name === "duckduckgo_search") return Globe
  if (name === "search_web_zh") return BookOpen
  if (name === "search_web_en") return Languages
  if (isSearchTool(name)) return Search
  return SquareChevronRight
}

/** 时间线内联展示的友好标签 */
export function getFriendlyToolLabel(tool: ToolRecord): string {
  const { functionName, args, status, result } = tool
  const meta = getMeta(functionName)
  const query = getQuery(args)

  if (functionName === "calculate") {
    const expr = args?.expression
    return typeof expr === "string" ? `计算 ${expr}` : "执行计算"
  }

  if (functionName === "get_current_time") {
    return status === "calling" ? "获取当前时间…" : "获取当前时间"
  }

  if (functionName === "echo") {
    const text = args?.text ?? args?.message
    return typeof text === "string" ? `回显「${truncate(text)}」` : "执行 echo"
  }

  if (isSearchTool(functionName) && meta) {
    const parsed = status === "called" ? parseSearchToolResult(result) : null
    const fallbackHint =
      parsed?.usedBaiduFallback && status === "called" ? "（已回退百度）" : ""
    const countHint =
      parsed && parsed.items.length > 0 ? ` · ${parsed.items.length} 条` : ""

    if (status === "calling") {
      return query
        ? `${meta.callingVerb}「${truncate(query)}」…`
        : `${meta.callingVerb}…`
    }

    return query
      ? `${meta.provider} ${meta.calledVerb}「${truncate(query)}」${countHint}${fallbackHint}`
      : `${meta.provider} ${meta.calledVerb}${countHint}${fallbackHint}`
  }

  return `${tool.toolName}.${functionName}`
}

/** 工具面板标题 */
export function getToolPanelTitle(tool: ToolRecord): string {
  const meta = getMeta(tool.functionName)
  if (meta) return `${meta.title} · ${meta.provider}`
  return `${tool.toolName}.${tool.functionName}`
}

/** 参数区展示文案 */
export function formatToolArgs(tool: ToolRecord): string {
  const { functionName, args } = tool

  if (isSearchTool(functionName)) {
    const lines = [`查询：${getQuery(args) || "（未提供）"}`]
    const dateRange = args?.date_range
    if (typeof dateRange === "string" && dateRange !== "all") {
      lines.push(`时间范围：${dateRange}`)
    }
    return lines.join("\n")
  }

  if (functionName === "calculate") {
    return `表达式：${String(args?.expression ?? "")}`
  }

  if (functionName === "get_current_time") {
    return "无参数"
  }

  return JSON.stringify(args ?? {}, null, 2)
}

function asRecord(value: unknown): Record<string, unknown> | null {
  return value && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : null
}

function parseSearchItems(data: unknown): SearchResultItem[] {
  const record = asRecord(data)
  if (!record || !Array.isArray(record.results)) return []

  return record.results
    .map((item) => asRecord(item))
    .filter((item): item is Record<string, unknown> => item !== null)
    .map((item) => ({
      title: String(item.title ?? "无标题"),
      url: String(item.url ?? ""),
      snippet: String(item.snippet ?? ""),
    }))
    .filter((item) => item.title || item.url || item.snippet)
}

/** 解析搜索工具返回结果 */
export function parseSearchToolResult(result: unknown): ParsedSearchToolResult {
  const record = asRecord(result)
  if (!record) {
    return { success: false, message: "", items: [] }
  }

  const success = record.success !== false
  const message = String(record.message ?? "")
  const data = record.data
  const items = parseSearchItems(data)
  const usedBaiduFallback = message.includes("自动改用百度")

  let rawText: string | undefined
  if (items.length === 0) {
    if (typeof data === "string" && data.trim()) {
      rawText = data.trim()
    } else if (message.trim()) {
      rawText = message.trim()
    }
  }

  const dataRecord = asRecord(data)

  return {
    success,
    message,
    query: dataRecord ? String(dataRecord.query ?? "") : undefined,
    items,
    rawText,
    usedBaiduFallback,
  }
}

/** 结果区摘要 */
export function formatToolResultSummary(tool: ToolRecord): string | null {
  const { functionName, result, status } = tool
  if (status !== "called" || result === undefined) return null

  if (isSearchTool(functionName)) {
    const parsed = parseSearchToolResult(result)
    if (!parsed.success) {
      return parsed.message || "搜索失败"
    }
    if (parsed.items.length > 0) {
      const first = parsed.items[0]!
      const prefix = parsed.usedBaiduFallback ? "[百度回退] " : ""
      return `${prefix}${parsed.items.length} 条结果 · ${first.title}`
    }
    if (parsed.rawText) {
      return truncate(parsed.rawText, 120)
    }
    return parsed.message || "无搜索结果"
  }

  const record = asRecord(result)
  if (record?.message && typeof record.message === "string") {
    return record.message
  }

  return null
}

/** 状态徽章中文文案 */
export function getToolStatusLabel(status: ToolRecord["status"]): string {
  return status === "calling" ? "执行中" : "已完成"
}
