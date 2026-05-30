# smind-family P0-P7 重构审查报告

> 审查对象: `smind-family P0-P7 refactoring`
> 审查类型: `code-review | closure-review | grand-consolidated`
> 审查时间: `2026-05-31`
> 审查人: `DeepSeek (独立审查)`
> 审查范围:
> - `apps/` — API / Worker / CLI 三入口
> - `packages/` — 全部 19 个业务与基础能力包
> - `tests/` — smoke + integration (P0-P7)
> - `docs/refactor/` — core.sql, vec.sql, index.md, todo-list.md, database.md
> - `docs/closure/` — P0-closure.md ~ P7-closure.md (8份)
> - `docs/action-plan/` — P0.md ~ P7.md (8份)
> 对照真相:
> - `docs/refactor/index.md` — 总纲与架构边界
> - `docs/refactor/database.md` — 数据库设计规范
> - `docs/refactor/todo-list.md` — 执行计划与验收标准
> - `docs/action-plan/P0.md~P7.md` — 分阶段执行计划
> 文档状态: `reviewed`

---

## 0. 总结结论

> 整体判断: P0-P7 阶段工作**主体骨架成立、流程可跑通、关键路径有测试覆盖**，但代码实现中存在**若干正确性缺陷、架构契约违反、安全隐患和 schema drift**，在当前状态下不应标记为全部 `full-close`。

- **整体判断**：实现主体框架正确，P0/P1 的基础工程骨架与 workflow kernel 质量较高。P2-P7 的业务层存在多个阻塞级正确性问题，以及多处违反 `database.md` 设计契约的实现漂移。
- **结论等级**：`changes-requested`
- **是否允许关闭本轮 review**：`no`
- **本轮最关键的 1-3 个判断**：
  1. **存在 4 个 blocker 级别 bug**（R1/R2/R3/R4），直接导致特定路径下功能错误或安全风险；
  2. **`database.md` 的多项设计约束被实现层违反**（R8/R9/R10），导致数据流向与设计文档不一致；
  3. **closure 文档所宣称的 `verified` 状态与实际代码质量不完全匹配**，多个 closure 宣称的 `full-close` 需回调。

---

## 1. 审查方法与已核实事实

### 对照文档

- `docs/refactor/index.md` (999行) — 总纲、模块映射、通信拓扑
- `docs/refactor/database.md` (597行) — 数据库设计原则、不变量、事务流程
- `docs/refactor/todo-list.md` (708行) — 分阶段 checklist、验收标准
- `docs/refactor/core.sql` (760行) — core.db DDL SSOT
- `docs/refactor/vec.sql` (150行) — vec.db DDL SSOT
- `docs/action-plan/P0.md` ~ `P7.md` (8份)
- `docs/closure/P0-closure.md` ~ `P7-closure.md` (8份)

### 核查实现

- `apps/api/src/smind_api/` (9文件, ~400行)
- `apps/worker/src/smind_worker/` (1文件, ~70行)
- `apps/cli/src/smind_cli/` (1文件, ~50行)
- `packages/` 全部 19 个包的核心源文件
- `tests/smoke/` (4文件)
- `tests/integration/` (8文件)

### 执行过的验证

- 代码静态审查：全仓 60+ 个 Python 源文件逐行阅读
- schema 对账：`core.sql` / `vec.sql` DDL 与 migration runner 实现交叉核对
- 测试对账：integration test 逻辑与 action-plan 验收标准逐项比对
- closure 对账：8 份 closure 的 claim 与代码实际能力逐一核实

### 1.1 已确认的正面事实

- **P0 骨架质量高**：目录结构、workspace 配置、工程命令与 `docs/refactor/index.md` §6 完美对齐。
- **workflow kernel 事务正确**：`claim_next_step` 使用 `BEGIN IMMEDIATE` + `ux_task_claims_active_step` 唯一索引，step claim 不变量（database.md §4.1）可被 DDL 保障。
- **migration 幂等设计**：`apply_core_migrations` 和 `apply_vec_schema` 都使用 migration_id 做幂等检测，支持增量部署。
- **sqlite-vec fallback 机制**：`apply_vec_schema` 在 vec0 扩展不可用时优雅降级为普通表，设计务实。
- **smoke 测试覆盖完整**：4 个 smoke 分别覆盖 API/Worker/CLI 启动与 shared imports，全部可独立运行。
- **legacy freeze 守卫**：`check_legacy_freeze.sh` + `test_p7_legacy_freeze_guard() ` 形成自动化闸门。
- **Auth 三表齐全**：`users` / `sessions` / `api_keys` 以及 team 体系完整，控制面基础设施到位。

### 1.2 已确认的负面事实

- **`workflow_rag/service.py:40`** — `step['run_id']` 访问不存在的 key，应为 `step['workflow_run_id']`。**一定触发 `KeyError`**。
- **`workflow_clean/service.py:24`** — `_load_raw_payload` 对 file source 返回 `object_key`（路径字符串），而非从 `ObjectStore` 读取文件内容。clean pipeline 的输入永远是路径字符串而非真实文本。**一定导致 clean 产出错误的 artifact**。
- **`vector_sqlite_vec/store.py:91-106`** — `search()` 执行全表扫描 + Python 端遍历计算余弦相似度，未使用 `sqlite-vec` 的原生 KNN 能力。**数据集扩大的场景下性能不可接受**。
- **`auth/service.py:9`** — `_hash()` 使用无盐 SHA256，无 bcrypt/argon2，**违反密码存储安全基线**。
- **`database.md` §3.4  / §3.5 违反** — `cleaned_text` 和 `structured_json` 的 payload 以内联形式存在 `artifacts.metadata_json` 中，未使用 `object_store`。**设计契约漂移**。
- **`rag_vectorizer/search.py:48`** — `chunk_text` 字段实际返回 `content_hash`（哈希摘要）而非文本内容。**搜索结果对用户不可读**。
- **chunk 文本未持久化** — `rag_constructor/build_chunks` 仅在内存构建切块，chunk text 既不写入 `storage_objects`，也不作为 `artifacts` 记录。**vectorize 后原始切块内容丢失**。
- **时间格式不统一** — `purge.py`/`restart.py` 使用 `CURRENT_TIMESTAMP`（本地时间），违反 `database.md` §9.2 强制 UTC ISO-8601 文本时间约束。
- **migration runner 使用路径遍历** — `_repo_root()` 向上寻找 SQL 文件，在 wheel 安装场景下一定失败。

