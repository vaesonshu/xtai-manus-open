# xtai-manus-open

开源的 **Manus 类通用智能体（General AI Agent）**：任务规划、多角色分步执行、ReAct 工具循环、人机协作与 SSE 实时流式反馈。

前后端分离的 monorepo：

| 包 | 路径 | 说明 |
| --- | --- | --- |
| 后端 API | `apps/api` | FastAPI + DDD + LangChain / LangGraph |
| 前端 Web | `apps/web` | Next.js App Router + shadcn/ui |
| 共享 UI | `packages/ui` | Radix + Tailwind 组件库 |

更细的后端说明见 [`apps/api/README.md`](apps/api/README.md)；架构与编码约束见 [`AGENTS.md`](AGENTS.md)。

---

## 功能概览

| 能力 | 说明 |
| --- | --- |
| 任务规划 | 支持 LLM 在线规划或离线三步规划；可按配置在每步后动态重规划 |
| 多角色执行 | Coordinator / Researcher / Coder / Reviewer 等角色，按步骤绑定不同工具集 |
| ReAct 循环 | 单步内 LLM ↔ 工具迭代，产出结构化步骤结果 |
| LangGraph 编排 | 默认 `StateGraph` 驱动规划→执行→等待→汇总；可切换为应用层 ReAct 循环 |
| 工具系统 | Shell、文件、百度搜索、HTTP 浏览器、计算、时间、用户交互等 |
| 人机协作 | `message_ask_user` 触发 WAITING，用户回复后断点续跑 |
| 记忆 | 工作记忆 + 情景记忆，支持压缩与用户输入回滚 |
| 流式 UI | SSE 推送 plan / step / message / tool / title / wait / done |
| 工具工作区 | 搜索结果列表、浏览器页面预览、文件内容、截图等结构化展示 |
| 基础设施 | PostgreSQL 业务库、Redis 缓存与任务流、LangGraph Checkpointer（Postgres / SQLite） |

---

## 前端界面

Manus 风格三栏布局（`TaskShell`）：

- **左侧**：历史任务侧栏，本地持久化（`localStorage`），按最近活动时间排序
- **中间**：欢迎页 / 对话时间线（消息、步骤卡片、工具调用标签）
- **右侧**：工具工作区（参数、结构化结果、执行状态）
- **设置页** `/settings`：LLM 端点、模型、API Key 等配置

开发环境下，SSE 订阅默认直连 `http://127.0.0.1:8000`，避免 Next 代理缓冲事件流；普通 REST 可走同源 `/api` 代理。

---

## 技术栈

