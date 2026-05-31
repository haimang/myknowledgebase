# Nano-Agent 代码审查报告 — CR-3 · 对象存储与向量层 (storage_objects + vec.db)

> 审查对象: `packages/storage_objects/` + `packages/vector_sqlite_vec/` + `docs/refactor/vec.sql`(运行时 SSOT)及其消费方
> 审查类型: `code-review`
> 审查时间: `2026-05-31`
> 审查人: `Claude (Opus 4.8) 主审 + 3 个 sub-agent 分工作面调查（Face A 对象存储、Face B 向量引擎/schema/退化、Face C VectorStore/检索/一致性）`
> 审查范围:
> - `packages/storage_objects/src/storage_objects/filesystem_store.py`
> - `packages/vector_sqlite_vec/src/vector_sqlite_vec/{engine,schema,store}.py` + `vec.sql`
> - 消费方: `ingestion/service.py`、`workflow_clean/service.py`、`workflow_rag/service.py`、`workflow_core/purge.py`、`rag_vectorizer/{embedder,search}.py`、`apps/api/routes/{search,ingestion}.py`
> 对照真相:
> - `docs/refactor/index.md`（§5 vec.db 设计、§5.5 purge 序、§5.6 vectorize 五步序、§5.7 检索路径、§1 B/D/L 与 C1–C5、§7 owner 口径）
> - `docs/refactor/vec.sql`、`docs/refactor/database.md`（§6.5 KNN、§9.2 时间格式）、`docs/refactor/core.sql`（chunks / v_search_hydration / v_pending_purge_chunks）
> - `legacy-family/smind-admin/core/r2.ts`（R2 对象存储）、`legacy-family/smind-skill-rag-vectorizer/*`（Vectorize + DO + purger）
> - `docs/eval/first-code-review-plan/part-cr-1.md`、`part-cr-2.md`、`docs/closure/P4-closure.md`、`P5-closure.md`
> 文档状态: `changes-requested`

---

## 0. 总结结论

- **整体判断**：`本簇是迄今最严重的一簇 —— 对象存储存在可被用户输入触达的真实路径遍历漏洞,向量索引能力从未真正存在(静默退化为全表+JSON 暴力扫描),且 VectorStore 的 rowid 分配在两条常见路径下破坏数据/审计完整性。绝不可标记为 completed。`
- **结论等级**：`changes-requested`（实质接近 `blocked`：含 1 个安全漏洞 + 向量核心能力不可用）
- **是否允许关闭本轮 review**：`no`
- **本轮最关键的 4 个判断（均经主审独立实测复现)**：
  1. **路径遍历漏洞(critical/安全)**：`FileSystemObjectStore` 对 object_key 零校验,`../` 与绝对路径双逃逸;且 key 末段来自**未校验的 HTTP `filename`**,构成认证用户可达的任意文件读写 + 跨 team 越权。
  2. **向量索引是假绿(critical)**：全代码库从不加载 sqlite-vec 扩展,`vec0` 虚拟表恒建失败 → 静默退化为普通 `TEXT` 表;`search()` 不走任何 KNN,而是全表扫描 + Python cosine。P4/P5 closure 以绿色 PASS 宣称 vector/retrieval 完成,实为 O(N) 暴力实现。
  3. **rowid 不变量破坏(critical)**：同一 chunk_id 重复 upsert → 孤儿 rowid 无限累积;软删后新增 → `MAX+1` 重号 + `INSERT OR REPLACE` **静默删除已软删的审计记录**。
  4. **purge 不删对象(high)**：对象存储无 delete 接口,`purge.py` 全程不碰 object_store → 被 purge 文档的正文/原始上传**永久残留磁盘**(合规/隐私缺陷)。
- **重要澄清**：①与 CR-1/CR-2 一致,**G-CR1-01 时间格式 bug 不经由 CR-3 污染** —— store.py 时间列全走内联 `strftime`(SQLite 侧正确)。②vec.db **关系层 schema 本体是健康的**(表/索引/视图/CHECK/幂等实测全通过),问题集中在向量索引退化与 VectorStore 写路径。③C3 架构方向正确(双库解耦 + core post-filter),**读路径安全不会脏读**,缺陷在写路径漂移不自愈。

---

## 1. 审查方法与已核实事实

采用"主审 + 3 工作面并行 sub-agent"模式。三个 Face 独立调查并各自实跑取证后回归,主审对其中 **4 个 critical 发现全部独立复跑复现**(路径遍历、vec0 退化、孤儿 rowid、重号静默删除),再统一 reasoning 成报告。