---

## 2. 审查发现

### 2.1 Finding 汇总表

| 编号 | 标题 | 严重级别 | 类型 | blocker | 建议处理 |
|------|------|----------|------|--------|----------|
| R1 | `workflow_rag` KeyError — `step['run_id']` 不存在 | critical | correctness | yes | 改用 `step['workflow_run_id']` |
| R2 | `workflow_clean` `_load_raw_payload` 返回路径而非文件内容 | critical | correctness | yes | 从 ObjectStore 读取实际内容 |
| R3 | `VectorStore.search()` 全表扫描 + Python 端余弦 | critical | platform-fitness | yes | 使用 sqlite-vec KNN 或改为 DB 端排序 |
| R4 | 无盐 SHA256 密码存储 | critical | security | yes | 改用 bcrypt/argon2 |
| R5 | `schema_migrations` / `vec_schema_migrations` 不在 SSOT SQL 中 | high | docs-gap / schema-drift | yes | 回写 core.sql/vec.sql |
| R6 | purge/restart 使用 `CURRENT_TIMESTAMP` 而非 UTC ISO-8601 | high | protocol-drift | yes | 改为 Python 端生成 ISO-8601 时间 |
| R7 | `search.chunk_text` 返回 hash 而非实际文本 | high | correctness | yes | 从 artifact 或 object store 读取文本 |
| R8 | Artifact payload 内联在 `metadata_json` 而非 object store | high | docs-gap (design violation) | no | 按 database.md §3.4 改用 ObjectStore |
| R9 | Chunk 文本未持久化 | high | delivery-gap | yes | 写入 ObjectStore 并记录 artifact ref |
| R10 | Migration runner 路径遍历 | high | platform-fitness | yes | 改为 package data 嵌入或显式配置路径 |
| R11 | `retry.py` 使用 `INSERT OR REPLACE` 可能覆盖 | medium | correctness | no | 改用 `INSERT ... ON CONFLICT DO UPDATE` |
| R12 | 包名不一致 (pyproject.toml vs import) | medium | platform-fitness | no | 统一命名规范或明确说明 |
| R13 | API 每次请求创建新 DB 连接 | medium | platform-fitness | no | 添加 simple connection caching |
| R14 | 无 worker error path 测试覆盖 R1 | medium | test-gap | no | 增加 fail/failure 测试 |
| R15 | Legacy freeze 仅扫描 `.py` / `.sh` | low | test-gap | no | 扩展文件类型扫描 |

### R1. `workflow_rag/service.py:40` — `step['run_id']` 访问不存在的 key

- **严重级别**：`critical`
- **类型**：`correctness`
- **是否 blocker**：`yes`
- **事实依据**：
  - `workflow_rag/service.py:40`: `raise ValueError(f"run not found: {step['run_id']}")`
  - `core.sql` `workflow_steps` 定义中字段为 `workflow_run_id TEXT NOT NULL`，不存在 `run_id` 字段
  - 若 `step["workflow_run_id"]` 查询 `workflow_runs` 返回 None，下一行会触发 `KeyError: 'run_id'`
- **为什么重要**：如果 worker 遇到缺失 run 的场景（可能在 restart/purge 竞态下），错误信息会被 `KeyError` 吞掉，真实错误原因不可诊断。
- **审查判断**：这是一个明确的正确性 bug。`step` 是从 `SELECT * FROM workflow_steps` 取出的 Row，只有 `workflow_run_id` 列，没有 `run_id` 列。修复为 `step['workflow_run_id']`。
- **建议修法**：
  ```python
  # 第40行改
  raise ValueError(f"run not found: {step['workflow_run_id']}")
  # 同时可简化：将上两行的 step["workflow_run_id"] 赋给局部变量复用
  ```

### R2. `workflow_clean/service.py:24` — `_load_raw_payload` 返回路径而非文件内容

- **严重级别**：`critical`
- **类型**：`correctness`
- **是否 blocker**：`yes`
- **事实依据**：
  - `workflow_clean/service.py:11-32`: `_load_raw_payload()` 函数
  - 第12-24行: 对于 `source_kind == "file"` 的情况，执行 `SELECT u.object_key FROM sources s JOIN uploads u ... WHERE s.id = ?`，返回 `row["object_key"]`（形如 `raw/{team_id}/{upload_id}/{filename}` 的路径字符串）
  - 然而在 `ingestion/service.py:54` 中，`file_confirm` 调用 `self.object_store.put_text(upload["object_key"], content)` 将实际内容写入文件系统
  - clean pipeline 不读取 object store，导致`process_clean_step` 接收到的输入是路径字符串而非文件内容
  - P3 集成测试不验证实际审计内容，仅检查 artifact 是否创建，因此未暴露此 bug