| 区域 | 技术 |
| --- | --- |
| 前端 | Next.js 16、React 19、shadcn/ui、Tailwind CSS 4、lucide-react |
| 后端 | FastAPI、Pydantic v2、SQLAlchemy、Alembic、[uv](https://github.com/astral-sh/uv) |
| Agent | LangChain、LangGraph（StateGraph + Checkpointer）、OpenAI 兼容端点 |
| 数据 | PostgreSQL 16、Redis 7 |
| 工程 | pnpm workspace、Turborepo、Docker Compose |

---

## 仓库结构

```text
xtai-manus-open/
├── apps/
│   ├── api/                 # FastAPI 后端（DDD）
│   │   ├── domain/          # 实体、值对象、领域事件、端口
│   │   ├── application/     # 用例：Task、Planning、ReAct、LLM…
│   │   ├── infrastructure/  # LangGraph、LLM、工具、搜索、浏览器、持久化
│   │   ├── presentation/    # 路由、Schema、SSE 契约校验
│   │   └── tests/
│   └── web/                 # Next.js 前端
│       ├── app/             # 首页、/tasks/[taskId]、/settings
│       ├── components/task/ # 侧栏、时间线、工具面板等
│       ├── hooks/           # useTaskSession
│       └── lib/             # api-client、task-reducer、tool-display
├── packages/
│   ├── ui/                  # 共享 shadcn 组件
│   ├── eslint-config/
│   └── typescript-config/
├── docker-compose.yml       # Redis + PostgreSQL
├── AGENTS.md                # 项目规则与 DDD 约束
└── package.json             # pnpm + turbo 根脚本
```

后端依赖方向（DDD）：

```text
presentation ──▶ application ──▶ domain ◀── infrastructure
```

---

## 执行流程（简版）

```text
用户输入 goal
  → POST /v1/tasks
  → TaskExecution（LangGraph 或 ReAct 编排）
  → 规划 → 逐步执行（StepExecutor → ReActExecutor）
  → 事件写入 output_stream（Redis 或内存队列）
  → GET /v1/tasks/{id}/stream（SSE）推送到前端
  → 需要用户时 wait + WAITING，POST reply 后续跑
  → 完成后 summarize 并推送 done
```

---

## 内置工具

按角色动态授权，完整列表在 `application/agent/role_config.py`。

| 工具 | 说明 |
| --- | --- |
| `search_web` | 百度搜索（默认 `SEARCH_ENGINE=baidu`，可改 `mock`） |
| `browser_navigate` / `browser_view` | HTTP 抓取页面正文（默认 `BROWSER_BACKEND=http`） |
| `read_file` / `write_file` / `replace_in_file` / `search_in_file` / `find_files` | 本地沙箱文件操作 |
| `shell_execute` / `shell_read_output` | 本地 Shell 沙箱 |
| `calculate` | 安全数学表达式计算 |
| `get_current_time` | 当前时间 |
| `message_ask_user` / `message_notify_user` | 向用户提问或通知 |
| `echo` | 测试用回显（Executor 角色） |

工具结果经 `tool_content` 下发结构化载荷，前端对搜索、浏览器、文件等做富展示。

---

## 快速开始

### 环境要求

- Node.js ≥ 20、pnpm ≥ 10
- Python ≥ 3.10、[uv](https://github.com/astral-sh/uv)
- Docker（推荐，用于 Redis / PostgreSQL）

### 1. 安装依赖

```bash
git clone https://github.com/vaesonshu/xtai-manus-open.git
cd xtai-manus-open
pnpm install
```

### 2. 启动基础设施

在项目根目录：

```bash
docker compose up -d
```

| 服务 | 地址 |
| --- | --- |
| Redis | `redis://localhost:6379/0` |
| PostgreSQL | `postgresql+psycopg://postgres:postgres@localhost:5433/xtai` |

> Windows 若本机已有 PostgreSQL（占用 5432），Compose 将容器映射到宿主机 **5433**。

### 3. 配置并启动后端

```bash
cd apps/api
uv sync

# 新建 .env（按需修改）
cat > .env << 'EOF'
OPENAI_API_KEY=sk-your-key
OPENAI_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4o-mini

REDIS_ENABLED=true
REDIS_URL=redis://localhost:6379/0
DATABASE_ENABLED=true
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5433/xtai

AGENT_ORCHESTRATOR=langgraph
AGENT_USE_LLM_PLANNING=true
SEARCH_ENGINE=baidu
BROWSER_BACKEND=http
EOF

uv run alembic upgrade head
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

- Swagger：http://localhost:8000/docs
- 健康检查：http://localhost:8000/health（含 Redis、DB、checkpoint、orchestrator 状态）

`OPENAI_BASE_URL` 可指向任意 OpenAI 兼容服务。

Windows 下若 PowerShell 将 uvicorn 的 INFO 日志标红，可改用：

```bash
python -m uvicorn main:app --reload
```

### 4. 启动前端

在仓库根目录（`pnpm dev` 仅启动 Web；API 需单独运行）：

```bash
pnpm --filter web dev
```

浏览器打开 http://localhost:3000 。

可选环境变量：

| 变量 | 说明 |
| --- | --- |
| `API_URL` | Next 服务端 rewrite 目标（默认 `http://127.0.0.1:8000`） |
| `NEXT_PUBLIC_API_URL` | 浏览器侧 API 根路径；设置后 REST 与 SSE 均直连该地址 |

### 5. curl 验证后端

```bash
# 创建任务
curl -s -X POST http://localhost:8000/v1/tasks \
  -H "Content-Type: application/json" \
  -d '{"goal": "用一句话介绍这个项目"}'

# 订阅 SSE（替换 task_id）
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

## 常用配置

`apps/api/.env` 中与 Agent 相关的主要项（完整列表见 `infrastructure/config.py`）：

| 配置项 | 默认 | 说明 |
| --- | --- | --- |
| `AGENT_ORCHESTRATOR` | `langgraph` | `langgraph` 或 `react` |
| `AGENT_USE_LLM_PLANNING` | `true` | 是否 LLM 在线规划 |
| `AGENT_REPLAN_AFTER_EACH_STEP` | `false` | 每步完成后是否重规划 |
| `CHECKPOINT_BACKEND` | `auto` | DB 开启时用 Postgres，否则 SQLite |
| `SEARCH_ENGINE` | `baidu` | `baidu` 或 `mock` |
| `BROWSER_BACKEND` | `http` | `http` 或 `stub` |
| `REDIS_ENABLED` / `DATABASE_ENABLED` | `true` | 关闭后回退内存实现（仅适合本地调试） |

---

## 核心 API

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `GET` | `/health` | 健康检查 |
| `POST` | `/v1/tasks` | 提交 goal，后台执行 |
| `GET` | `/v1/tasks/{task_id}` | 任务状态与规划 |
| `GET` | `/v1/tasks/{task_id}/stream` | SSE 事件流 |
| `POST` | `/v1/tasks/{task_id}/reply` | WAITING 状态下用户回复 |
| `GET` / `PUT` | `/v1/llm/config` | LLM 配置读写 |
| `POST` / `GET` | `/v1/agents/runs` … | **遗留接口**，薄封装至 `/v1/tasks` |

### SSE 事件类型

| `type` | 说明 |
| --- | --- |
| `plan` | 规划创建或更新（含 `status`） |
| `step` | 步骤状态变化 |
| `message` | 用户 / 助手消息（支持 `partial` 流式） |
| `tool` | 工具调用（`calling` / `called`，含 `tool_content`） |
| `title` | 任务标题更新 |
| `wait` | 等待用户输入 |
| `error` | 错误 |
| `done` | 任务结束 |

---

## 测试

后端：

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

- 后端遵循 DDD：领域逻辑集中在 `domain/`，应用层只做编排。
- Agent 能力通过 LangChain Tool + `ToolRegistry` 扩展；编排优先 LangGraph。
- 前端格式遵循根目录 `.prettierrc`（LF、无分号、双引号、2 空格、printWidth 80）。
- 详细规则见 [`AGENTS.md`](AGENTS.md)。

---

## 当前状态

项目处于积极迭代中，已具备端到端任务执行与 Web 控制台。以下能力有明确边界：

- **浏览器**：HTTP 抓取 HTML 正文，不执行 JavaScript；复杂站点可能需后续接入 Playwright 等。
- **搜索**：默认百度网页抓取，可能触发风控；可切换 `SEARCH_ENGINE=mock` 做离线调试。
- **沙箱**：本地 Shell / 文件沙箱，生产环境需加强隔离与鉴权。
- **遗留 API**：`/v1/agents/*` 保留兼容，新集成请使用 `/v1/tasks`。

欢迎 Issue 与 PR。

---

## License

仓库内暂无独立 License 文件；默认仅供学习与研究使用。商用或再分发前请自行确认合规性。
