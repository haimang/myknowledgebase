# smind-family 重构为 Python 模块化单体的技术报告

## 0. 文档目标

本文用于明确 `smind-family` 从当前 Cloudflare 多 Worker 流水线架构，重构为 **本地 Python 模块化单体** 时的技术选型、架构原则、组件通信方式、数据存储适配策略与实施建议。

本文不是迁移执行清单，而是 **技术路线定稿文档**。核心目标是回答四个问题：

1. 为什么主体语言选择 Python；
2. 为什么用 SQLite 作为状态内核而不是继续使用 queue；
3. 为什么用本地 `sqlite-vec/vec1 extension` 替代 Cloudflare Vectorize；
4. 在单体前提下，各组件之间应该如何通信、如何存储、如何保持分段处理与状态控制。

---

## 1. 执行结论

**最终技术路线：**

1. **Python** 作为主体语言；
2. **SQLite** 作为关系数据、工作流状态与任务分配内核；
3. **sqlite-vec / vec1 extension** 作为本地向量存储；
4. **模块化单体 + monorepo** 作为工程组织方式；
5. **显式阶段状态机** 替代 Cloudflare Queue / callback / service binding；
6. **本地对象存储适配层** 替代 R2；
7. **本地配置与 Prompt Registry** 替代 KV；
8. **本地 worker claim/lease 机制** 替代 Durable Object + queue consumer。

**一句话定义未来目标架构：**

> `smind-family` 将被重构为一个 Python 模块化单体，其内部使用 SQLite 驱动多阶段工作流状态机，通过 sqlite-vec 存储向量，通过本地文件系统存储对象，通过组件边界而非部署边界来实现独立演进。

---

## 2. 为什么选择 Python

## 2.1 选择 Python 的核心原因

当前重构的主问题，不是“单机极限吞吐”，而是：

1. 把分布式异步流程收敛为本地可控状态机；
2. 把 clean / rag / vectorizer 能力模块化；
3. 把文件、网页、API、文本、embedding、结构化处理统一到一个运行时中；
4. 保证未来仍然能快速演进 prompt、解析策略、阶段流转规则与 provider 适配。

在这个问题空间里，Python 的综合适配度最高。

## 2.2 Python 相比 Go 的判断

Go 的强项在：

1. 单二进制部署；
2. 并发调度；
3. 长期驻留服务稳定性；
4. 更适合被桌面/移动应用携带为本地引擎。

但当前阶段选择 Python 仍然更合理，原因是：

1. **这次重构本质是工作流与数据处理重构，不是部署优化；**
2. **clean / rag / embedding / parsing / browser / PDF / HTML 等生态在 Python 中明显更成熟；**
3. **SQLite + Python 的开发摩擦更低；**
4. **后续需要频繁修改 pipeline 与推理策略，Python 的迭代成本更低。**

因此当前阶段的最优判断是：

| 维度 | Python | Go | 结论 |
| --- | --- | --- | --- |
| 工作流重构速度 | 强 | 中 | Python 优势明显 |
| 文档/网页/AI/RAG 生态 | 强 | 中 | Python 更适合当前业务 |
| SQLite 集成体验 | 强 | 强 | 两者都可行 |
| 本地二进制分发 | 中 | 强 | Go 更强 |
| 移动/桌面嵌入 | 中 | 强 | Go 更强 |
| 当前阶段总体适配 | **最高** | 高 | **选 Python** |

**结论：当前选择 Python 是为了解决“正确重构”和“快速演进”的主矛盾。**

---

## 3. 重构后的目标架构

## 3.1 架构原则

重构后不再保留当前的“多服务部署拓扑”，但保留当前系统最有价值的三层抽象：

1. **控制面抽象**：入口、用户、团队、管理、工作流启动；
2. **编排器抽象**：clean workflow 与 rag workflow 的阶段状态机；
3. **执行器抽象**：cleaners / providers / structurizer / constructor / vectorizer。

重构后的总原则如下：

1. **去掉服务边界，保留模块边界；**
2. **去掉 queue，保留异步阶段语义；**
3. **去掉 callback HTTP，保留 callback 的状态合并语义；**
4. **去掉 Durable Object，保留 claim/lease/串行控制语义；**
5. **去掉平台绑定，保留业务协议与状态模型。**

## 3.2 目标运行形态

未来运行时建议收敛为：

```text
Client / CLI / Local App
  -> Python API Layer
  -> Workflow Engine
  -> Stage Scheduler
  -> Clean Workers / RAG Workers / Vector Workers
  -> SQLite + sqlite-vec + Local Object Store
```