- **为什么重要**：clean pipeline 是整个知识加工管道的输入正确性基础。如果 clean 的输入是路径字符串，那么 `cleaned_text` artifact 的内容就永远是路径描述而非用户文件内容，下游 structurizer/constructor/vectorizer 全部建立在错误输入之上。
- **审查判断**：这是一个确定的正确性 bug。`_load_raw_payload` 没有履行"从 ObjectStore 加载原始负载"的职责。
- **建议修法**：
  ```python
  def _load_raw_payload(conn: Connection, object_store: FileSystemObjectStore,
                         source_id: str, source_kind: str) -> str:
      if source_kind == "file":
          row = conn.execute(...).fetchone()
          if not row:
              return ""
          # 从 ObjectStore 读取实际内容
          obj_path = row["object_key"]
          obj = object_store.get_text(obj_path)  # 需要添加 get_text 方法
          return obj if obj else ""
      ...
  ```
  需要给 `FileSystemObjectStore` 添加 `get_text(key)` 方法。同时调整 `process_clean_step` 接受 `object_store` 参数。

### R3. `VectorStore.search()` 全表扫描 + Python 端余弦计算

- **严重级别**：`critical`
- **类型**：`platform-fitness`
- **是否 blocker**：`yes`
- **事实依据**：
  - `vector_sqlite_vec/store.py:91-106`: `search()` 方法
  - 第92-99行：`SELECT vr.chunk_id, cei.embedding FROM vector_records vr JOIN chunk_embedding_index cei ... WHERE vr.deleted_at IS NULL` — 无条件全表扫描
  - 第101-104行：对每一行反序列化 JSON embedding，`for row in rows: ... _cosine(embedding, candidate)`
  - 设计文档 `database.md §5.7` 明确要求 `vec.db` 使用 sqlite-vec 的 KNN 能力
  - `vec.sql` 已经定义了 `chunk_embedding_index USING vec0(embedding float[1536])` 虚拟表，原生支持 KNN 查询
- **为什么重要**：随着向量数量增长（1000+），全部拉取到 Python 内存再计算余弦不可扩展。当数据达到 10000+ 条时，该函数将成为系统瓶颈。而且 sqlite-vec 的 `vec0` 虚拟表支持 `knn` 查询，native 调用远比 Python 端计算快。
- **审查判断**：实现层没有使用 vec0 的 KNN 能力，选择全表扫描 + Python 端手动计算。即使在 sqlite-vec 不可用的 fallback 模式下（普通 `chunk_embedding_index` 表），也应当在同一 SQLite 连接中用 `ATTACH` 或自定义标量函数做计算。
- **建议修法**：
  ```python
  def search(self, *, embedding: list[float], top_k: int = 10) -> list[dict]:
      try:
          # 尝试使用 vec0 KNN
          embedding_json = json.dumps(embedding)
          rows = self.conn.execute(
              "SELECT rowid, distance FROM chunk_embedding_index WHERE embedding MATCH ? ORDER BY distance LIMIT ?",
              (embedding_json, top_k),
          ).fetchall()
          # 然后 rowid -> chunk_id 映射
          ...
      except OperationalError:
          # fallback: 客户端计算
          ...
  ```

### R4. 无盐 SHA256 密码存储

- **严重级别**：`critical`
- **类型**：`security`
- **是否 blocker**：`yes`
- **事实依据**：
  - `auth/service.py:8-9`: `_hash(v) -> hashlib.sha256(v.encode("utf-8")).hexdigest()`
  - 无 salt、无迭代、无 bcrypt/argon2/scrypt
  - 密码直接哈希存入 `users.password_hash`
- **为什么重要**：密码被静态 SHA256 存储意味着：
  1. 相同密码产生相同 hash（彩虹表攻击）
  2. 无迭代因子（暴力破解速度快）
  3. 不符合任何现代密码存储标准（OWASP / NIST）
- **审查判断**：这是安全敏感实现缺陷。当前为开发阶段，但此问题若进入生产将成为严重违规。
- **建议修法**：
  ```python
  import bcrypt  # 或 hashlib.scrypt, argon2

  def _hash(password: str) -> str:
      return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode()

  def _verify(password: str, hash: str) -> bool:
      return bcrypt.checkpw(password.encode("utf-8"), hash.encode())
  ```

### R5. `schema_migrations` / `vec_schema_migrations` 不在 SSOT SQL 中

- **严重级别**：`high`
- **类型**：`docs-gap / schema-drift`
- **是否 blocker**：`yes`
- **事实依据**：
  - `storage_sqlite/migrations/runner.py:14-20`: `_ensure_migration_table` 动态创建 `schema_migrations` 表
  - `vector_sqlite_vec/schema.py:14-20`: `_ensure_migration_table` 动态创建 `vec_schema_migrations` 表
  - `core.sql` (760行) 和 `vec.sql` (150行) 中均未包含这两个 migration tracking 表
  - `database.md` 未约定 migration tracking 表的设计
- **为什么重要**：SSOT DDL 与实际运行时数据库结构之间存在隐性差异。任何依赖 SSOT 做 schema 重建的测试或部署流程都会遗漏这两张表。长远看应纳入版本化 migration 体系。
- **审查判断**：虽然不是功能性 blocker，但导致 `core.sql` 不再能直接重建完整的 `core.db`，违背了"SSOT 设计文档"的承诺。
- **建议修法**：
  在 `core.sql` 和 `vec.sql` 的 `BEGIN;` 之后、其他 `CREATE TABLE` 之前，加入 migration tracking 表的定义：
  ```sql
  CREATE TABLE IF NOT EXISTS schema_migrations (
      migration_id TEXT PRIMARY KEY,
      applied_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
  );
  ```
  同理到 `vec.sql`。

### R6. purge/restart 使用 `CURRENT_TIMESTAMP` 而非 UTC ISO-8601

- **严重级别**：`high`
- **类型**：`protocol-drift`
- **是否 blocker**：`yes`
- **事实依据**：
  - `purge.py:36`: `SET status='processing', started_at=CURRENT_TIMESTAMP`
  - `restart.py:35`: `SET status='processing', started_at=CURRENT_TIMESTAMP`
  - `database.md §9.2`：强制 "统一使用 UTC ISO-8601 文本时间，格式示例: `2026-05-30T18:16:48.420Z`"
  - `core.sql` 中所有列默认值使用 `strftime('%Y-%m-%dT%H:%M:%fZ', 'now')` — 这是正确的
  - 但 purge.py 和 restart.py 使用 raw `CURRENT_TIMESTAMP`，在非 UTC 本地时区的系统上会产生偏差
