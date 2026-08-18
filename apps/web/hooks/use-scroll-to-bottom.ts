"use client"

import { useCallback, useEffect, useRef } from "react"

const NEAR_BOTTOM_PX = 96

type UseScrollToBottomOptions = {
  /** 流式输出中：始终跟随到底部 */
  streaming?: boolean
}

/** 在 ScrollArea 视口内滚动到底部 */
export function useScrollToBottom<T extends HTMLElement = HTMLDivElement>(
  deps: unknown[],
  options?: UseScrollToBottomOptions
) {
  const rootRef = useRef<T>(null)
  const contentRef = useRef<HTMLDivElement>(null)
  const userPinnedUpRef = useRef(false)
  const streaming = options?.streaming ?? false

  const getViewport = useCallback(() => {
    return rootRef.current?.querySelector(
      '[data-slot="scroll-area-viewport"]'
    ) as HTMLElement | null
  }, [])

  const isNearBottom = useCallback((viewport: HTMLElement) => {
    const distance =
      viewport.scrollHeight - viewport.scrollTop - viewport.clientHeight
    return distance <= NEAR_BOTTOM_PX
  }, [])

  const scrollToBottom = useCallback(
    (behavior: ScrollBehavior = "auto") => {
      const viewport = getViewport()
      if (!viewport) return
      const effectiveBehavior = streaming ? "auto" : behavior
      viewport.scrollTo({ top: viewport.scrollHeight, behavior: effectiveBehavior })
    },
    [getViewport, streaming]
  )

  const followBottom = useCallback(() => {
    if (streaming || !userPinnedUpRef.current) {
      requestAnimationFrame(() => {
        scrollToBottom("auto")
      })
    }
  }, [scrollToBottom, streaming])

  useEffect(() => {
    const viewport = getViewport()
    if (!viewport) return

    const onScroll = () => {
      if (streaming) {
        userPinnedUpRef.current = false
        return
      }
      userPinnedUpRef.current = !isNearBottom(viewport)
    }

    viewport.addEventListener("scroll", onScroll, { passive: true })
    return () => viewport.removeEventListener("scroll", onScroll)
  }, [getViewport, isNearBottom, streaming])

  useEffect(() => {
    const content = contentRef.current
    if (!content) return

    const ro = new ResizeObserver(() => {
      followBottom()
    })
    ro.observe(content)
    return () => ro.disconnect()
  }, [followBottom])

  useEffect(() => {
    followBottom()
    // eslint-disable-next-line react-hooks/exhaustive-deps -- deps 由调用方传入
  }, deps)

  useEffect(() => {
    if (streaming) {
      userPinnedUpRef.current = false
      followBottom()
    }
  }, [streaming, followBottom])

  return { rootRef, contentRef, scrollToBottom }
}