- **核查实现**：storage_objects + vector_sqlite_vec 全部 6 个 py 文件 + vec.sql + 上述全部消费方。
- **执行过的验证(主审亲测)**：
  - `FileSystemObjectStore().put_text('../escaped.txt', ...)` → 文件写到 root **之外**(确认 R1);绝对路径 key 直接丢弃 root。
  - `CREATE VIRTUAL TABLE ... USING vec0(...)` → `no such module: vec0`;实跑 `apply_vec_schema` 后 `chunk_embedding_index` 实际为 `CREATE TABLE (... embedding TEXT)` 普通表(确认 R2)。
  - 同 chunk_id upsert ×3 → index rowids `[1,2,3]`,孤儿 `[1,2]`(确认 R3)。
  - 软删 b(deleted_at 置位、embedding_rowid=2 保留)→ upsert c 重号 rowid 2 → `b survived? 0`,b 软删记录被抹除(确认 R4)。
  - 全仓 `grep load_extension/enable_load_extension/sqlite_vec` → 仅依赖名,**无任何加载调用**。
- **执行过的验证(sub-agent 实跑)**：vec.sql 退化路径建库(4 表/6 索引/3 视图全建出,5 项 CHECK 逐条生效,幂等);`_cosine` 维度截断(5 维 vs 3 维 → score=1.0 无报错);C3 vectorize/purge 崩溃窗口分析。
- **复用 / 对照的既有审查**：part-cr-1（G-CR1-01）、part-cr-2（迁移无版本化、双副本、PRAGMA vec FK=OFF 合理分化)—— 独立复核后引用。
- **对照 closure claim**：`P4-closure.md:47`「vector gate ✅ PASS」、`P5-closure.md:46`「retrieval gate ✅ PASS」—— 与实际退化实现对账,判定为假绿。

### 1.1 已确认的正面事实

- vec.db **关系层 schema 保真且工程质量良好**:vector_namespaces / vector_records / 3 视图 / 6 索引实测干净建出;CHECK(dimension=1536 / distance_metric IN / deleted_at>=created_at / json_valid)逐条实测生效;幂等成立。
- C3 **架构方向正确**:VectorStore 对 vec.db 独立 commit、不依赖跨库事务,core 侧 `v_search_hydration.core_post_filter_eligible`(要求 vec_status='vectorized')**兜住检索正确性,崩溃窗口期不产生脏读**。
- `delete_chunks` 对已软删记录幂等跳过;rowid→chunk_id 的 JOIN 映射在 search hydration 路径实现良好。
- vec.sql 的 `PRAGMA/BEGIN/COMMIT` 与 `executescript` 叠加无冲突;包内 vec.sql 副本存在且与 docs 逐字节一致(同 CR-2,fallback 成立)。
- **CR-3 时间写入干净**:store.py 时间列全走内联 `strftime('%Y-%m-%dT%H:%M:%fZ','now')`,不引用畸形的 `now_iso()`,G-CR1-01 不经本簇污染。

### 1.2 已确认的负面事实

- object_key 零校验,`../` / 绝对路径双逃逸,且经未校验 HTTP `filename` 可达(实测)。
- sqlite-vec 扩展从不加载,vec0 恒失败,向量索引静默退化为普通 TEXT 表(实测)。
- `search()` 全表扫描 + Python cosine,无 KNN、无 namespace/model 过滤、无 limit 下推。
- 重复 upsert → 孤儿 rowid 累积;软删后新增 → 重号 + `INSERT OR REPLACE` 静默删除软删记录(实测)。
- 对象存储无 delete,purge 不清对象 → purged 内容永久残留。
- `put_text` 非原子;`get_text` 抛裸 `FileNotFoundError` 无人捕获;search `exists()→get_text()` 有 TOCTOU。
- `embedding_dimension` 硬编码 1536(不论实际向量长度);`_cosine` 维度不等静默截断。
- 仅 text 接口,无二进制(legacy R2 支持二进制 + ContentType)。

### 1.3 证据可信度说明

| 证据类型 | 本轮是否使用 | 说明 |
|----------|--------------|------|
| 文件 / 行号核查 | yes | 6 个 py + vec.sql + 全部消费方逐处核行号 |
| 本地命令 / 测试 | yes | 路径遍历、vec0 退化、孤儿 rowid、重号删除 4 个 critical 主审亲测复现;vec.sql 建库/CHECK/cosine 截断 sub-agent 实跑 |
| schema / contract 反向校验 | yes | vec.sql ↔ database.md;rowid 不变量 ↔ vec.sql:56-57 注释;v_search_hydration post-filter ↔ core.sql:677 |
| live / deploy / preview 证据 | n/a | 存储层无需 live 部署 |
| 与上游 design / QNA 对账 | yes | index §5.5/5.6/5.7;closure P4/P5 vector/retrieval gate 假绿对账;legacy r2.ts / vectorizer_do.ts / purger_logic.ts |

---

## 2. 审查发现

### 2.1 Finding 汇总表

