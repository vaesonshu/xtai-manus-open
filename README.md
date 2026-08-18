# xtai-manus-open

开源的 **Manus 类通用智能体（General AI Agent）**：任务规划、多角色执行、工具调用、人机协作与实时流式反馈。

前后端分离的 monorepo：

- **后端** `apps/api`：FastAPI + DDD + LangChain / LangGraph
- **前端** `apps/web`：Next.js (App Router) + shadcn/ui
- **共享 UI** `packages/ui`：基于 Radix + Tailwind 的组件库

> 更细的后端说明见 [`apps/api/README.md`](apps/api/README.md)；架构与编码约束见 [`AGENTS.md`](AGENTS.md)。

---

## 功能概览

| 能力 | 说明 |
| --- | --- |
| 任务规划 | 支持离线三步规划或 LLM 在线规划，可按步骤动态修订 |
| 多角色执行 | Coordinator / Researcher / Coder / Reviewer 等角色分工 |
| ReAct 循环 | 单步内 LLM ↔ 工具迭代，直到产出结构化结果 |
| 工具系统 | Shell、文件、搜索、浏览器、交互提问等，可扩展注册 |
| 人机协作 | 模型可调用 `message_ask_user`，任务进入 WAITING，用户回复后断点续跑 |
| 实时流式 UI | SSE 推送 plan / step / tool / message / wait / done |
| 记忆 | 工作记忆 + 情景记忆，支持压缩与回滚 |
| 基础设施 | PostgreSQL 持久化、Redis 缓存与消息流、可关闭降级为内存实现 |

---

## 技术栈

| 区域 | 技术 |
| --- | --- |
| 前端 | Next.js 16、React 19、shadcn/ui、Tailwind CSS 4、lucide-react |
| 后端 | FastAPI、Pydantic v2、SQLAlchemy、Alembic、uv |
| Agent | LangChain、LangGraph（StateGraph）、OpenAI 兼容端点 |
| 数据 | PostgreSQL 16、Redis 7 |
| 工程 | pnpm workspace、Turborepo、Docker Compose |

---

## 仓库结构

```text
xtai-manus-open/
├── apps/
│   ├── api/                 # FastAPI 后端（DDD 分层）
│   │   ├── domain/          # 实体、值对象、领域事件、端口
│   │   ├── application/     # 用例编排（Task Runner、Planning、ReAct…）
│   │   ├── infrastructure/  # LLM、Redis、Postgres、工具、LangGraph
│   │   ├── presentation/    # 路由、Schema、异常处理
│   │   └── tests/
│   └── web/                 # Next.js 前端
│       ├── app/             # App Router 页面
│       ├── components/
│       ├── hooks/           # 如 useTaskSession
│       └── lib/             # api-client、reducer、types
├── packages/
│   ├── ui/                  # 共享 shadcn 组件
│   ├── eslint-config/
│   └── typescript-config/
├── docker-compose.yml       # Redis + PostgreSQL
├── AGENTS.md                # 架构与开发约束
└── package.json             # pnpm + turbo 根脚本
```

后端依赖方向（DDD）：

```text
presentation ──▶ application ──▶ domain ◀── infrastructure
```

---

## 端到端流程（简版）

```text
用户输入 goal
  → POST /v1/tasks
  → AgentTaskRunner：建任务 → 规划 → 逐步执行
  → 每步 StepExecutor → ReActExecutor（LLM + 工具）
  → 事件写入 output_stream
  → SSE GET /v1/tasks/{id}/stream 推送到前端
  → 需要用户时进入 WAITING，reply 后续跑
  → 全部完成后 summarize 并推送 done
```

更完整的链路说明可参考项目讨论中的流程分析，或直接阅读：

- `application/task/agent_task_runner.py`
- `application/agent/react_executor.py`
- `presentation/api/routes/tasks.py`

---

## 快速开始

### 环境要求

- Node.js ≥ 20、pnpm ≥ 10
- Python ≥ 3.10、[uv](https://github.com/astral-sh/uv)
- Docker（推荐，用于 Redis / PostgreSQL）

### 1. 克隆并安装前端依赖

```bash
git clone https://github.com/vaesonshu/xtai-manus-open.git
cd xtai-manus-open
pnpm install
```

### 2. 启动基础设施

```bash
docker compose up -d
```

默认：

| 服务 | 地址 |
| --- | --- |
| Redis | `redis://localhost:6379/0` |
| PostgreSQL | `postgresql+psycopg://postgres:postgres@localhost:5432/xtai` |

### 3. 配置并启动后端

```bash
cd apps/api
uv sync

# 创建 .env（无模板时手动新建）
cat > .env << 'EOF'
OPENAI_API_KEY=sk-your-key
OPENAI_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4o-mini
REDIS_ENABLED=true
REDIS_URL=redis://localhost:6379/0
DATABASE_ENABLED=true
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/xtai
AGENT_USE_LLM_PLANNING=true
EOF

uv run alembic upgrade head
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

- Swagger：http://localhost:8000/docs  
- 健康检查：http://localhost:8000/health  

可将 `OPENAI_BASE_URL` 换成任意 OpenAI 兼容服务。

### 4. 启动前端

```bash
# 在仓库根目录
pnpm --filter web dev
```

默认 http://localhost:3000 。若 API 不在同源代理下，可设置：

```bash
export NEXT_PUBLIC_API_URL=http://localhost:8000
```

### 5. 仅用 curl 验证后端

```bash
# 创建任务
curl -s -X POST http://localhost:8000/v1/tasks \
  -H "Content-Type: application/json" \
  -d '{"goal": "用一句话介绍这个项目"}'

# 订阅事件流（替换 task_id）
curl -N http://localhost:8000/v1/tasks/{task_id}/stream

# 查询状态
curl -s http://localhost:8000/v1/tasks/{task_id}
```

WAITING 时回复：

```bash
curl -s -X POST http://localhost:8000/v1/tasks/{task_id}/reply \
  -H "Content-Type: application/json" \
  -d '{"content": "用户补充说明"}'
```

---

## 核心 API

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `GET` | `/health` | 健康检查（含 Redis / DB 状态） |
| `POST` | `/v1/tasks` | 提交目标，后台执行，返回 `task_id` |
| `GET` | `/v1/tasks/{task_id}` | 查询任务状态与规划 |
| `GET` | `/v1/tasks/{task_id}/stream` | SSE 事件流 |
| `POST` | `/v1/tasks/{task_id}/reply` | WAITING 状态下用户回复 |
| `GET/PUT` | `/v1/llm/config` | LLM 配置读写 |

SSE 常见事件类型：`user_message`、`plan_created`、`plan_updated`、`step_started`、`step_completed`、`tool_calling`、`tool_called`、`assistant_message`、`wait`、`done`、`error`。

---

## 测试

```bash
cd apps/api
uv run pytest
```

前端：

```bash
pnpm --filter web typecheck
pnpm --filter web lint
```

---

## 开发约定

- 后端严格遵循 DDD：领域逻辑只在 `domain/`，应用层只做编排。
- Agent 相关能力优先走 LangChain / LangGraph，工具统一经 `ToolRegistry` 注册。
- 前端遵循根目录 `.prettierrc`（无分号、双引号、2 空格、printWidth 80）。
- 详细规则见 [`AGENTS.md`](AGENTS.md)。

---

## 状态说明

项目仍在积极迭代。部分能力（如真实浏览器、搜索引擎）可能存在 stub / mock 实现，便于本地跑通主链路；生产使用前请替换为真实适配器并完善鉴权与沙箱隔离。

---

## License

以仓库内实际 License 文件为准。若暂无声明，默认仅供学习与研究使用。
