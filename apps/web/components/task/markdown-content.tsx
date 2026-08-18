"use client"

import { useMemo } from "react"
import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"
import { cn } from "@workspace/ui/lib/utils"

export interface MarkdownContentProps {
  content: string
  className?: string
}

/** 修正 GFM autolink 与 CJK 字符的边界问题 */
const CJK_RANGES = "\u3000-\u303F\u4E00-\u9FFF\uFF01-\uFF60"
const URL_FOLLOWED_BY_CJK = new RegExp(
  `(https?:\\/\\/[^\\s${CJK_RANGES}]+)([${CJK_RANGES}])`,
  "g"
)

function normalizeAutolinks(text: string): string {
  return text.replace(URL_FOLLOWED_BY_CJK, "$1 $2")
}

const headingClasses: Record<string, string> = {
  h1: "text-lg font-semibold mt-4 mb-2 first:mt-0",
  h2: "text-base font-semibold mt-3 mb-1.5 first:mt-0",
  h3: "text-sm font-semibold mt-2.5 mb-1 first:mt-0",
  h4: "text-sm font-medium mt-2 mb-1 first:mt-0",
}

const components: React.ComponentProps<typeof ReactMarkdown>["components"] = {
  h1: ({ className, ...props }) => (
    <h1 className={cn(headingClasses.h1, className)} {...props} />
  ),
  h2: ({ className, ...props }) => (
    <h2 className={cn(headingClasses.h2, className)} {...props} />
  ),
  h3: ({ className, ...props }) => (
    <h3 className={cn(headingClasses.h3, className)} {...props} />
  ),
  h4: ({ className, ...props }) => (
    <h4 className={cn(headingClasses.h4, className)} {...props} />
  ),
  p: ({ className, ...props }) => (
    <p
      className={cn("mb-2 text-sm leading-relaxed last:mb-0", className)}
      {...props}
    />
  ),
  ul: ({ className, ...props }) => (
    <ul
      className={cn("mb-2 list-disc space-y-0.5 pl-5 text-sm", className)}
      {...props}
    />
  ),
  ol: ({ className, ...props }) => (
    <ol
      className={cn("mb-2 list-decimal space-y-0.5 pl-5 text-sm", className)}
      {...props}
    />
  ),
  li: ({ className, ...props }) => (
    <li className={cn("leading-relaxed", className)} {...props} />
  ),
  strong: ({ className, ...props }) => (
    <strong className={cn("font-semibold", className)} {...props} />
  ),
  code: ({ className, children, ...props }) => {
    const text = typeof children === "string" ? children : ""
    const isBlock = text.includes("\n")
    return (
      <code
        className={cn(
          isBlock
            ? "my-2 block overflow-x-auto rounded-md bg-muted p-3 font-mono text-sm"
            : "inline rounded bg-muted px-1.5 py-0.5 font-mono text-[0.8125em]",
          className
        )}
        {...props}
      >
        {children}
      </code>
    )
  },
  pre: ({ className, ...props }) => (
    <pre className={cn("my-2 overflow-x-auto", className)} {...props} />
  ),
  blockquote: ({ className, ...props }) => (
    <blockquote
      className={cn(
        "my-2 border-l-4 border-muted-foreground/30 py-0.5 pl-3 text-sm text-muted-foreground italic",
        className
      )}
      {...props}
    />
  ),
  a: ({ className, href, children, ...props }) => {
    if (href && /[\u4E00-\u9FFF\u3000-\u303F\uFF00-\uFFEF]/.test(href)) {
      return <span className="text-sm">{children}</span>
    }
    return (
      <a
        className={cn("text-sm text-primary hover:underline", className)}
        href={href}
        target="_blank"
        rel="noopener noreferrer"
        {...props}
      >
        {children}
      </a>
    )
  },
}

/** Markdown 正文渲染 */
export function MarkdownContent({ content, className }: MarkdownContentProps) {
  const normalized = useMemo(() => normalizeAutolinks(content), [content])

  return (
    <div className={cn("markdown-content wrap-break-word", className)}>
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
        {normalized}
      </ReactMarkdown>
    </div>
  )
}