| 编号 | 标题 | 严重级别 | 类型 | 是否 blocker | 建议处理 |
|------|------|----------|------|--------------|----------|
| R1 | 对象存储路径遍历(用户 filename 可达,跨 team 越权 + 任意文件读写) | critical | security / B+L | yes | store 内做 key 规范化+边界断言;ingestion basename 收口 |
| R2 | sqlite-vec/vec0 从不加载,向量索引静默退化为 TEXT 表 + 暴力 cosine(假绿) | critical | platform-fitness / B+D | yes | 退化 fail-loud;声明 sqlite-vec 依赖+load;closure 重新定级 |
| R3 | 重复 upsert 致孤儿 rowid 累积,违反一一对应不变量 | critical | correctness / L | yes | upsert 复用现有 embedding_rowid 或先删旧 index 行 |
| R4 | 软删后新增致 rowid 重号 + `INSERT OR REPLACE` 静默删除软删审计记录 | critical | correctness / L | yes | rowid 单调不复用;软硬删一致 |
| R5 | 对象存储无 delete,purge 不清对象 → purged 内容永久残留(合规) | high | delivery-gap / B+D | yes | store 加 delete;purge 接 object_store 删对象 |
| R6 | `put_text` 非原子写 + 读回不校验 hash/size → 静默损坏 | high | correctness / C1 | no | temp+os.replace 原子写;search 比对 content_hash |
| R7 | `embedding_dimension` 硬编码 1536 + `_cosine` 维度静默截断 | high | correctness / L | no | 写 len(embedding) 并校验;维度不等 raise |
| R8 | 对象存储仅 text,无二进制(PDF 等无法存) | high | scope-drift / B | no | 加 put_bytes/get_bytes 或文档化文本-only |
| R9 | `delete_chunk` 软删 vector_records 但硬删 index,软硬删不一致 | high | correctness / L | no | 统一删除策略;消除重号空洞 |
| R10 | `search` 仅按 team_id 过滤,无 namespace/embedding_model,跨模型错误打分 | high | correctness / B | no | search 增 namespace/model 过滤参数 |
| R11 | `get_text` 抛裸 FileNotFoundError 无人捕获;search exists→get 有 TOCTOU | medium | correctness / C2 | no | try/except 取代 exists+get;调用方分类处理 |
| R12 | purge 中途崩溃 request 卡 'processing' 不被重捞(无重入) | medium | correctness / C3+D | no | 同时捞 pending + 超时 processing |
| R13 | vectorize 崩溃窗口留 vec 孤儿向量,无补偿器;replay 放大 R3 | medium | correctness / C3 | no | 幂等重写(复用 rowid)+ 补偿路径 |
| R14 | 维度三处硬编码 + 无维度迁移路径(换模型需全库重建) | medium | delivery-gap / D | no | 文档化维度变更=重建;长期版本化迁移 |
| R15 | 对象存储无日志/可观测性(legacy R2 有 traceId/错误码) | low | platform-fitness | no | 加最小日志与错误包装 |
| R16 | vec.sql docs/包内双副本漂移风险(当前一致) | low | correctness / D | no | 单一来源(同 CR-2 R9) |

### R1. 对象存储路径遍历(用户 filename 可达,跨 team 越权 + 任意文件读写)

- **严重级别**：`critical`
- **类型**：`security / B+L`
- **是否 blocker**：`yes`
- **事实依据**：
  - `storage_objects/filesystem_store.py:11-14`(put_text)、`:16-17`(get_text)、`:19-20`(exists)对 object_key 零校验,直接 `self.root / object_key`。
  - **主审实测**:`put_text('../escaped.txt', ...)` 写到 root 之外;绝对路径 key 因 Python `Path(root)/'/abs'` 语义直接丢弃 root,写到任意绝对路径。
  - 来源链:`apps/api/.../routes/ingestion.py:18` `FileInitiateBody.filename: str`(无校验)→ `ingestion/service.py:17` `object_key = f"raw/{team_id}/{upload_id}/{filename}"` → `file_confirm` 调 `object_store.put_text(...)`。`filename` 是 HTTP body 字段,完全用户可控,中间无 `basename`/`normpath`/拒绝 `..`。
- **为什么重要**：
  - 认证用户可借 `filename` 含 `../../../` 跨 team 覆写/读取对象(打穿 team 隔离),或写到 object root 之外的进程可写路径(配置、SQLite db、代码),构成任意文件写/读。直接破坏 legacy "基于 Team UUID 隔离" 的 SaaS 模型。
- **审查判断**：
  - 真实可利用的路径遍历漏洞(事实,非推断):store 层零防御 + 消费方零校验,双重失守。
- **建议修法**：
  - store 内对 key:拒绝绝对路径、拒绝含 `..` 段;`resolved = (self.root / key).resolve()` 并断言 `resolved.is_relative_to(self.root.resolve())`,否则 raise。store 是最后防线必须修;同时 `ingestion/service.py` 对 `filename` 做 `os.path.basename` 纵深防御。

### R2. sqlite-vec/vec0 从不加载,向量索引静默退化为 TEXT 表 + 暴力 cosine(假绿)

