"use client"

import Link from "next/link"
import { useCallback, useEffect, useState } from "react"

import {
  fetchHealth,
  fetchLlmConfig,
  getAgentRun,
  startAgentRun,
  updateLlmConfig,
} from "@/lib/api-client"
import type {
  AgentRunResponse,
  HealthResponse,
  LlmConfigResponse,
} from "@/lib/types"
import { TaskSidebar } from "@/components/task/task-sidebar"
import { loadTaskSessions } from "@/lib/task-storage"
import { Alert, AlertDescription, AlertTitle } from "@workspace/ui/components/alert"
import { Badge } from "@workspace/ui/components/badge"
import { Button } from "@workspace/ui/components/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@workspace/ui/components/card"
import { Input } from "@workspace/ui/components/input"
import { Label } from "@workspace/ui/components/label"
import { SidebarInset, SidebarProvider } from "@workspace/ui/components/sidebar"
import { Spinner } from "@workspace/ui/components/spinner"
import { Switch } from "@workspace/ui/components/switch"
import { ArrowLeftIcon } from "lucide-react"

/** 设置页：LLM 配置、健康检查、旧版 Agent Run 调试 */
export function SettingsPageClient() {
  const [sessions, setSessions] = useState(loadTaskSessions())
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const [config, setConfig] = useState<LlmConfigResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState<string | null>(null)

  const [provider, setProvider] = useState("")
  const [model, setModel] = useState("")
  const [baseUrl, setBaseUrl] = useState("")
  const [apiKey, setApiKey] = useState("")
  const [temperature, setTemperature] = useState("0")
  const [maxTokens, setMaxTokens] = useState("")
  const [clearMaxTokens, setClearMaxTokens] = useState(false)

  const [agentGoal, setAgentGoal] = useState("用 echo 回复 ping")
  const [agentRun, setAgentRun] = useState<AgentRunResponse | null>(null)
  const [agentLoading, setAgentLoading] = useState(false)

  const refresh = useCallback(async () => {
    setLoading(true)
    try {
      const [healthData, configData] = await Promise.all([
        fetchHealth(),
        fetchLlmConfig(),
      ])
      setHealth(healthData)
      setConfig(configData)
      setProvider(configData.provider)
      setModel(configData.model)
      setBaseUrl(configData.base_url)
      setTemperature(String(configData.temperature))
      setMaxTokens(
        configData.max_tokens ? String(configData.max_tokens) : ""
      )
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "加载失败")
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void refresh()
  }, [refresh])

  const handleSave = async () => {
    setSaving(true)
    setMessage(null)
    try {
      const updated = await updateLlmConfig({
        provider,
        model,
        base_url: baseUrl,
        api_key: apiKey || undefined,
        temperature: Number(temperature),
        max_tokens: maxTokens ? Number(maxTokens) : undefined,
        clear_max_tokens: clearMaxTokens,
      })
      setConfig(updated)
      setApiKey("")
      setMessage("配置已保存")
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "保存失败")
    } finally {
      setSaving(false)
    }
  }

  const handleStartAgentRun = async () => {
    setAgentLoading(true)
    setMessage(null)
    try {
      const run = await startAgentRun(agentGoal)
      setAgentRun(run)

      if (run.status === "running" || run.status === "created") {
        const polled = await getAgentRun(run.run_id)
        setAgentRun(polled)
      }
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Agent Run 失败")
    } finally {
      setAgentLoading(false)
    }
  }

  return (
    <SidebarProvider defaultOpen>
      <TaskSidebar
        sessions={sessions}
        onRefresh={() => setSessions(loadTaskSessions())}
      />

      <SidebarInset className="min-h-svh">
        <div className="mx-auto flex w-full max-w-3xl flex-col gap-6 p-6">
          <div className="flex items-center gap-3">
            <Link href="/">
              <Button size="icon-sm" variant="ghost" aria-label="返回首页">
                <ArrowLeftIcon />
              </Button>
            </Link>
            <div>
              <h1 className="text-lg font-semibold">设置</h1>
              <p className="text-muted-foreground text-sm">
                管理 LLM 配置与系统状态
              </p>
            </div>
          </div>

          {message ? (
            <Alert>
              <AlertTitle>提示</AlertTitle>
              <AlertDescription>{message}</AlertDescription>
            </Alert>
          ) : null}

          {loading ? (
            <div className="flex items-center gap-2 text-sm">
              <Spinner />
              加载中…
            </div>
          ) : (
            <>
              <Card>
                <CardHeader>
                  <CardTitle>系统健康</CardTitle>
                  <CardDescription>GET /health</CardDescription>
                </CardHeader>
                <CardContent className="grid gap-2 text-sm">
                  <div className="flex items-center gap-2">
                    <Badge
                      variant={
                        health?.status === "ok" ? "secondary" : "destructive"
                      }
                    >
                      {health?.status ?? "unknown"}
                    </Badge>
                    <span>{health?.service}</span>
                  </div>
                  <p>环境：{health?.env}</p>
                  <p>Redis：{health?.redis}</p>
                  <p>Database：{health?.database}</p>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => void refresh()}
                  >
                    刷新
                  </Button>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>LLM 配置</CardTitle>
                  <CardDescription>GET/PUT /v1/llm/config</CardDescription>
                </CardHeader>
                <CardContent className="grid gap-4">
                  {config ? (
                    <p className="text-muted-foreground text-xs">
                      当前 Key：{config.api_key_masked}（
                      {config.has_api_key ? "已配置" : "未配置"}）
                    </p>
                  ) : null}

                  <div className="grid gap-2">
                    <Label htmlFor="provider">Provider</Label>
                    <Input
                      id="provider"
                      value={provider}
                      onChange={(event) => setProvider(event.target.value)}
                    />
                  </div>

                  <div className="grid gap-2">
                    <Label htmlFor="model">Model</Label>
                    <Input
                      id="model"
                      value={model}
                      onChange={(event) => setModel(event.target.value)}
                    />
                  </div>

                  <div className="grid gap-2">
                    <Label htmlFor="baseUrl">Base URL</Label>
                    <Input
                      id="baseUrl"
                      value={baseUrl}
                      onChange={(event) => setBaseUrl(event.target.value)}
                    />
                  </div>

                  <div className="grid gap-2">
                    <Label htmlFor="apiKey">API Key（留空则不修改）</Label>
                    <Input
                      id="apiKey"
                      type="password"
                      value={apiKey}
                      onChange={(event) => setApiKey(event.target.value)}
                    />
                  </div>

                  <div className="grid gap-2 sm:grid-cols-2">
                    <div className="grid gap-2">
                      <Label htmlFor="temperature">Temperature</Label>
                      <Input
                        id="temperature"
                        value={temperature}
                        onChange={(event) =>
                          setTemperature(event.target.value)
                        }
                      />
                    </div>
                    <div className="grid gap-2">
                      <Label htmlFor="maxTokens">Max Tokens</Label>
                      <Input
                        id="maxTokens"
                        value={maxTokens}
                        onChange={(event) => setMaxTokens(event.target.value)}
                      />
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    <Switch
                      checked={clearMaxTokens}
                      onCheckedChange={setClearMaxTokens}
                      id="clearMaxTokens"
                    />
                    <Label htmlFor="clearMaxTokens">清除 max_tokens 限制</Label>
                  </div>

                  <Button disabled={saving} onClick={() => void handleSave()}>
                    {saving ? <Spinner /> : "保存配置"}
                  </Button>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Agent Run（旧版接口）</CardTitle>
                  <CardDescription>
                    POST/GET /v1/agents/runs — 用于调试 LangGraph 运行
                  </CardDescription>
                </CardHeader>
                <CardContent className="grid gap-3">
                  <div className="grid gap-2">
                    <Label htmlFor="agentGoal">Goal</Label>
                    <Input
                      id="agentGoal"
                      value={agentGoal}
                      onChange={(event) => setAgentGoal(event.target.value)}
                    />
                  </div>
                  <Button
                    disabled={agentLoading}
                    onClick={() => void handleStartAgentRun()}
                  >
                    {agentLoading ? <Spinner /> : "发起 Run"}
                  </Button>
                  {agentRun ? (
                    <pre className="bg-muted overflow-x-auto rounded-md p-3 text-xs">
                      {JSON.stringify(agentRun, null, 2)}
                    </pre>
                  ) : null}
                </CardContent>
              </Card>
            </>
          )}
        </div>
      </SidebarInset>
    </SidebarProvider>
  )
}
