# xtai-api

FastAPI + **DDD（领域驱动设计）** 后端，目标是用 LangChain / LangGraph 生态构建一个类 Manus 的自主智能体（Autonomous Agent）。

## 技术栈

| 层 | 技术 |
| --- | --- |
| Web 框架 | FastAPI + Uvicorn |
| 数据校验 | Pydantic v2 + pydantic-settings |
| 业务数据库 | PostgreSQL + SQLAlchemy + Alembic |
| 缓存 | Redis |
| Agent 编排 | LangGraph（StateGraph + Checkpointer） |
| LLM | LangChain + langchain-openai（任意 OpenAI 兼容端点） |
| 状态持久化 | langgraph-checkpoint-sqlite |
| 依赖管理 | uv |

## 目录结构（DDD 分层）

```
apps/api
├── domain/            # 领域层：核心业务实体、值对象、领域事件、仓库接口（纯 Python，零框架依赖）
│   ├── agent/         #   agent 聚合根、任务、状态、事件
│   └── ports/         #   仓库 / 事件总线等端口（抽象协议）
├── application/       # 应用层：用例编排、命令与处理器、DTO
│   └── agent/
├── infrastructure/    # 基础设施层：LangGraph 图实现、LLM 适配器、配置、依赖注入、持久化
│   ├── llm/
│   ├── langgraph/
│   ├── persistence/
│   └── config.py
├── presentation/      # 表现层：FastAPI 路由、Schema、依赖
│   ├── api/
│   └── deps.py
├── main.py            # 应用入口 + 生命周期
└── tests/             # 测试
```

### 依赖方向（DDD 铁律）

```
presentation ──▶ application ──▶ domain ◀── infrastructure
                    ▲
                    └────────────── infrastructure（实现端口，运行时注入）
```

- `domain` 不依赖任何外部框架，只定义**领域模型**和**端口（Protocol）**。
- `application` 编排用例，调用端口，不关心具体实现。
- `infrastructure` 实现端口（LangGraph 图、LLM、PostgreSQL 仓库、Redis 缓存、SQLite checkpointer），通过依赖注入在启动时装配。
- `presentation` 只负责 HTTP 协议转换，调用应用层服务。

## 快速开始

```bash
cd apps/api

# 1. 安装依赖（会自动创建 .venv）
uv sync

# 2. 一键启动 Redis 与 PostgreSQL（推荐，在项目根目录执行）
cd ../..
docker compose up -d
cd apps/api

# 或分别启动，见下方「Redis 与 PostgreSQL 启动指南」
# 3. 配置环境变量
cp .env.example .env
# 编辑 .env，填入 LLM 端点、API Key，以及 Redis / PostgreSQL 连接信息

# 4. 执行数据库迁移
uv run alembic upgrade head

# 5. 启动开发服务器
uv run uvicorn main:app --reload
```

启动后访问：

- Swagger UI: http://localhost:8000/docs
- 健康检查: http://localhost:8000/health

## Redis 与 PostgreSQL 启动指南

本地开发推荐使用 Docker 启动依赖服务。若未安装 Docker，也可使用本机已安装的 Redis / PostgreSQL，并在 `.env` 中调整连接地址。

### 一键启动（Docker Compose）

项目根目录已提供 `docker-compose.yml`，可同时启动 Redis 与 PostgreSQL：

```bash
# 在项目根目录执行
docker compose up -d
```

查看服务状态：

```bash
docker compose ps
```

验证连接：

```bash
docker exec xtai-redis redis-cli ping
# 期望输出：PONG

docker exec xtai-postgres psql -U postgres -d xtai -c "SELECT 1"
# 期望输出：1 行记录
```

首次启动后，在 `apps/api` 目录执行数据库迁移：

```bash
cd apps/api
uv run alembic upgrade head
```

停止服务：

```bash
docker compose down
```

清除数据卷（会删除 Redis / PostgreSQL 持久化数据）：

```bash
docker compose down -v
```

默认连接信息与 `infrastructure/config.py` 中的配置一致，一般无需修改 `.env`：

| 服务 | 地址 |
| --- | --- |
| Redis | `redis://localhost:6379/0` |
| PostgreSQL | `postgresql+psycopg://postgres:postgres@localhost:5432/xtai` |

若修改了 Compose 中的端口或账号，请同步更新 `.env` 中的 `REDIS_URL` 与 `DATABASE_URL`。