- **严重级别**：`critical`
- **类型**：`platform-fitness / B(盲点) + D(断点)`
- **是否 blocker**：`yes`
- **事实依据**：
  - 全仓无 `load_extension`/`enable_load_extension`/`sqlite_vec.load`;`vector_sqlite_vec/engine.py:11-20` 只设 PRAGMA;pyproject 无 sqlite-vec PyPI 依赖。
  - **主审实测**:`USING vec0(...)` → `no such module: vec0`;`apply_vec_schema`(schema.py:62-67)恒命中 except 分支执行 `_fallback_vec_sql`,实建 `chunk_embedding_index` 为普通 `TABLE(rowid INTEGER PRIMARY KEY, embedding TEXT NOT NULL)`。
  - `store.py:91-107` `search()` 不调用任何 KNN,全表 `SELECT vr JOIN cei` + 逐行 `json.loads` + Python `_cosine` + sort top_k。
  - `P4-closure.md:47`/`P5-closure.md:46` 以 ✅ PASS 宣称 vector/retrieval 能力完成;tests/ 下无任何断言该表为 vec0 虚拟表(零守护)。
- **为什么重要**：
  - 这不是"vec0 暂缺但代码就绪",而是**向量索引能力从未存在且为结构性**(三重证据:无依赖声明、无 load 调用、不开 enable_load_extension)。embedding 以 JSON TEXT 存,`float[1536]` 类型约束/维度/ANN 算子全丢;检索退化为 O(N·D) 全扫,team 向量越多越慢;`distance_metric` 字段建了从不被读(search 硬编码 cosine)。设计 SSOT(index §5.7、database.md §6.5)被架空。退化分支零日志 → 系统"看起来正常",closure 据此打绿 = 假绿。
- **审查判断**：
  - 被当成已实现的真盲点(B)+ 设计契约断点(D)。相对 legacy 是两级倒退:Vectorize 托管 ANN →(设计)sqlite-vec KNN →(实际)全表+JSON cosine。
- **建议修法**：
  - ①退化分支至少 `logger.warning` fail-loud,禁止静默;②closure 把 vec/retrieval 能力定级为"degraded/brute-force,非生产 KNN";③若 vec0 为生产前提,pyproject 声明 sqlite-vec 并在 `engine.connect()` 中 `enable_load_extension(True)` + `sqlite_vec.load(conn)`,加载失败 fail-loud;④`search` 读 namespace 的 `distance_metric` 而非硬编码。

### R3. 重复 upsert 致孤儿 rowid 累积,违反一一对应不变量

- **严重级别**：`critical`
- **类型**：`correctness / L`
- **是否 blocker**：`yes`
- **事实依据**：
  - `store.py:32` `rowid = embedding_rowid if ... else self._next_embedding_rowid()`;生产唯一路径(`workflow_rag/service.py`、`purge.py`)均不传 embedding_rowid。
  - **主审实测**:同 chunk_id upsert ×3 → vector_records.embedding_rowid 依次 1→2→3(REPLACE 丢弃旧值),chunk_embedding_index rowids=`[1,2,3]`,**孤儿 `[1,2]`**(index 有但 vr 无)。
- **为什么重要**：
  - 违反 vec.sql:56-57 硬约束「chunk_embedding_index.rowid = vector_records.embedding_rowid 一一对应」。workflow replay/重跑(content_hash 相同会反复 upsert)使孤儿无限累积;真 vec0 下孤儿向量仍参与 KNN 产生检索污染(本地 fallback 因 search 用 JOIN 暂时掩盖)。
- **审查判断**：
  - 逻辑错误 L,违反设计硬约束。相对 legacy 的幂等 upsert(vec_uuid 作主键,覆盖同 id)是退步。
- **建议修法**：
  - upsert 同一 chunk_id 时先 SELECT 复用其现有 embedding_rowid;或分配新 rowid 前 `DELETE FROM chunk_embedding_index WHERE rowid=旧值`。

### R4. 软删后新增致 rowid 重号 + `INSERT OR REPLACE` 静默删除软删审计记录

- **严重级别**：`critical`
- **类型**：`correctness / L + 数据/审计完整性`
- **是否 blocker**：`yes`
- **事实依据**：
  - `_next_embedding_rowid`(store.py:128)用 `MAX(rowid)+1` 基于 **chunk_embedding_index**(会被硬删)。
  - **主审实测**:upsert a(1)、b(2);`delete_chunk('b')` → b 的 vector_records 软删(deleted_at 置位、embedding_rowid 仍=2)、index rowid 2 硬删 → index={1};upsert 新 chunk c → `_next=MAX(1)+1=2` → `INSERT OR REPLACE INTO vector_records` 命中 `UNIQUE(embedding_rowid=2)` 冲突 → REPLACE **静默删除整行 b**;实测 `b survived? 0`。
- **为什么重要**：
  - purge 流程(`purge.py:91`→`delete_chunks`→软删 vr + 硬删 index)正是该组合;随后任何新文档 vectorize 即可能重号,**悄无声息删除一条被软删的合规审计记录**(purge 留痕),破坏 `deleted_at` 软删语义。数据完整性 + 审计完整性双重 critical。
