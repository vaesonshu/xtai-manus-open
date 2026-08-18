import { Geist, Geist_Mono } from "next/font/google"
import Script from "next/script"

import "@workspace/ui/globals.css"
import { ThemeProvider } from "@/components/theme-provider"
import { TooltipProvider } from "@workspace/ui/components/tooltip"
import { cn } from "@workspace/ui/lib/utils"

const geist = Geist({ subsets: ["latin"], variable: "--font-sans" })

const fontMono = Geist_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
})

/** 首屏阻塞脚本：在 React 水合前应用主题，避免闪烁 */
const themeInitScript = `
(function () {
  try {
    var storageKey = "theme";
    var themes = ["light", "dark"];
    var root = document.documentElement;
    var theme = localStorage.getItem(storageKey) || "system";
    if (theme === "system") {
      theme = window.matchMedia("(prefers-color-scheme: dark)").matches
        ? "dark"
        : "light";
    }
    root.classList.remove.apply(root.classList, themes);
    root.classList.add(theme);
    root.style.colorScheme = theme;
  } catch (e) {}
})();
`.trim()

export const metadata = {
  title: "XTAI Manus",
  description: "LangGraph 驱动的自主 Agent 工作台",
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html
      lang="zh-CN"
      suppressHydrationWarning
      className={cn("antialiased", fontMono.variable, "font-sans", geist.variable)}
    >
      <body className="overflow-hidden">
        <Script id="theme-init" strategy="beforeInteractive">
          {themeInitScript}
        </Script>
        <ThemeProvider>
          <TooltipProvider>{children}</TooltipProvider>
        </ThemeProvider>
      </body>
    </html>
  )
}