- **为什么重要**：时间格式不统一会造成：
  1. 日志和 API 输出的时间可能出现时区不一致
  2. `sort_by created_at` 等以字符串排序的操作在不同时区服务器上结果不同
  3. 违反强制性的设计 doc 契约
- **审查判断**：实现与 SSOT 之间存在明确的 protocol drift。
- **建议修法**：将 `purge.py` / `restart.py` 中的所有 `CURRENT_TIMESTAMP` 替换为 Python 端的 `utc_now_iso()` 传入，或统一使用 SQLite 的 `strftime('%Y-%m-%dT%H:%M:%fZ', 'now')`。

### R7. `search()` 返回 `chunk_text` 为 `content_hash`

- **严重级别**：`high`
- **类型**：`correctness`
- **是否 blocker**：`yes`
- **事实依据**：
  - `rag_vectorizer/search.py:44-49`: search 结果组装
  - 第48行: `"chunk_text": row["content_hash"]`
  - `content_hash` 是 `chunks.content_hash` 列，存储的是 SHA256 hex digest
  - 而 chunk 的实际文本内容未被持久化（见 R9），因此无法提供
- **为什么重要**：search 是有直接用户触达的 API 面。返回不可读的 hash 字符串意味着搜索功能对用户不可用。客户端拿到 `chunk_text` 字段期望的是可读文本。
- **审查判断**：命名与内容不符，且底层 chunk 文本持久化的缺失导致了此问题（R9 是根本原因）。
- **建议修法**：先解决 R9（chunk 文本持久化），然后：
  ```python
  # 从 object store 或 artifact 加载 chunk 文本
  "chunk_text": self._load_chunk_text(row["chunk_id"]) or row["content_hash"]
  ```

### R8. Artifact payload 内联在 `metadata_json` 违反设计契约

- **严重级别**：`high`
- **类型**：`docs-gap (design violation)`
- **是否 blocker**：`no`（可后续优化）
- **事实依据**：
  - `database.md §3.4`: "以下内容禁止直接内联存入数据库字段：原始文件二进制；大段清洗文本；完整 structured JSON；长段 chunk 文本 … 数据库只保存：对象引用；内容 hash；元数据……"
  - `workflow_clean/service.py:57-67`: 将 `{"text": cleaned, "source_kind": ...}` 直接存入 `artifacts.metadata_json`
  - `workflow_rag/service.py:45-60`: 将 `{"paragraphs": ..., "paragraph_count": ...}` 直接存入 `artifacts.metadata_json`
- **为什么重要**：`metadata_json` 列按设计只应存元数据，不应存正文。短期内将大文本内联在 JSON 中不会造成问题，但随着数据量增长，`artifacts` 表会膨胀，备份和查询性能会下降。更重要的是，这个漂移意味着整个 clean → rag 管道的 artifact 数据流没有被 ObjectStore 承接。
- **审查判断**：虽然是显式的设计违反，但当前阶段（dev/prototype）内联存储是可接受的权衡。应记录为技术债务并在 P6/P7 阶段追踪。
- **建议修法**：将 `cleaned_text` / `structured_json` 的 payload 写入 `FileSystemObjectStore`，`metadata_json` 只保留 `{"object_key": "clean/team_id/run_id/artifact_id.txt", "source_kind": "url"}`。

### R9. Chunk 文本未持久化

- **严重级别**：`high`
- **类型**：`delivery-gap`
- **是否 blocker**：`yes`
- **事实依据**：
  - `workflow_rag/service.py:83-120`: `rag:construct` 阶段创建 chunk
  - 第88-109行: `INSERT INTO chunks(...)` — 只插入了元数据（chunk_index, content_hash, token_count, char_count），没有写入实际文本
  - 第111-119行: `vector_store.upsert_chunk(...)` — 只做了向量 upsert
  - `rag_constructor/service.py` 的 `build_chunks` 在内存中切分段落，切分后的文本列表返回后直接被 vectorize，然后丢弃
  - chunk 文本没有写入 `artifacts` 表，也没有写入 `storage_objects`
- **为什么重要**：chunk 文本的缺失导致：
  1. 搜索结果无法返回可读文本（R7）
  2. 无法重建向量索引（如果 vec.db 丢失，chunk 文本不能恢复重新 embedding）
  3. chunk 层面的 purge 重构不可能（找不到原文）
  4. 违反了 `database.md §3.4` 和 `database.md §4.2` 的 chunk identity 不变量
- **审查判断**：这是一个系统性的交付缺口。chunk 作为 RAG pipeline 的核心产出，其文本内容是整个知识库可恢复性的基础。
- **建议修法**：
  ```python
  # 在 workflow_rag/service.py 中，build_chunks 之后：
  for index, text in enumerate(chunks):
      chunk_id = str(uuid4())
      # 写入 object store
      chunk_key = f"chunks/{run['team_id']}/{run['id']}/{chunk_id}.txt"
      object_store.put_text(chunk_key, text)
      # 创建 artifact 记录
      artifact_id = str(uuid4())
      conn.execute(
          "INSERT INTO artifacts (...) VALUES ('chunk_text', ...)",
          ...
      )
      # 更新 chunks 表
      conn.execute(
          "INSERT INTO chunks (...) VALUES (...) ",
          ...
      )
      # 然后 vectorize
  ```

### R10. Migration runner 路径遍历不可移植