- **审查判断**：
  - 逻辑错误 L,与 R9 软硬删不一致叠加放大。
- **建议修法**：
  - rowid 单调自增且**不复用**(独立序列表,或基于 `vector_records` 的 MAX(embedding_rowid)+1 含软删行);`delete_chunk` 不硬删 index 留空洞,或软硬删保持一致。

### R5. 对象存储无 delete,purge 不清对象 → purged 内容永久残留(合规)

- **严重级别**：`high`
- **类型**：`delivery-gap / B+D`
- **是否 blocker**：`yes`（合规要求驱动）
- **事实依据**：
  - `FileSystemObjectStore` 仅 put_text/get_text/exists,**无 delete**。`workflow_core/purge.py:process_purge_requests` 全程只动 SQLite + VectorStore(`:91 delete_chunks`),**从不 import/接收 object_store**。
  - legacy 明确提供 `deleteR2Object`(r2.ts:194)、`deleteStaticR2Object`(:285)。
- **为什么重要**：
  - 被 purge 的 document 其 chunk_text 对象(`chunks/{team}/{run}/{chunk_id}.txt`)与原始上传对象(`raw/{team}/{upload}/{filename}`)永久残留磁盘。"purge"语义上是数据删除/合规清退,实际对象层一条没删。
- **审查判断**：
  - 能力缺口 B + purge 实现断点 D,合规/隐私实质缺陷。
- **建议修法**：
  - store 增 `delete(object_key)`(同样做 R1 边界校验);`purge.py` 接收 object_store,查 artifacts/static_files/uploads 的 object_key 逐个删除。

### R6. `put_text` 非原子写 + 读回不校验 → 静默损坏

- **严重级别**：`high`
- **类型**：`correctness / C1`
- **是否 blocker**：`no`
- **事实依据**：
  - `filesystem_store.py:14` `path.write_text(...)` 非原子(无 temp+rename),写中途崩溃留半文件;`get_text:17` 直接 read 无校验。
  - `workflow_rag/service.py:107,128` 已把 chunk_text 的 `content_hash`/`size_bytes` 入库,但 `rag_vectorizer/search.py:123-126` 读回时不比对。
- **为什么重要**：
  - 崩溃/并发下半文件被当正常 chunk 文本返回检索结果(静默数据损坏)。R2 网络 PUT 天然原子,本地 FS 退化丢了该性质。
- **审查判断**：非原子写断点。
- **建议修法**：写 temp 后 `os.replace` 原子 rename;search 比对已存 content_hash。

### R7. `embedding_dimension` 硬编码 1536 + `_cosine` 维度静默截断

- **严重级别**：`high`
- **类型**：`correctness / L`
- **是否 blocker**：`no`
- **事实依据**：
  - `store.py:46` INSERT 写字面量 `1536`,`:144` `_ensure_namespace` 同;`embedding: list[float]` 长度从不校验 —— 传 3 维向量仍记 `embedding_dimension=1536`(sub-agent 实跑确认)。
  - `_cosine:154` 用 `min(len(a),len(b))` 截断;5 维 query vs 3 维 stored → score=1.0 无报错(实跑确认)。
- **为什么重要**：维度元数据与真实向量背离(数据完整性);query/stored 维度不一致静默截断产生错误相似度(检索正确性)。两防线皆失。
- **审查判断**：逻辑错误 L + 数据完整性。vec.sql 的 `CHECK(embedding_dimension=1536)` 因硬编码恒满足而形同虚设。
- **建议修法**：写 `len(embedding)` 并对 1536 做真校验;`_cosine` 维度不等 raise。

### R8. 对象存储仅 text,无二进制

- **严重级别**：`high`
- **类型**：`scope-drift / B`
- **是否 blocker**：`no`（当前 API 也只收 str,未即时触发)
- **事实依据**：
  - store 仅 `put_text/get_text`,硬编码 `encoding="utf-8"`;legacy R2 PUT 走二进制 body + ContentType(r2.ts:131)。当前上传链 `file_confirm(content: str)`(routes/ingestion.py:25)全程 str。
- **为什么重要**：`mime_type` 字段存在 + legacy 存二进制,说明设计支持非文本上传;一旦接入真实 PDF,`put_text` 对非 UTF-8 字节抛 `UnicodeEncodeError`。
- **审查判断**：盲点 B(能力面缩小),当前被 API 层 str 限制掩盖。
- **建议修法**：MVP 只做文本则文档化 + mime 白名单;否则加 put_bytes/get_bytes。

### R9. `delete_chunk` 软删 vector_records 但硬删 index,软硬删不一致