### 分别启动 Redis（缓存）

```bash
docker run -d \
  --name xtai-redis \
  -p 6379:6379 \
  redis:7-alpine
```

验证连接：

```bash
docker exec -it xtai-redis redis-cli ping
# 期望输出：PONG
```

相关环境变量（`.env`）：

| 配置项 | 默认值 | 说明 |
| --- | --- | --- |
| `REDIS_ENABLED` | `true` | 是否启用 Redis 缓存 |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis 连接地址 |
| `REDIS_KEY_PREFIX` | `xtai` | 缓存键前缀 |
| `REDIS_DEFAULT_TTL` | `300` | 默认过期时间（秒） |

设为 `REDIS_ENABLED=false` 可关闭缓存，应用将直接访问底层仓库。

### 分别启动 PostgreSQL（业务数据库）

```bash
docker run -d \
  --name xtai-postgres \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=xtai \
  -p 5432:5432 \
  postgres:16-alpine
```

首次启动后执行迁移：

```bash
cd apps/api
uv run alembic upgrade head
```

验证连接（可选）：

```bash
docker exec -it xtai-postgres psql -U postgres -d xtai -c "\dt"
# 迁移成功后应能看到 agent_runs 表
```

相关环境变量（`.env`）：

| 配置项 | 默认值 | 说明 |
| --- | --- | --- |
| `DATABASE_ENABLED` | `true` | 是否启用 PostgreSQL |
| `DATABASE_URL` | `postgresql+psycopg://postgres:postgres@localhost:5432/xtai` | 数据库连接串 |
| `DATABASE_ECHO` | `false` | 是否打印 SQL 日志 |

设为 `DATABASE_ENABLED=false` 时，业务数据将回退到内存仓库（仅适合本地快速调试）。

### 健康检查

`GET /health` 会返回 Redis 与 PostgreSQL 的状态（`ok` / `disabled` / `error`）。任一依赖异常时，整体状态为 `degraded`：

```json
{
  "status": "ok",
  "service": "xtai-api",
  "env": "development",
  "redis": "ok",
  "database": "ok"
}
```

## 核心 API

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `GET` | `/health` | 健康检查 |
| `POST` | `/v1/agents/runs` | 发起一次 agent 运行（异步编排） |
| `GET` | `/v1/agents/runs/{run_id}` | 查询运行状态与结果 |
| `POST` | `/v1/agents/runs/{run_id}/stream` | 流式执行（SSE） |

## 架构说明

- **领域层** `AgentRun` 是聚合根，封装任务的完整生命周期（`created → running → completed/failed`）与领域事件（`AgentRunStarted`、`AgentRunCompleted` 等）。
- **应用层** 提供 `StartAgentRun` 用例，负责校验、装配、调用端口，不泄露框架细节。
- **基础设施层** 的 `LangGraphAgent` 用 StateGraph 实现 agent 循环（`planner → executor → reflection`），并用 SQLite checkpointer 做状态持久化与断点续跑。
- 后续扩展（多 agent、工具调用、记忆系统）都在不破坏领域层的前提下，通过替换/新增基础设施适配器完成。

## 日志系统

日志在应用启动时由 `infrastructure/logging_.py` 的 `setup_logging()` 统一装配，通过 `.env` 中的 `LOG_*` 配置项控制：

| 配置项 | 默认值 | 说明 |
| --- | --- | --- |
| `LOG_LEVEL` | `INFO` | 日志等级（`DEBUG`/`INFO`/`WARNING`/`ERROR`/`CRITICAL`） |
| `LOG_FORMAT` | `text` | 输出格式：`text`（人类可读）/ `json`（结构化） |
| `LOG_CONSOLE_ENABLED` | `true` | 是否输出到控制台 |
| `LOG_FILE_ENABLED` | `true` | 是否输出到文件 |
| `LOG_FILE_PATH` | `./data/logs/app.log` | 日志文件路径 |
| `LOG_FILE_MAX_BYTES` | `10485760` | 单文件最大字节数（滚动切割） |
| `LOG_FILE_BACKUP_COUNT` | `5` | 保留的历史日志文件数 |
| `LOG_COLORS` | `true` | 控制台是否彩色输出 |

使用方式：各模块通过 `logging.getLogger(__name__)` 获取 logger，无需手动配置。JSON 格式额外支持在 `extra` 中携带 `request_id`、`run_id` 等结构化字段，便于日志采集与检索。