这里的重点是：

1. **业务仍然是多阶段并发处理；**
2. **但并发协调由 SQLite 状态内核管理；**
3. **组件之间优先走进程内调用，异步边界通过数据库状态推进。**

---

## 4. 技术栈选择

## 4.1 主体技术栈

建议技术栈如下：

| 层 | 技术 | 选择理由 |
| --- | --- | --- |
| 主语言 | Python 3.12+ | 生态成熟，适合 AI/RAG/解析/工作流重构 |
| HTTP/API | FastAPI | 声明式接口、类型友好、适合本地 API 面 |
| 数据建模 | Pydantic v2 | 输入输出 schema、内部 command/event 契约 |
| ORM/SQL | SQLAlchemy 2.x | 对 SQLite 控制力较强，便于事务管理 |
| DB Migration | Alembic | 管理 SQLite schema 演进 |
| 并发模型 | asyncio + 受控 worker loop | 适合 I/O 型清洗和阶段调度 |
| 本地任务执行 | 自研 scheduler，不引入 Celery | 当前目标是单机状态机，不是分布式队列系统 |
| 向量存储 | sqlite-vec / vec1 extension | 本地、轻量、与 SQLite 一体化 |
| 对象存储 | 本地文件系统适配层 | 替代 R2，简单稳定 |
| 浏览器能力 | Playwright | 替代当前 browser fetch/render 逻辑 |
| HTML 解析 | selectolax / BeautifulSoup / lxml | 通用内容抽取 |
| PDF/文档抽取 | pypdf / pymupdf / unstructured | 处理文件 ingestion |
| LLM/Embedding | Adapter 封装 OpenAI/Gemini/本地模型 | 与业务解耦 |
| 日志 | structlog / logging | 保留结构化日志 |
| 测试 | pytest | 简洁直接 |

## 4.2 不建议引入的技术

当前阶段不建议引入：

1. Celery / Redis 队列；
2. Kafka / NATS / RabbitMQ；
3. 重新拆分为多个独立 Python 微服务；
4. 过早引入 PostgreSQL；
5. 过早引入外部向量数据库。

原因很简单：这次重构的目标是 **本地模块化单体**，而不是“换一套基础设施继续微服务化”。

---

## 5. 工程组织方式：monorepo + 模块化单体

## 5.1 总体原则

虽然运行时是单体，但工程组织应模块化，这样才能：

1. 独立演进清洗器；
2. 独立演进 RAG 能力；
3. 独立演进存储与向量层；
4. 独立维护 API 层与工作流引擎。

## 5.2 建议目录结构

建议收敛为类似下面的 monorepo 结构：

```text
smind-family/
  apps/
    api/
    worker/
    cli/
  packages/
    common/
    contracts/
    config/
    storage_sqlite/
    storage_objects/
    vector_sqlite_vec/
    workflow_core/
    workflow_clean/
    workflow_rag/
    auth/
    team/
    ingestion/
    management/
    cleaners_universal/
    providers_dedicated/
    rag_structurizer/
    rag_constructor/
    rag_vectorizer/
    llm_adapters/
    browser_runtime/
  docs/
    eval/
```

## 5.3 运行时边界与代码边界

运行时建议保留为少量进程：

1. `apps/api`：对外提供 HTTP / CLI 控制面；
2. `apps/worker`：本地阶段调度与执行；
3. `apps/cli`：本地维护、debug、restart、purge 工具。

但模块边界应体现在 `packages/` 中，而不是体现在“每个模块一个部署单元”。

---

## 6. 组件映射：从当前目录到 Python 模块

| 当前目录 | 新模块建议 | 说明 |
| --- | --- | --- |
| `smind-admin/` | `packages/auth`, `packages/team`, `packages/ingestion`, `packages/management`, `apps/api` | 控制面拆成多个领域包 |
| `smind-clean-dispatcher/` | `packages/workflow_clean` | clean 阶段状态机 |
| `smind-rag-dispatcher/` | `packages/workflow_rag` | rag 阶段状态机 |
| `smind-skill-clean-universal/` | `packages/cleaners_universal` | 通用 clean 执行器 |
| `smind-skill-clean-dedicated-apis/` | `packages/providers_dedicated` | provider/API 执行器 |
| `smind-skill-rag-structurizer/` | `packages/rag_structurizer` | 结构化处理模块 |
| `smind-skill-rag-constructor/` | `packages/rag_constructor` | chunk/summary/layer 构造模块 |
| `smind-skill-rag-vectorizer/` | `packages/rag_vectorizer`, `packages/vector_sqlite_vec` | 向量化与本地索引模块 |
| Cloudflare bindings | `packages/config`, `packages/storage_*`, `packages/llm_adapters` | 平台能力改成本地适配层 |