- **严重级别**：`high`
- **类型**：`platform-fitness`
- **是否 blocker**：`yes`（对 wheel 部署场景）
- **事实依据**：
  - `storage_sqlite/migrations/runner.py:6-10`: `_repo_root()` 向上查找 `docs/refactor/core.sql`
  - `vector_sqlite_vec/schema.py:6-10`: `_repo_root()` 向上查找 `docs/refactor/vec.sql`
  - 两个函数都假设代码一定在 git repo 的目录树下
  - 在 `pip install smind-storage-sqlite`（wheel 安装）场景下，`docs/refactor/core.sql` 文件不存在于 site-packages 中
- **为什么重要**：这直接阻止了包的 wheel 分发。当前开发模式下（`pip install -e .`）工作正常，但一旦部署到非开发环境就断裂。
- **审查判断**：开发阶段的合理 shortcut，但必须记录为 deploy blocker。
- **建议修法**：
  - 选项A：将 SQL DDL 作为 package data 内嵌，使用 `importlib.resources` 读取
  - 选项B：将 SQL DDL 以字符串常量嵌入 Python 文件
  - 选项C：在 setup.py/pyproject.toml 中将 SQL 文件声明为 `package_data`
  ```python
  # 推荐方案——使用 importlib.resources 嵌入
  import importlib.resources as pkg_resources
  from . import sql_assets  # 包内嵌的 SQL 文件目录

  core_sql = pkg_resources.read_text(sql_assets, "core.sql")
  conn.executescript(core_sql)
  ```

### R11. `retry.py:28` `INSERT OR REPLACE` 可能覆盖

- **严重级别**：`medium`
- **类型**：`correctness`
- **是否 blocker**：`no`
- **事实依据**：
  - `retry.py:28`: `INSERT OR REPLACE INTO step_attempts (...) VALUES (?, ?, ..., 'success', 0, ?, ?)`
  - 主键 `id` 为 `f"attempt_{claim['id']}"`，同一 claim 不会重复
  - UNIQUE(`step_id`, `attempt_number`) 也保证了不同 claim 不会冲突
  - 但若 `claim['id']` 生成方式改变（如改为更短 ID），可能与其他 attempts 冲突
- **审查判断**：当前实现中 ID 是 `attempt_{claim_id}` 格式，理论不会碰撞，但 `OR REPLACE` 语义过于宽松。
- **建议修法**：改用 `INSERT ... ON CONFLICT(id) DO UPDATE SET ...`，更安全且明确。

### R12. 包名不一致

- **严重级别**：`medium`
- **类型**：`platform-fitness`
- **是否 blocker**：`no`
- **事实依据**：
  - pyproject.toml 命名：`smind-auth`, `smind-team`, `smind-ingestion`, `smind-management`
  - Python import 包名：`auth`, `team`, `ingestion`, `management`
  - 命名空间不一致，未来若出现与 PyPI 同名包可能导致冲突
- **审查判断**：当前在 monorepo 内不影响运行，但长期维护有冲突风险。
- **建议修法**：统一使用 `smind_` 前缀作为 Python 包名（如 `smind_auth`, `smind_team`），或明确约定 monorepo 内使用短名。

### R13. API 每次请求创建新 DB 连接

- **严重级别**：`medium`
- **类型**：`platform-fitness`
- **是否 blocker**：`no`
- **事实依据**：
  - `deps.py:13-16`: `get_core_conn()` 每次调用都创建新的 `CoreSQLiteEngine(...).connect()`
  - `/healthz` / `/auth/register` / `/auth/login` 每个请求都打开独立连接
- **审查判断**：SQLite 连接创建成本不高，但无限制的增长不会自动回收。
- **建议修法**：添加 `@lru_cache` 或 `contextvars` 管理数据库连接的生命周期。

### R14. 无 worker error path 测试覆盖 R1

- **严重级别**：`medium`
- **类型**：`test-gap`
- **是否 blocker**：`no`
- **审查判断**：worker 测试仅覆盖 happy path（clean step 成功、rag pipeline 到 completed）。没有测试 `step not found`、`run not found`、`source not found` 等异常路径。R1 的 bug 就是因为在异常路径使用错误字段名。
- **建议修法**：新增 test 覆盖 worker 消费不存在的 run/step/source 时能正常 fail 而不是 crash。

### R15. Legacy freeze 仅扫描 `.py` / `.sh`

- **严重级别**：`low`
- **类型**：`test-gap`
- **是否 blocker**：`no`
- **事实依据**：
  - `check_legacy_freeze.sh`: `--glob '*.py' --glob '*.sh'`
  - 不扫描 `.json`, `.yaml`, `.yml`, `.toml`, `.md` 等
- **审查判断**：当前新代码中没有这些文件，但守卫的覆盖面不足。
- **建议修法**：扩展 pattern 集，或改为扫描所有 `apps/` `packages/` `tests/` `tools/` 下的文件。

---

## 3. In-Scope 逐项对齐审核

### 3.1 P0 — 基础骨架

| # | 计划项 / 设计项 | 审查结论 | 说明 |
|---|----------------|----------|------|
| P0-01 | 建立顶层目录骨架 | done | `apps/` `packages/` `tests/` `tools/` `data/` 全部到位 |
| P0-02 | 冻结 legacy 只读边界 | done | README + `check_legacy_freeze.sh` 双重保障 |
| P0-03 | 统一 Python workspace | done | pyproject.toml + 23 子包 pyproject.toml，editable install |
| P0-04 | API/Worker/CLI 运行壳 | done | 三者均有最小可运行入口 |
| P0-05 | common/contracts/config 公共面 | done | 三个基础包存在且被入口应用引用 |
| P0-06 | P0 smoke 验收 | done | 4 个 smoke 测试存在且通过 |

P0 **对齐判定**：`done` — 无显著 gap。

### 3.2 P1 — 数据库与状态内核