- **严重级别**：`high`
- **类型**：`correctness / L`
- **是否 blocker**：`no`（但喂养 R3/R4)
- **事实依据**：`store.py:76-88` vector_records 软删(deleted_at)、chunk_embedding_index 硬删(DELETE)。
- **为什么重要**：软硬删不一致直接制造 R3 孤儿镜像与 R4 重号空洞;保留软删 vr 的"可追溯"被硬删 index 抵消。
- **审查判断**：逻辑不一致,需 owner 明确意图。
- **建议修法**：统一策略(都软删 / 都硬删),且 rowid 不可重号。

### R10. `search` 仅按 team_id 过滤,跨模型错误打分

- **严重级别**：`high`
- **类型**：`correctness / B`
- **是否 blocker**：`no`
- **事实依据**：`store.py:91-100` WHERE 仅 `deleted_at IS NULL AND team_id=?`;无 namespace_id / embedding_model / 维度过滤,无 top_k/limit 下推。
- **为什么重要**：同 team 下多 namespace/多 embedding_model/多维度向量被混在一起算 cosine,产生跨模型错误打分;即便接入 vec0 该缺陷仍在。当前被硬编码 1536(R7)掩盖。
- **审查判断**：盲点 B + 多模型正确性隐患。
- **建议修法**：search 增 namespace_id/embedding_model 过滤参数;vec.sql:12-13 的"单模型单维度"假设需代码 enforce 或文档化。

### R11. `get_text` 抛裸 FileNotFoundError 无人捕获;search TOCTOU

- **严重级别**：`medium`
- **类型**：`correctness / C2`
- **是否 blocker**：`no`
- **事实依据**：`get_text:16-17` 对缺失 key 抛裸 `FileNotFoundError`,全链路无捕获;`rag_vectorizer/search.py:125-126` 是 `exists()` 后 `get_text()` 两步(TOCTOU);`workflow_clean/service.py:34,40` 直接 get 无 exists。
- **为什么重要**：对象层与 DB 元数据不一致时(R5 残留、并发删除)读路径硬崩,异常未分类排障难。
- **审查判断**：错误处理断点 + 真实 TOCTOU 窗口。
- **建议修法**：try/except FileNotFoundError 取代 exists+get;调用方对缺失对象决定跳过或显式 fail。

### R12. purge 中途崩溃 request 卡 'processing' 不被重捞

- **严重级别**：`medium`
- **类型**：`correctness / C3+D`
- **是否 blocker**：`no`
- **事实依据**：`purge.py` vec 侧 `delete_chunks`(:91)独立 commit,core 侧多个 UPDATE + request 收尾延迟到 `:149 conn.commit()`。崩溃在两者之间 → vec 已删、core 停 `pending_purge`、request 停 `processing`;而 `process_purge_requests` 只捞 `status='pending'`(:31),processing 不被重捞。
- **为什么重要**：孤儿 processing request 无重入路径,需人工/清道夫(断点 D)。
- **审查判断**：顺序符合设计 §5.5,但中途崩溃无重入 = 断点。
- **建议修法**：同时捞 pending + 超时 processing(参考 v_stale_claims lease 思路),或 core 每步即时 commit 缩小窗口。

### R13. vectorize 崩溃窗口留 vec 孤儿向量,无补偿器

- **严重级别**：`medium`
- **类型**：`correctness / C3`
- **是否 blocker**：`no`
- **事实依据**：`workflow_rag/service.py` vectorize 五步序:vec.db 在 `:167` 即独立 commit,core `vec_status='vectorized'` 回写延迟到 `:233`。崩溃于两者间 → vec 有向量、core 停 `pending_vectorize`。
- **为什么重要**：`v_search_hydration` post-filter 兜住不脏读(正面),但 vec 残留孤儿无清道夫,replay 重跑放大 R3。
- **审查判断**：符合"状态机保证一致性"原则,读路径安全;缺向量侧补偿。
- **建议修法**：恢复时按 chunk_id 幂等重写(复用 rowid,见 R3 修法);文档化补偿路径。

### R14. 维度三处硬编码 + 无维度迁移路径

- **严重级别**：`medium`
- **类型**：`delivery-gap / D`
- **是否 blocker**：`no`
- **事实依据**：`vec.sql:22,43` CHECK=1536 双表 + `:58-60` `float[1536]` + `store.py:46,144` 硬编码;`vec_schema_migrations` 单条 `vec-0001-ssot`,无 vec-0002。schema 注释(vec.sql:54-55)称换维度"must be recreated as part of a controlled migration",但代码无此机制。
- **为什么重要**：换 embedding 模型(维度变化)需三处硬编码 + CHECK + 已存向量全部重建,无迁移路径承接。呼应 CR-2 迁移无版本化。
- **审查判断**：设计意图与实现脱节,与 CR-2 同源。
- **建议修法**：文档明确"维度变更=全库重建+人工脚本";长期引入版本化迁移序列。

### R15. 对象存储无日志/可观测性

