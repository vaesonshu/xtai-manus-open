# 项目规则约束

本项目致力于效仿 Manus 类通用智能体（General AI Agent）。以下规则约束所有代码生成、维护与重构工作，请严格遵循。

## 1. 项目定位

- 目标：构建一个 Manus 类通用智能体，具备任务规划、工具调用、多步骤执行与自主决策能力。
- 前后端分离：后端提供 AI Agent 能力与业务 API，前端提供交互界面。

## 2. 后端技术栈（FastAPI 全家桶）

- **Web 框架**：FastAPI
- **依赖注入**：FastAPI 的 Depends
- **数据校验**：Pydantic v2
- **ORM / 数据库**：SQLAlchemy（可配合 async）
- **数据库迁移**：Alembic
- **异步任务**：Celery（如需要）
- **缓存**：Redis
- **API 文档**：FastAPI 自动生成的 OpenAPI / Swagger UI

## 3. 后端架构设计（DDD 领域驱动设计）

后端必须遵循 DDD（Domain-Driven Design，领域驱动设计）分层架构，严格遵守以下原则：

### 3.1 分层结构

- **Domain 层（领域层）**：核心业务逻辑、实体（Entity）、值对象（Value Object）、领域事件（Domain Event）、聚合根（Aggregate Root）、领域服务（Domain Service）。该层不依赖任何外部框架与基础设施。
- **Application 层（应用层）**：用例（Use Case）、应用服务（Application Service）、DTO、命令/查询（CQRS 可选）。负责编排领域对象，不包含业务规则。
- **Infrastructure 层（基础设施层）**：数据库持久化（Repository 实现）、外部服务调用、消息队列、缓存等具体实现。负责实现领域层定义的接口。
- **Interface 层（接口层 / 表现层）**：FastAPI 路由、控制器、请求/响应模型。负责接收 HTTP 请求并转换为应用层调用。

### 3.2 DDD 原则

- 领域逻辑必须集中在 Domain 层，不得泄漏到 Application 或 Interface 层。
- Repository 接口定义在 Domain 层，具体实现在 Infrastructure 层（依赖倒置）。
- 实体与聚合根封装业务不变量（invariant），通过方法修改状态，避免贫血模型。
- 跨聚合的修改通过领域事件或领域服务完成，保证一致性边界。
- 应用层保持薄，只做流程编排与事务边界控制。

## 4. 前端技术栈（Next.js + shadcn/ui）

- **框架**：Next.js（App Router）
- **组件库**：shadcn/ui（基于 Radix UI + Tailwind CSS）
- **图标库**：lucide-react（与 shadcn/ui 配套的图标库）
- 使用 shadcn/ui 约定的组件组织方式：组件位于 `components/ui/` 目录，通过 CLI 添加。
- 遵循 React 组合模式与性能最佳实践（见项目内 `.agents/skills/` 相关规范）。

### 4.1 Prettier 格式规范（强制）

生成的前端代码必须严格遵守项目根目录 `.prettierrc` 的格式规范，不得违反。具体要求如下：

- **行尾符（endOfLine）**：`lf`（Unix 换行符），不使用 CRLF。
- **分号（semi）**：`false`，语句末尾不添加分号。
- **引号（singleQuote）**：`false`，字符串统一使用双引号。
- **缩进（tabWidth）**：`2`，使用 2 个空格缩进。
- **尾随逗号（trailingComma）**：`es5`，按 ES5 兼容规则保留尾随逗号（对象、数组、多行参数）。
- **每行最大宽度（printWidth）**：`80`，超过 80 列时按 Prettier 规则换行。
- **Tailwind CSS 插件**：启用 `prettier-plugin-tailwindcss`，Tailwind 类名将自动排序；样式表来源为 `packages/ui/src/styles/globals.css`。
- **Tailwind 函数**：`cn`、`cva` 会被识别为类名合并函数并对其内的类名排序。
- 生成的代码若与上述规范冲突，一律以 `.prettierrc` 为准，并在提交前使用 `prettier` 进行格式化校验。

## 5. 代码注释规范（强制）

- **所有生成的代码必须附带注释**，便于理解与维护。
- 注释应解释「为什么」（意图、权衡、约束），而非简单复述「做了什么」。
- 每个模块、类、函数、复杂逻辑块均需添加注释。
- 后端注释使用中文或英文均可，但需保持一致风格；关键业务逻辑建议使用中文说明。

## 6. AI Agent 框架（LangChain / LangGraph）

后端 AI 智能体的开发**全程使用 LangChain / LangGraph 框架**：

- **LangChain**：用于模型调用、Prompt 管理、工具（Tool）封装、RAG（检索增强生成）、记忆（Memory）等基础能力。
- **LangGraph**：用于构建智能体的有状态、多步骤执行图（StateGraph），实现任务规划、循环执行、条件分支、工具调用循环（Agent Loop）等。
- Agent 的规划、执行、反思等核心流程应使用 LangGraph 的状态图（Graph）建模。
- 工具调用统一通过 LangChain 的 Tool 接口封装，便于智能体动态选择与调用。

## 7. 总体要求

- 严格遵守上述技术栈与架构约束，不得擅自引入替代方案（除非用户明确指示）。
- 编写任何代码前，先阅读相关文档（如 `node_modules/next/dist/docs/` 下的 Next.js 指南、FastAPI / LangChain / LangGraph 官方文档）。
- 保持代码可读性、可维护性与可测试性。