| # | 计划项 / 设计项 | 审查结论 | 说明 |
|---|----------------|----------|------|
| P1-01 | core.db/vec.db engine + migration | done | 两库 engine 存在，migration runner 有幂等保护 |
| P1-02 | core.db 全量 schema | partial | 表/索引/视图完整，但 `schema_migrations` 表不在 SSOT |
| P1-03 | vec.db 全量 schema | partial | vec0 虚拟表 + fallback，`vec_schema_migrations` 不在 SSOT |
| P1-04 | Repositories 基线 | done | 6 个 repositories 存在，覆盖 step/workflow/artifact/chunk/request |
| P1-05 | Workflow kernel claim/heartbeat/retry/reaper | done | claim 事务正确，唯一索引 + BEGIN IMMEDIATE 保障 |
| P1-06 | P1 集成回归 | partial | 测试存在但未覆盖 worker 异常路径（R14） |

P1 **对齐判定**：`partial` — 核心 kernel 质量好，但 schema drift（R5）和 time format 违反（R6）需修复。

### 3.3 P2 — 控制面与 ingestion

| # | 计划项 / 设计项 | 审查结论 | 说明 |
|---|----------------|----------|------|
| P2-01 | auth/team 控制面 | done | register/login/session/team bootstrap 完整 |
| P2-02 | file/url/api ingestion | done | 三类入口可用，object store 接入 |
| P2-03 | static files | done | static initiate/confirm 可用 |
| P2-04 | management 读面 | done | workflow/document/static-file list/detail 完整 |
| P2-05 | P2 集成回归 | partial | 测试覆盖全路径，但 password hash 安全问题（R4）未暴露 |

P2 **对齐判定**：`partial` — 功能面完整，但安全缺陷（R4）必须在进入生产前修复。

### 3.4 P3 — Clean Pipeline

| # | 计划项 / 设计项 | 审查结论 | 说明 |
|---|----------------|----------|------|
| P3-01 | clean step 执行内核 | partial | 可执行，但 `_load_raw_payload` 返回路径而非内容（R2） |
| P3-02 | universal cleaner | done | HTML 提取实现，结构简单但可用 |
| P3-03 | provider adapter | done | chinatax 标记 stub |
| P3-04 | clean artifact 持久化 | partial | 创建 artifact 记录但 content 内联在 metadata_json（R8） |
| P3-05 | rag step 自动创建 | done | clean finalizer 后创建 rag:structurize step |
| P3-06 | P3 集成回归 | partial | 测试存在但未验证 artifact 实际内容 |

P3 **对齐判定**：`partial` — 能力壳存在，但输入正确性（R2）存在 blocker。

### 3.5 P4 — RAG Pipeline

| # | 计划项 / 设计项 | 审查结论 | 说明 |
|---|----------------|----------|------|
| P4-01 | structurize | done | 段落切分 stub，可用 |
| P4-02 | construct / chunker | partial | chunk 元数据写入但文本未持久化（R9） |
| P4-03 | vectorizer / vec.db 写入 | partial | 向量写入 vec.db 但 search 使用全表扫描（R3） |
| P4-04 | workflow completed | partial | 可到达 completed 状态，但 chunk 文本丢失 |
| P4-05 | P4 集成回归 | partial | 检查 `status=completed` 和 `vec_status=vectorized`，但未验证 vec.db 内容 |

P4 **对齐判定**：`partial` — 管道可闭环，但 chunk 文本丢失（R9）和 `step['run_id']` bug（R1）影响正确性。

### 3.6 P5 — 检索与查询面

| # | 计划项 / 设计项 | 审查结论 | 说明 |
|---|----------------|----------|------|
| P5-01 | VectorStore.search | partial | 仅全表扫描 + 客户端余弦（R3），不可扩展 |
| P5-02 | SearchService | partial | 存在但 `chunk_text` 返回哈希（R7），不可读 |
| P5-03 | /search API | done | POST /search 和 /search/debug 路由存在 |
| P5-04 | CLI search | done | `smind-cli search` 接线 |
| P5-05 | P5 集成回归 | partial | 测试存在但未验证搜索结果可读性 |

P5 **对齐判定**：`partial` — API 面完整，但 search 实现的两个 blocker（R3/R7）使搜索功能不可用。

### 3.7 P6 — 运维与恢复能力

| # | 计划项 / 设计项 | 审查结论 | 说明 |
|---|----------------|----------|------|
| P6-01 | restart request | partial | 功能可用但 `CURRENT_TIMESTAMP`（R6） |
| P6-02 | purge request | partial | 功能可用但 `CURRENT_TIMESTAMP`（R6）且只支持 `target_kind='document'` |
| P6-03 | health / ops API | done | `/ops/health`, `/ops/claims`, `/ops/restarts`, `/ops/purges` 全部存在 |
| P6-04 | P6 集成回归 | partial | 测试存在但未验证 purge 后的 vec.db 状态 |

P6 **对齐判定**：`partial` — 功能面存在但时间格式违反设计契约（R6）。

### 3.8 P7 — 收敛与替换

| # | 计划项 / 设计项 | 审查结论 | 说明 |
|---|----------------|----------|------|
| P7-01 | legacy freeze 守卫脚本 | done | `check_legacy_freeze.sh` 存在 |
| P7-02 | cutover guard 回归 | done | `test_cutover.py` 执行 freeze check |
| P7-03 | 跨阶段总回归 | done | `pytest tests/integration tests/smoke` 报告 14 passed |

P7 **对齐判定**：`done` — 在作用域内无 gap。

### 3.9 对齐结论

| 等级 | 数量 |
|------|------|
| done | 18 |
| partial | 13 |
| missing | 0 |
| stale | 0 |
| out-of-scope-by-design | 0 |

> 整体更像 `"核心骨架完成 + 关键路径可通，但 4 个 blocker + 5 个 high severity finding 导致多个阶段的 closure claim 偏高"`。

---

## 4. Out-of-Scope 核查