- **严重级别**：`low`
- **类型**：`platform-fitness`
- **是否 blocker**：`no`
- **事实依据**：store 全文无日志/trace/content-type;legacy R2 每操作带 traceId/Logger/ErrorCodes(r2.ts:165 等)。
- **审查判断**：R2→本地 FS 运维可观测性退化,MVP 可接受。
- **建议修法**：后续加最小日志与错误包装。

### R16. vec.sql docs/包内双副本漂移风险

- **严重级别**：`low`
- **类型**：`correctness / D`
- **是否 blocker**：`no`
- **事实依据**：`schema.py:8-14` 路径搜索 docs 优先 + 包内 fallback;两份当前 IDENTICAL(diff 确认),手工同步。
- **审查判断**：当前无害,机制脆弱(同 CR-2 R9)。
- **建议修法**：单一来源(构建期拷贝或只读包资源)。

---

## 3. In-Scope 逐项对齐审核

> 计划项来自 index §3 CR-3 表格的"关注"与"已知风险"。

| 编号 | 计划项 / 设计项 / 已知风险 | 审查结论 | 说明 |
|------|----------------------------|----------|------|
| S1 | FileSystemObjectStore 路径安全 / 原子写 | `missing` | R1 路径遍历(critical 安全)+ R6 非原子写 |
| S2 | ObjectStore 能力面(delete/binary) | `missing` | R5 无 delete(purge 不清对象)+ R8 无二进制 |
| S3 | VectorStore upsert / delete / search | `partial` | 能跑,但 R3/R4 rowid 破坏 + R9 软硬删不一致 + R10 过滤缺失 |
| S4 | vec0 rowid ↔ vector_records.embedding_rowid 一一对应 | `missing` | R3/R4 实测破坏不变量 |
| S5 | distance metric 与维度一致性 | `missing` | R2 metric 被忽略 + R7 维度硬编码/截断 |
| S6 | vec0 / sqlite-vec 向量索引能力 | `missing` | R2 从不加载,静默退化为 TEXT 表 + 暴力 cosine(假绿) |
| S7 | vec.sql schema 保真(表/索引/视图/CHECK) | `done` | 实测干净建库,约束逐条生效,幂等成立 |
| S8 | 已知风险 C3 跨库一致性 | `partial` | 架构正确 + 读路径 post-filter 安全;写路径漂移不自愈(R12/R13) |

### 3.1 对齐结论

- **done**: `1`(S7)
- **partial**: `3`(S3、S8)→ 实为 2 项 partial(S3、S8)
- **missing**: `5`(S1、S2、S4、S5、S6)
- **stale**: `0`
- **out-of-scope-by-design**: `0`

> 它更像"vec.db 的关系层 schema 已正确落地,但对象存储有安全漏洞、向量索引能力从未真正实现、VectorStore 写路径破坏数据完整性",而非 completed。schema 是本簇唯一成熟的部分;对象存储安全与向量索引核心是最严重的缺口。

### 3.2 stub / 真实现标定表(index §7.1 必交项)

| 文件 | 公开符号 | 标定 | 依据 |
|------|----------|------|------|
| filesystem_store.py | `put_text/get_text/exists` | 真实现(有 critical 安全缺陷) | R1 路径遍历 + R6 非原子 |
| filesystem_store.py | `delete` | **缺失** | R5,purge 因此清不掉对象 |
| filesystem_store.py | `put_bytes/get_bytes` | **缺失** | R8,无二进制能力 |
| vec engine.py | `VecSQLiteEngine.connect` | 真实现(缺扩展加载) | R2,从不 load sqlite-vec |
| vec schema.py | `apply_vec_schema` | 真实现(恒走退化) | R2,vec0 恒失败 → TEXT 表 |
| vec schema.py | `_fallback_vec_sql` | 真实现(静默退化器) | R2,无告警,造成假绿 |
| store.py | `upsert_chunk` | 真实现但**逻辑错误** | R3/R4 破坏 rowid 不变量 |
| store.py | `delete_chunk/delete_chunks` | 真实现但软硬删不一致 | R9 |
| store.py | `search` | 部分(暴力实现,非 KNN) | R2/R10,全表 cosine,过滤缺失 |
| store.py | `_cosine` | 真实现但维度静默截断 | R7 |

---

## 4. Out-of-Scope 核查

| 编号 | Out-of-Scope / Deferred 项 | 审查结论 | 说明 |
|------|----------------------------|----------|------|
| O1 | G-CR1-01 时间格式 bug 根因 | `遵守(归 CR-1)` | CR-3 store 时间走内联 strftime(正确),不污染;不在本簇改 _utils.py |
| O2 | SearchService / search 路由 API 面深审 | `部分(移交 CR-7/CR-8)` | 本簇仅为 C3 一致性追踪 search hydration;API 契约深审属后续簇 |
| O3 | rag vectorize 业务编排(embed 模型选择等) | `部分(移交 CR-7)` | 本簇仅审 vectorize 的 C3 五步序与 vec 写入;业务逻辑归 RAG 簇 |
| O4 | 迁移版本化机制 | `遵守(同 CR-2)` | R14/R16 与 CR-2 R7/R9 同源,记录但不在本簇重复深挖 |
| O5 | PRAGMA foreign_keys=OFF(vec) | `误报已澄清` | CR-2 已判为 vec 合理分化,本簇复核确认无冲突 |