---

## 7. 组件间通信：新的基本规则

## 7.1 通信原则

重构后，组件间不再通过：

1. HTTP service binding；
2. Cloudflare Queue；
3. callback HTTP 回调；
4. Durable Object endpoint；

来完成主业务通信。

新的通信规则应分为两类：

### A. 同步通信：进程内函数调用

适用于：

1. API 层调用工作流启动器；
2. 工作流层读取配置与注册表；
3. 执行器调用 parser / llm adapter / object storage adapter；
4. 管理接口发起 restart / purge。

### B. 异步通信：数据库驱动的状态推进

适用于：

1. clean 阶段任务领取；
2. rag 阶段任务领取；
3. vectorizer 串行阶段控制；
4. 长任务的 retry / restart / lease 续租。

也就是说，**模块间传值优先走内存；阶段间推进优先走 SQLite 状态。**

---

## 8. SQLite 作为工作流内核

## 8.1 为什么 SQLite 不只是数据库

在这次重构中，SQLite 不能只扮演“把数据存下来”的角色。  
它必须同时承担：

1. 工作流状态中心；
2. 任务分配中心；
3. 失败恢复中心；
4. restart / purge / replay 控制中心；
5. 轻量事件日志中心。

因此应把 SQLite 定位为：

> **workflow kernel**

## 8.2 必须满足的能力

SQLite 层必须支持：

1. `workflow` 与 `step` 状态记录；
2. 按阶段查询待处理任务；
3. worker claim/lease 机制；
4. step attempt / retry 次数记录；
5. artifact 关联；
6. restart / replay 控制；
7. purge 操作；
8. 审计和调试。

## 8.3 建议核心表

建议最少包含以下核心表：

| 表名 | 作用 |
| --- | --- |
| `workflow_runs` | 一次完整业务流程实例 |
| `workflow_steps` | 每个阶段的 step 节点 |
| `step_attempts` | step 的执行尝试记录 |
| `task_claims` | 任务租约、领取、心跳、超时控制 |
| `artifacts` | 文件、中间产物、结构化结果、JSON、文本等 |
| `sources` | 原始输入源，例如 file/url/api |
| `documents` | clean 后的主文档对象 |
| `vector_chunks` | chunk 与 embedding 元数据 |
| `events` | 工作流事件审计日志 |
| `configs` | 配置与 prompt registry 版本记录 |

## 8.4 建议状态模型

### `workflow_runs.status`

建议包含：

1. `pending`
2. `running`
3. `completed`
4. `failed`
5. `paused`
6. `cancelled`
7. `purged`

### `workflow_steps.status`

建议包含：

1. `pending`
2. `claimed`
3. `running`
4. `succeeded`
5. `failed`
6. `retry_wait`
7. `cancelled`
8. `skipped`

### `task_claims.status`

建议包含：

1. `active`
2. `expired`
3. `released`
4. `finished`

---

## 9. 任务分配：如何替代 Queue

## 9.1 总原则

我们不再引入 queue，但也不能退化成单线程串行处理。  
因此必须实现：

> **阶段化并发 + SQLite claim/lease 调度**

也就是：

1. 不同阶段可以并发执行；
2. 同一阶段可以有多个 worker 并发 claim；
3. 每个 step 在任一时刻只能被一个 worker 持有；
4. 若 worker 崩溃，lease 过期后其他 worker 可以接管。

## 9.2 推荐执行模型

每类 worker 启动自己的 polling loop，例如：

| Worker 类型 | 负责阶段 |
| --- | --- |
| `clean-universal-worker` | 通用清洗 |
| `clean-dedicated-worker` | 专用 provider 清洗 |
| `rag-structurizer-worker` | 结构化 |
| `rag-constructor-worker` | 构造 |
| `rag-vectorizer-worker` | 向量化 |

每个 worker loop 逻辑一致：

1. 查询自己可处理的 `workflow_steps`；
2. 通过事务 claim 一条或一批 step；
3. 执行；
4. 写回结果；
5. 推进下一阶段；
6. 更新 claim 为 finished；
7. 若失败则进入 retry 或 failed。

## 9.3 领取任务的事务语义

SQLite 没有原生分布式队列能力，因此任务领取必须靠事务保护。