| # | Out-of-Scope / Deferred 项 | 审查结论 | 说明 |
|---|----------------------------|----------|------|
| O1 | rerank/hybrid retrieval (P5 已 defer) | 遵守 | P5-closure 明确标记为 A 类 deferred |
| O2 | 更细粒度 detector/drill 扩展 (P6 已 defer) | 遵守 | P6-closure 标记为 C 类可后续增强 |
| O3 | clean contract 深化 (P3 已 defer) | 遵守 | P3-closure 标记为 C 类 |
| O4 | layered/summary artifact 扩展 (P4 已 defer) | 遵守 | P4-closure 标记为 C 类 |
| O5 | parity matrix 自动校验 (P7 已 defer) | 遵守 | P7-closure 标记为 C 类 |
| O6 | 生产级 LLM/embedding provider | 遵守 | 所有 embedding 使用本地 sha256 模拟，属合理 placeholder |

---

## 5. 跨阶段 / 跨包深度分析

### 5.1 API Surface 一致性

**已实现的路由与 action-plan 对照：**

| 路由 | 实现 | action-plan 要求 | 一致 |
|------|------|------------------|------|
| POST /auth/register | ✅ | P2 要求 | ✅ |
| POST /auth/login | ✅ | P2 要求 | ✅ |
| GET /auth/session | ✅ | P2 要求 | ✅ |
| POST /team/bootstrap | ✅ | P2 要求 | ✅ |
| GET /team/list | ✅ | P2 要求 | ✅ |
| POST /team/select | ✅ | P2 要求 | ✅ |
| GET /me / PATCH /me | ✅ | — | ✅ (超范围但合理) |
| POST /ingestion/file/initiate | ✅ | P2 要求 | ✅ |
| POST /ingestion/file/confirm | ✅ | P2 要求 | ✅ |
| POST /ingestion/url/submit | ✅ | P2 要求 | ✅ |
| POST /ingestion/api/submit | ✅ | P2 要求 | ✅ |
| POST /ingestion/static/initiate | ✅ | P2 要求 | ✅ |
| POST /ingestion/static/confirm | ✅ | P2 要求 | ✅ |
| GET /management/workflows | ✅ | P2 要求 | ✅ |
| GET /management/workflows/:id | ✅ | P2 要求 | ✅ |
| GET /management/documents | ✅ | P2 要求 | ✅ |
| GET /management/documents/:id | ✅ | P2 要求 | ✅ |
| GET /management/static-files | ✅ | P2 要求 | ✅ |
| GET /management/static-files/:id | ✅ | P2 要求 | ✅ |
| GET /workflow-configs | ✅ | — | ✅ (合理扩展) |
| POST /search | ✅ | P5 要求 | ✅ |
| POST /search/debug | ✅ | P5 要求 | ✅ |
| GET /ops/health | ✅ | P6 要求 | ✅ |
| GET /ops/claims | ✅ | P6 要求 | ✅ |
| GET /ops/restarts | ✅ | P6 要求 | ✅ |
| POST /ops/restarts | ✅ | P6 要求 | ✅ |
| GET /ops/purges | ✅ | P6 要求 | ✅ |
| POST /ops/purges | ✅ | P6 要求 | ✅ |

API surface 覆盖度 **完整**，符合 action-plan 预期。

### 5.2 测试用例核实

| 测试文件 | 覆盖的阶段 | 断言强度 | 评价 |
|---------|-----------|---------|------|
| `tests/smoke/test_api_smoke.py` | P0 | 响应状态码 + JSON body | 充分 |
| `tests/smoke/test_cli_smoke.py` | P0 | return code + stdout | 充分 |
| `tests/smoke/test_shared_imports_smoke.py` | P0 | 导入成功 + 基础调用 | 充分 |
| `tests/smoke/test_worker_smoke.py` | P0 | return code | 轻度 |
| `test_kernel_flow.py` | P1 | claim→heartbeat→fail→retry→reclaim→succeed | **充分，质量好** |
| `test_requests_and_vec.py` | P1 | restart/purge backlog + vec upsert/delete | 充分 |
| `test_ingestion_management.py` | P2 | 全链路 API smoke | 充分 |
| `test_clean_pipeline.py` | P3 | artifact 存在 + rag step 创建 | **轻度，未见证 content** |
| `test_rag_pipeline.py` | P4 | workflow completed + chunk count | **轻度，未见证 vec.db** |
| `test_search.py` | P5 | 返回非空 results + debug count | **轻度，未见证评分正确性** |
| `test_operations.py` | P6 | restart + purge + health + search after purge | 充分 |
| `test_cutover.py` | P7 | legacy freeze guard exit code | 充分 |

**测试覆盖评价**：P1 的 kernel flow 测试质量最高（step 级状态机覆盖），P3/P4/P5 的测试仅验证"存在性"而非"正确性"（artifact 存在、workflow completed 等），未能揭露 R2/R3/R7/R9 等正确性缺陷。

### 5.3 SQLite 表结构符合性

**`core.sql`**（对照 `database.md` §5 表分组）：

| 分组 | 表 | 状态 | 说明 |
|------|-----|------|------|
| 身份与控制面 | users, teams, team_members, api_keys, sessions | ✅ 全部实现 | 符合设计 |
| 输入与对象元数据 | uploads, sources, documents, static_files, artifacts, chunks | ✅ 全部实现 | 符合设计 |
| 工作流内核 | workflow_runs, workflow_steps, task_claims, step_attempts, workflow_step_links, workflow_events | ✅ 全部实现 | 符合设计 |
| 配置与版本 | configs, prompt_versions, provider_configs | ✅ 全部实现 | 符合设计 |
| 运维请求 | restart_requests, purge_requests | ✅ 全部实现 | 符合设计 |
| 审计 | audit_logs | ✅ 全部实现 | 符合设计 |

视图：11 个核心视图全部实现 ✅

索引：~38 个索引全部实现 ✅

**`vec.sql`**（对照 `database.md` §6）：

