"use client"

import type { TimelineItem, ToolRecord } from "@/lib/types"
import { Bubble, BubbleContent } from "@workspace/ui/components/bubble"
import { Card, CardContent, CardHeader, CardTitle } from "@workspace/ui/components/card"
import { Marker, MarkerContent } from "@workspace/ui/components/marker"
import {
  Message,
  MessageAvatar,
  MessageContent,
  MessageHeader,
} from "@workspace/ui/components/message"
import {
  MessageScroller,
  MessageScrollerButton,
  MessageScrollerContent,
  MessageScrollerItem,
  MessageScrollerProvider,
  MessageScrollerViewport,
} from "@workspace/ui/components/message-scroller"
import { Badge } from "@workspace/ui/components/badge"
import { cn } from "@workspace/ui/lib/utils"
import {
  BotIcon,
  Loader2Icon,
  UserIcon,
  WrenchIcon,
} from "lucide-react"

interface TaskTimelineProps {
  timeline: TimelineItem[]
  isStreaming: boolean
  onToolSelect?: (toolId: string) => void
  selectedToolId?: string | null
  className?: string
}

function MessageRow({
  role,
  content,
}: {
  role: "user" | "assistant"
  content: string
}) {
  const isUser = role === "user"

  return (
    <Message align={isUser ? "end" : "start"}>
      <MessageAvatar className="size-8">
        {isUser ? <UserIcon className="size-4" /> : <BotIcon className="size-4" />}
      </MessageAvatar>
      <MessageContent>
        <MessageHeader>{isUser ? "你" : "助手"}</MessageHeader>
        <Bubble variant={isUser ? "default" : "muted"} align={isUser ? "end" : "start"}>
          <BubbleContent className="whitespace-pre-wrap">{content}</BubbleContent>
        </Bubble>
      </MessageContent>
    </Message>
  )
}

function StepRow({ item }: { item: Extract<TimelineItem, { kind: "step" }> }) {
  return (
    <Marker>
      <MarkerContent>
        <span className="font-medium">{item.step.description}</span>
        <Badge variant="outline" className="ml-2 text-[10px]">
          {item.step.agent_role} · {item.eventStatus}
        </Badge>
        {item.step.result ? (
          <p className="text-muted-foreground mt-1 text-xs">{item.step.result}</p>
        ) : null}
      </MarkerContent>
    </Marker>
  )
}

function ToolRow({
  item,
  selected,
  onSelect,
}: {
  item: Extract<TimelineItem, { kind: "tool" }>
  selected: boolean
  onSelect?: (toolId: string) => void
}) {
  return (
    <button
      type="button"
      onClick={() => onSelect?.(item.toolCallId)}
      className={cn(
        "hover:bg-muted/40 w-full rounded-lg border px-3 py-2 text-left transition-colors",
        selected && "border-primary bg-primary/5"
      )}
    >
      <div className="flex items-center gap-2 text-xs font-medium">
        <WrenchIcon className="size-3.5" />
        {item.toolName}.{item.functionName}
        <Badge variant="outline" className="ml-auto text-[10px]">
          {item.status === "calling" ? "调用中" : "已完成"}
        </Badge>
      </div>
    </button>
  )
}

/** 任务时间线：消息 / 步骤 / 工具混排 */
export function TaskTimeline({
  timeline,
  isStreaming,
  onToolSelect,
  selectedToolId,
  className,
}: TaskTimelineProps) {
  return (
    <MessageScrollerProvider autoScroll>
      <MessageScroller className={className}>
        <MessageScrollerViewport>
          <MessageScrollerContent className="mx-auto max-w-3xl px-4 py-6">
            {timeline.length === 0 ? (
              <div className="text-muted-foreground flex min-h-[240px] items-center justify-center text-sm">
                等待智能体开始规划与执行…
              </div>
            ) : (
              timeline.map((item) => (
                <MessageScrollerItem
                  key={item.id}
                  scrollAnchor={item.kind === "message" && item.role === "user"}
                >
                  {item.kind === "message" ? (
                    <MessageRow role={item.role} content={item.content} />
                  ) : null}

                  {item.kind === "step" ? <StepRow item={item} /> : null}

                  {item.kind === "tool" ? (
                    <ToolRow
                      item={item}
                      selected={selectedToolId === item.toolCallId}
                      onSelect={onToolSelect}
                    />
                  ) : null}

                  {item.kind === "system" ? (
                    <Marker
                      className={cn(
                        item.variant === "error" && "text-destructive"
                      )}
                    >
                      <MarkerContent>{item.content}</MarkerContent>
                    </Marker>
                  ) : null}
                </MessageScrollerItem>
              ))
            )}

            {isStreaming ? (
              <MessageScrollerItem>
                <div className="text-muted-foreground flex items-center gap-2 text-xs">
                  <Loader2Icon className="size-3.5 animate-spin" />
                  智能体正在思考…
                </div>
              </MessageScrollerItem>
            ) : null}
          </MessageScrollerContent>
        </MessageScrollerViewport>
        <MessageScrollerButton />
      </MessageScroller>
    </MessageScrollerProvider>
  )
}

/** 右侧工具详情面板 */
export function ToolPanel({
  tools,
  focusedToolId,
  className,
}: {
  tools: ToolRecord[]
  focusedToolId: string | null
  className?: string
}) {
  const focused =
    tools.find((tool) => tool.id === focusedToolId) ??
    tools[tools.length - 1] ??
    null

  return (
    <aside
      className={cn(
        "border-border/60 bg-muted/10 flex h-full w-full flex-col border-l",
        className
      )}
    >
      <div className="border-b border-border/60 px-4 py-3">
        <h2 className="text-sm font-medium">工具工作区</h2>
        <p className="text-muted-foreground text-xs">
          查看 Agent 调用的工具与参数
        </p>
      </div>

      <div className="min-h-0 flex-1 space-y-3 overflow-y-auto p-4">
        {tools.length === 0 ? (
          <p className="text-muted-foreground text-sm">暂无工具调用</p>
        ) : (
          tools.map((tool) => (
            <Card
              key={tool.id}
              className={cn(
                focused?.id === tool.id && "border-primary shadow-sm"
              )}
            >
              <CardHeader className="pb-2">
                <CardTitle className="text-sm">
                  {tool.toolName}.{tool.functionName}
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-2 text-xs">
                <Badge variant="outline">
                  {tool.status === "calling" ? "调用中" : "已完成"}
                </Badge>
                {tool.args ? (
                  <pre className="bg-muted overflow-x-auto rounded-md p-2">
                    {JSON.stringify(tool.args, null, 2)}
                  </pre>
                ) : null}
                {tool.result !== undefined ? (
                  <pre className="bg-muted overflow-x-auto rounded-md p-2">
                    {JSON.stringify(tool.result, null, 2)}
                  </pre>
                ) : null}
              </CardContent>
            </Card>
          ))
        )}
      </div>
    </aside>
  )
}