建议模式：

1. `BEGIN IMMEDIATE`
2. 选取符合条件的 `pending` 或 `retry_wait` 且已到执行时间的 step
3. 检查其是否未被活跃 lease 占用
4. 更新为 `claimed`
5. 写入 `task_claims`
6. `COMMIT`

关键条件应包括：

1. `stage = ?`
2. `status IN ('pending', 'retry_wait')`
3. `available_at <= now`
4. `lease_expires_at IS NULL OR lease_expires_at < now`

## 9.4 为什么这比 queue 更适合当前目标

因为当前目标是本地单体，而不是分布式消息系统。  
使用 SQLite claim/lease 模式有几个明显好处：

1. 所有状态在一个地方；
2. restart/replay 更简单；
3. 调试时可以直接看表；
4. 不需要额外部署 Redis/RabbitMQ；
5. 对桌面本地运行更友好。

---

## 10. Clean 与 RAG 的分段通信方式

## 10.1 原始架构

当前架构中：

1. admin 触发 ingestion；
2. clean dispatcher 通过 queue 调用 cleaner；
3. cleaner callback 回到 clean dispatcher；
4. clean finalizer 再触发 rag dispatcher；
5. rag dispatcher 调 structurizer / constructor / vectorizer；
6. 各 skill 再 callback 回 rag dispatcher。

## 10.2 新架构

新架构下建议改造成：

```text
API -> create workflow_run + steps
   -> stage scheduler claims clean step
   -> cleaner 执行并写 artifacts
   -> workflow_clean finalizer 生成下一批 rag steps
   -> stage scheduler claims rag steps
   -> structurizer / constructor / vectorizer 执行
   -> workflow_rag finalizer 收敛状态
```

这里“callback”的含义不再是网络回调，而是：

> 执行器完成后，把结果写回数据库，并由工作流引擎在同一事务或后续事务中推进下一阶段。

## 10.3 推荐通信载体

建议组件间的业务通信用三层契约：

### 1. Command

用于启动动作，例如：

- `StartWorkflowCommand`
- `RestartWorkflowCommand`
- `PurgeWorkflowCommand`
- `ExecuteStepCommand`

### 2. Result

用于执行器返回，例如：

- `CleanStepResult`
- `StructurizeResult`
- `ConstructResult`
- `VectorizeResult`

### 3. Event

用于审计和异步观察，例如：

- `WorkflowStarted`
- `StepClaimed`
- `StepSucceeded`
- `StepFailed`
- `WorkflowCompleted`

这些契约建议都定义在 `packages/contracts` 中，由 Pydantic 统一建模。

---

## 11. 数据存储适配策略

## 11.1 D1 -> SQLite

Cloudflare D1 当前承担的是：

1. 用户与团队；
2. 文件与静态资源；
3. workflow 记录；
4. 状态追踪；
5. RAG 中间记录；
6. vectorizer 状态辅助。

迁移后统一改为 SQLite。

建议启用：

1. `PRAGMA journal_mode=WAL;`
2. `PRAGMA synchronous=NORMAL;`
3. `PRAGMA foreign_keys=ON;`
4. `PRAGMA busy_timeout=5000;`

并对热点表加索引，例如：

1. `workflow_steps(stage, status, available_at)`
2. `task_claims(step_id, status, lease_expires_at)`
3. `artifacts(workflow_run_id, artifact_type)`

## 11.2 R2 -> 本地对象存储

R2 迁移后建议抽象为：

```text
data/
  objects/
    raw/
    cleaned/
    structured/
    constructed/
    exports/
```

通过统一接口屏蔽底层实现：

```python
class ObjectStore(Protocol):
    def put_bytes(...)
    def get_bytes(...)
    def put_json(...)
    def get_json(...)
    def delete(...)
```

这样未来若需要切换到 S3 兼容对象存储，不需要改业务层。

## 11.3 Vectorize -> sqlite-vec / vec1 extension

当前 Vectorize 负责最终 embedding 索引。  
迁移后建议抽象为 `VectorStore`：

```python
class VectorStore(Protocol):
    def upsert_chunks(...)
    def delete_chunks(...)
    def search(...)
    def purge_document(...)
```

第一版实现基于 `sqlite-vec / vec1 extension`。

注意事项：

1. 向量层必须被适配器包裹，不能把 SQL 方言散落到业务代码里；
2. chunk 元数据仍然需要在普通表中维护；
3. purge/restart 不能只删向量，也要同步更新 chunk 状态表；
4. embedding 生成与向量写入应拆成两个明确子步骤，便于失败恢复。