| 表 | 状态 | 说明 |
|-----|------|------|
| vector_namespaces | ✅ | 符合设计 |
| vector_records | ✅ | 符合设计 |
| chunk_embedding_index | ✅ | vec0 虚拟表 + fallback |

视图：3 个视图全部实现 ✅

索引：6 个索引全部实现 ✅

**Drift 分析**：
- `schema_migrations` / `vec_schema_migrations` 未在 SSOT 中（R5）
- `docs/refactor/database.md` §5 中提到了 `chunks` 表，已被 `core.sql` 实现 ✅
- `docs/refactor/database.md` §6.2 注明了 1536 维约束，`vec.sql` 中 CHECK 约束已实施 ✅
- `docs/refactor/database.md` §6.3 注明了 `embedding_rowid` 对应关系，`core.sql` 和 `vec.sql` 中无 DDL 级强制性保障，依赖应用层遵守

### 5.4 命名规范与执行逻辑

**命名规范问题**：

1. **包命名不一致**（R12）：pyproject.toml 中用 `smind-auth`，Python import 用 `auth`
2. **`smind_common` vs `smind-contracts` vs `common`**：`common` 包的 import 是 `smind_common`，但 `contracts` 包的 import 是 `smind_contracts` — 其中 `common`/`contracts` 的来源是 `src/smind_common/` 和 `src/smind_contracts/`，这是合理的
3. **`process_rag_step` 中变量名不一致**：第40行用 `step['run_id']`（不存在的字段），第37行正确使用 `step['workflow_run_id']`
4. **`p3_clean_pipeline.py` 测试**：第47行自定义 `row_factory` 使用字典实现，但与 `tests/fixtures/sqlite_kernel.py` 使用的 `sqlite3.Row` 语义不一致
5. **`providers_dedicated` 和 `cleaners_universal` 使用复数命名**，其他 service 包使用单数，风格不统一

**执行逻辑问题（除已列出的 blocker 外）**：

1. `workflow_rag/service.py:133`: `raise ValueError(f"unsupported rag stage: {stage}")` — 这个错误路径没有 `conn.rollback()`，事务可能悬空
2. `claim.py:69`: 异常处理中执行 `conn.rollback()` 但 `raise` 后调用方没有正确处理，worker 进程可能继续运行而不 recover
3. `purge.py:40-51`: 只处理 `target_kind='document'`，其他 target 直接标记 failed，没有回滚

### 5.5 closure 文档可信度评估

| Closure | 宣称 close-type | 审查后评估 | 关键 gap |
|---------|----------------|------------|----------|
| P0-closure | full-close | ✅ 维持 full-close | 无显著 gap |
| P1-closure | full-close | ⚠ 回调为 closed-with-explicit-deferrals | R5 schema drift, R6 time format |
| P2-closure | full-close | ⚠ 回调为 close-with-known-issues | R4 无盐密码 |
| P3-closure | full-close | ❌ 应回调为 close-with-known-issues | R2 输入正确性 bug |
| P4-closure | full-close | ❌ 应回调为 close-with-known-issues | R1 KeyError, R9 chunk 文本丢失 |
| P5-closure | full-close | ❌ 应回调为 close-with-known-issues | R3 全表扫描 search, R7 chunk_text 返回 hash |
| P6-closure | full-close | ⚠ 回调为 closed-with-explicit-deferrals | R6 time format |
| P7-closure | full-close | ✅ 维持 full-close | 无显著 gap |

closure 文档的诚实收口声明中均使用 `verified` 归类，但审查发现：
- 多个 `verified` 仅依赖测试"通过"而非测试"正确性验证"
- 证据类型中提到的 `commit SHA` 全部为 `N/A`（working-tree 证据）
- 四元组证据在 P3/P4/P5 closure 中实际仅覆盖了回归计数（14 passed），没有覆盖正确性断言

---

## 6. 最终 verdict 与收口意见

- **最终 verdict**：P0-P7 阶段工作主体完成，工程骨架、workflow kernel、控制面与 API surface 质量可靠。但业务层（clean/rag/search）存在 **4 个 critical blocker** 和 **5 个 high severity** 问题，部分 closure 的 `full-close` 判定需回调。
- **是否允许关闭本轮 review**：`no`
- **关闭前必须完成的 blocker**：
  1. ✅ **R1** — 修复 `workflow_rag/service.py:40` 的 `step['run_id']` → `step['workflow_run_id']`
  2. ✅ **R2** — 修复 `_load_raw_payload` 从 ObjectStore 读取文件内容而非返回路径
  3. ✅ **R3** — 将 `VectorStore.search()` 改为使用 sqlite-vec KNN，或至少改为在 fallback 模式下可扩展
  4. ✅ **R4** — 将密码哈希从无盐 SHA256 升级为 bcrypt/argon2
  5. ✅ **R6** — 统一 purge/restart 的时间格式为 ISO-8601 UTC
  6. ✅ **R7 + R9** — 持久化 chunk 文本，使 search 能返回可读内容
  7. ✅ **R10** — 修复 migration runner 的路径遍历问题
- **可以后续跟进的 non-blocking follow-up**：
  1. R5 — schema_migrations 表纳入 SSOT
  2. R8 — Artifact 内容迁移到 ObjectStore
  3. R11 — 改为更安全的 INSERT ... ON CONFLICT
  4. R12 — 包命名规范统一
  5. R13 — DB 连接缓存
  6. R14 — 增加 worker error path 测试
  7. R15 — 扩展 legacy freeze 扫描
- **建议的二次审查方式**：`same reviewer rereview`
- **实现者回应入口**：请按 `docs/templates/code-review.md` 的约定在本文档 append 段落回应，不改写 §0–§6。

---

## 修订历史

| 版本 | 日期 | 作者 | 变更 |
|------|------|------|------|
| r1 | 2026-05-31 | DeepSeek | 初完整审查 |