### 横切维度 C1–C5 对 CR-3 的逐项结论

| 维度 | 结论 | 证据 |
|------|------|------|
| C1 事务与并发 | `fail` | put_text 非原子(R6);upsert 进程内原子但 `INSERT OR REPLACE` 重号静默删行(R4,原子但语义错误) |
| C2 错误处理 | `fail` | get_text 裸 FileNotFoundError 无人捕获 + search TOCTOU(R11);store 无错误包装/日志(R15) |
| C3 一致性 | `partial` | 架构方向正确 + 读路径 post-filter 安全(正面);写路径漂移不自愈:purge processing 孤儿(R12)、vectorize vec 孤儿(R13);rowid 不变量破坏(R3/R4) |
| C4 可观测性 | `fail` | 对象存储零日志;vec 退化静默无告警(R2)—— 直接导致假绿 |
| C5 适配层纪律 | `partial` | 消费方确实经 ObjectStore/VectorStore 适配层(纪律 pass),但**适配层本身有 critical 缺陷**(路径遍历 R1、退化 R2),适配层未提供其承诺的安全/能力边界 |

---

## 5. 最终 verdict 与收口意见

- **最终 verdict**：`changes-requested`（实质接近 blocked：含安全漏洞 + 向量核心能力不可用)
- **是否允许关闭本轮 review**：`no`
- **关闭前必须完成的 blocker**：
  1. **R1**:`FileSystemObjectStore` 增 object_key 边界校验(拒绝绝对路径/`..`、resolve 后断言在 root 内),`ingestion` basename 收口 —— 路径遍历安全漏洞。
  2. **R2**:向量索引退化 fail-loud(告警 + 依赖声明 + `enable_load_extension`/`sqlite_vec.load`),并将 P4/P5 closure 的 vector/retrieval gate 重新定级为 degraded —— 修正假绿。
  3. **R3 + R4**:修 `upsert_chunk`/`_next_embedding_rowid`,使 rowid 一一对应不变量成立、不复用、不静默删除软删审计记录 —— 数据/审计完整性。
  4. **R5**:store 增 delete + purge 接 object_store 删对象 —— 合规清退。
- **可以后续跟进的 non-blocking follow-up**：
  1. **R6**:原子写 temp+os.replace;**R7**:维度写实际长度 + cosine 维度不等 raise;**R9**:统一软硬删策略。
  2. **R10**:search 增 namespace/embedding_model 过滤;**R8**:二进制能力或文档化文本-only。
  3. **R11**:错误处理与 TOCTOU;**R12/R13**:purge/vectorize 崩溃补偿与重入;**R14/R16**:维度迁移与双副本(同 CR-2)。
  4. **R15**:对象存储最小可观测性。
- **建议的二次审查方式**：`independent reviewer`（R1 安全修复需独立验证逃逸已封堵;R2 需确认 vec0 真实加载或明确 degraded 定级;R3/R4 需复跑 rowid 不变量回归)
- **实现者回应入口**：`请按 docs/templates/code-review-respond.md 在本文档 §6 append 回应,不要改写 §0–§5。`

> 本轮 review 不收口。CR-3 是迄今最严重的一簇:对象存储有可被用户输入触达的路径遍历漏洞(R1),向量索引能力从未真正存在且 closure 假绿(R2),VectorStore 写路径在两条常见路径破坏数据/审计完整性(R3/R4),purge 不清对象造成合规残留(R5)。vec.db 关系层 schema 与 C3 读路径架构是健康的,但上述 blocker 必须先修再复审。

---

## 附录 · legacy 能力对照速查(R2 + Vectorize → 本地)

| legacy 能力 | 本地实现 | 判断 |
|---|---|---|
| R2 PUT(原子) | put_text(非原子) | 断点(R6) |
| R2 二进制 + ContentType | 仅 UTF-8 text | 盲点(R8) |
| R2 DELETE / static DELETE | 无 | 断点(R5) |
| R2 key 基于 team_uuid + 服务端边界 | key 前缀 team 但无边界校验 | 漏洞(R1) |
| Vectorize 托管 ANN KNN | 全表 + Python cosine | 两级倒退(R2) |
| Vectorize upsert 幂等(id 主键) | rowid MAX+1 重号 | 逻辑错误(R3/R4) |
| Vectorize deleteByIds 硬删 | vr 软删 + index 硬删 | 不一致(R9) |
| DO Mutex 串行 + 429 拒并发 | 无锁,依赖单连接顺序 | 盲点(并发未控) |
| purger_logic 批量删 + force 重置 | purge 不清对象 + processing 不重入 | 断点(R5/R12) |