## 11.4 KV -> 配置与 Prompt Registry

当前 KV 承担 prompt/config 发放角色。  
迁移后建议改为双层结构：

1. `packages/config/prompts/*.yaml`
2. SQLite `configs` 表记录版本、启用状态、变更时间

这样可以同时满足：

1. 本地文件可读；
2. 配置变更可追溯；
3. 工作流运行时可绑定配置版本。

---

## 12. Durable Object 的替代方案

当前最 Cloudflare 平台化的部分是 vectorizer 的 Durable Object。  
它承担的是：

1. 串行控制；
2. 任务入口；
3. restart/purge 的流程编排；
4. 状态一致性。

迁移后不需要保留 DO 本身，但必须保留其语义。

建议替代方式：

1. 使用 `workflow_steps + task_claims` 表表达串行执行；
2. 对 `vectorize` 阶段设置更严格的并发上限；
3. 把 `purge` 与 `restart` 实现为明确的管理命令；
4. 必要时给单文档或单 workflow 加逻辑互斥锁。

换句话说：

> Durable Object 被替换的不是“单一类”，而是一组 SQLite 状态规则。

---

## 13. 组件详细通信模型

## 13.1 API 层到工作流层

建议流转：

```text
HTTP Request
  -> API Router
  -> Service Layer
  -> WorkflowCommandHandler
  -> SQLite transaction
  -> create workflow_run / source / steps / artifacts
```

特点：

1. 启动命令同步返回；
2. 真正执行异步发生在 worker loop 中；
3. 前端/调用方通过 workflow id 查询状态。

## 13.2 工作流层到执行器

建议流转：

```text
Scheduler loop
  -> claim step
  -> load step payload
  -> choose executor by stage + action
  -> execute
  -> persist result
  -> finalize / enqueue next logical step
```

这里不再发生跨服务 RPC，而是在本地调用：

```python
executor = registry.resolve(step.stage, step.action)
result = await executor.execute(context, payload)
```

## 13.3 执行器到存储层

所有执行器都不直接操作原始 SQLite 连接或原始文件路径，而是通过统一 adapter：

1. `WorkflowRepository`
2. `ArtifactRepository`
3. `ObjectStore`
4. `VectorStore`
5. `ConfigRepository`
6. `LLMClient`

这样做的意义是：

1. 避免业务代码直接绑死基础设施；
2. 方便未来局部替换存储实现；
3. 方便测试时 mock。

---

## 14. 失败恢复、重试、restart、purge

## 14.1 重试

每个 step 都应具备：

1. `max_attempts`
2. `attempt_count`
3. `retry_backoff_seconds`
4. `available_at`

失败后不要立即丢弃，而是：

1. 写入 `step_attempts`
2. 更新 `workflow_steps.status = retry_wait`
3. 设置新的 `available_at`
4. 由调度器稍后重新 claim

## 14.2 restart

restart 不应被实现为“简单重新跑整个 workflow”。  
应支持至少三种粒度：

1. **workflow restart**：从指定阶段重新展开；
2. **step restart**：只重跑某个失败 step；
3. **downstream restart**：删除某阶段之后的产物并重跑后续。

建议把 restart 设计为管理命令：

- `RestartWorkflowCommand`
- `RestartStepCommand`

## 14.3 purge

purge 主要涉及：

1. 删除 vector chunks；
2. 删除/标记无效的构造产物；
3. 重置相关 step 状态；
4. 保留审计日志。

purge 不能只做“物理删除”，应保留逻辑审计。

---

## 15. 并发模型建议

## 15.1 总体判断

Python 可以满足当前需求，但必须采用**受控并发**，不能粗暴开大量线程/协程直接打 SQLite。

## 15.2 推荐模型

建议：

1. API 层使用标准异步 HTTP；
2. worker 侧按阶段启动固定数量的 poller；
3. 数据库事务尽量短；
4. 长时间处理不持有 DB 事务；
5. 需要时对 CPU 密集型任务使用进程池。

## 15.3 基本执行规则

建议遵守：

1. **先 claim，后执行业务；**
2. **长计算期间不要一直持有 DB 锁；**
3. **结果写回时再开启新事务；**
4. **SQLite 连接不要跨线程乱共享；**
5. **每个 worker 并发度要可配置。**

## 15.4 阶段并发建议

第一版可保守配置，例如：

