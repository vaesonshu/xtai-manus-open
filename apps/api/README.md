# xtai-api

FastAPI + **DDD（领域驱动设计）** 后端，目标是用 LangChain / LangGraph 生态构建一个类 Manus 的自主智能体（Autonomous Agent）。

## 技术栈

| 层 | 技术 |
| --- | --- |
| Web 框架 | FastAPI + Uvicorn |
| 数据校验 | Pydantic v2 + pydantic-settings |
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
- `infrastructure` 实现端口（LangGraph 图、LLM、SQLite checkpointer），通过依赖注入在启动时装配。
- `presentation` 只负责 HTTP 协议转换，调用应用层服务。

## 快速开始

```bash
cd apps/api

# 1. 安装依赖（会自动创建 .venv）
uv sync

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env，填入你的 LLM 端点与 API Key

# 3. 启动开发服务器
uv run uvicorn main:app --reload
```

启动后访问：

- Swagger UI: http://localhost:8000/docs
- 健康检查: http://localhost:8000/health

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