| 阶段 | 初始并发建议 |
| --- | ---: |
| file/url/api ingestion normalize | 2 |
| clean universal | 4 |
| clean dedicated providers | 4 |
| rag structurizer | 2 |
| rag constructor | 2 |
| vectorizer | 1-2 |

这类并发值应通过配置文件控制，而不是写死。

---

## 16. 接口与契约设计建议

## 16.1 统一内部契约

建议所有阶段 payload 统一具备以下基础字段：

1. `workflow_run_id`
2. `step_id`
3. `source_id`
4. `document_id`
5. `stage`
6. `action`
7. `config_version`
8. `trace_id`

## 16.2 结果对象统一字段

建议所有结果对象至少包含：

1. `status`
2. `artifacts`
3. `metrics`
4. `warnings`
5. `next_step_hints`
6. `retryable`

这样可以把当前分散在 callback payload 里的语义统一为 Python 内部契约。

---

## 17. 可观测性与调试

当前迁移后的本地单体最怕“看不见状态”。  
因此必须在第一版就把可观测性做进去。

建议至少提供：

1. `workflow_runs` 列表查询；
2. `workflow_steps` 详情查询；
3. `step_attempts` 历史；
4. `artifacts` 浏览；
5. 当前活跃 `task_claims` 查询；
6. restart / purge 管理接口；
7. CLI debug 命令。

建议实现：

```text
smind-cli workflow list
smind-cli workflow inspect <id>
smind-cli workflow restart <id>
smind-cli step restart <step-id>
smind-cli workflow purge <id>
```

---

## 18. 迁移顺序建议

## 18.1 第一阶段：先搭内核

优先实现：

1. SQLite schema；
2. `workflow_core`；
3. claim/lease scheduler；
4. ObjectStore；
5. VectorStore 抽象。

这一阶段先不追求完整业务，只要把“本地阶段状态机”跑通。

## 18.2 第二阶段：迁 clean

迁移顺序建议：

1. `smind-admin` 的 ingestion 启动部分；
2. `smind-clean-dispatcher`；
3. `smind-skill-clean-universal`；
4. `smind-skill-clean-dedicated-apis`。

目标是先把：

```text
source -> clean workflow -> clean artifacts
```

闭环跑通。

## 18.3 第三阶段：迁 rag

再迁：

1. `workflow_rag`
2. `rag_structurizer`
3. `rag_constructor`
4. `rag_vectorizer`

目标是跑通：

```text
clean artifacts -> structured/constructed artifacts -> vectors
```

## 18.4 第四阶段：补管理面

最后补：

1. 管理接口；
2. restart / purge；
3. 可观测性；
4. CLI；
5. 配置管理。

---

## 19. 风险与边界

## 19.1 主要风险

| 风险 | 说明 | 应对 |
| --- | --- | --- |
| SQLite 写热点 | 多 worker 高频更新同一批表 | 缩短事务、拆表、加索引、控制并发 |
| Python 长任务阻塞 | 部分任务可能 CPU 密集 | 进程池或外部模型服务 |
| 浏览器渲染复杂度 | browser fetch 替代并不轻 | 独立 browser adapter |
| 向量能力上限 | sqlite-vec 更适合本地轻中量 | 保留 `VectorStore` 抽象 |
| restart 语义丢失 | 当前系统依赖重放能力 | 把 restart 当一等能力设计 |

## 19.2 当前阶段不追求的目标

本次技术路线不追求：

1. 一开始就支持分布式横向扩展；
2. 一开始就支持海量向量库；
3. 一开始就支持多租户云服务；
4. 一开始就追求 App 内嵌优化到极致。

当前的核心目标是：

> **先把系统收敛成一个可控、可维护、可演进的本地 Python 工作流内核。**

---

## 20. 最终建议

对于 `smind-family`，Python 路线是正确的，但前提是要坚持以下三件事：

1. **SQLite 必须被当成 workflow kernel，而不是普通数据库；**
2. **组件间不能继续模拟 HTTP/queue 微服务，而要改成“模块内调用 + 状态驱动推进”；**
3. **所有 Cloudflare 平台能力都必须被适配层封装，不能泄漏到业务层。**

最终建议的架构定义如下：

> `smind-family` 应重构为一个以 Python 为主体语言、以 SQLite 为工作流状态内核、以 sqlite-vec 为本地向量引擎、以本地文件存储为对象层、以 monorepo 管理模块边界的模块化单体系统。

这个方向既能保留当前系统最有价值的阶段化处理与状态控制能力，又能显著降低部署复杂度，并为后续更深的本地化演进打下稳定基础。
