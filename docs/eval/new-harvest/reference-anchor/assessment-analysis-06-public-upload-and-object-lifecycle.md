# 调查面 `06` · 公共上传、S13 bytes identity 与 object lifecycle — 深度评估

> **对象 / scope-fence**：authenticated upload contract；stream/size/digest；CAS replay；catalog-without-business-ref；orphan grace；concurrent upload；read boundary；随后 `local_object` ingest 的**衔接点**（不拥有 ingest 本身）。  
> **本面不含**：创造/修改 Intake identity、Source、Item、Revision（交由面 `03/04/08`）；purpose 字符串冻结（`T-P-NH-8` / QNA §10.2）；HTTP 路径/multipart 形状冻结。  
> **日期**：`2026-08-29`  
> **作者**：`Grok analysis-fleet / review-fleet`（fleet / panel：`new-harvest-reference-anchor` · face `06`）  
> **文档性质**：`assessment / analysis`（单面 measure-first 深评；零决策——只 MARK 不裁决）  
> **文档状态**：`draft`  
> **流水线位置**：站② · 上游 = [[assessment-index]]（消费其冻结分母 `D-14`/`D-15`）  
> **对照参考**：`docs/baseline/domain-truth/S13-artifact-storage.md` S13-v1.1；`docs/eval/new-harvest/pre-initial-planning-qna.md` v0.5 `T-O-385`；HEAD `1221aa1`  
> **上游权威输入**：
> - `docs/eval/new-harvest/assessment-index.md` — §2.2 冻结分母 / §3.06 本面登记 / §4 `G-NH-07`
> - `docs/eval/new-harvest/pre-initial-planning-qna.md` — `T-O-376/381/383/385`
> - `docs/baseline/domain-truth/S13-artifact-storage.md` — purpose 闭集、无公网 object API 原完成定义 + 被 `T-O-385` 窄 reopen
> **下游消费者**：`docs/eval/new-harvest/planning-proposed.md` · `pre-charter-qna.md`（owner-gate 裁决）· 设计/执行制品 · 面 `03/08/09`

---

## 0. Verdict（结论先行）`[核心]`

- **0.1 一句话缺口 / 现状判断**：HEAD 已有 team-scoped CAS、verify-on-read、catalog unique 与 GC delete-fence，但公共上传面为 **0**（`D-14`）、caller-upload purpose 为 **0**（`D-15`）；直接暴露内部 `promote` **不能**自动解决 catalog、orphan/GC 与 upload→ingest 竞态。`T-O-385` 要求的「受鉴权上传只创造 handle+digest+size、不创造 Item」在代码里仍是净新缝。
- **0.2 Top blockers（最关键断点）**：
  1. `NH-RA06-B01`：public `/v1` 无 object/upload/multipart 路由；`local_object` 今日依赖内部 promote（README 明示无公共上传端点）。
  2. `NH-RA06-B03`：合法「刚上传尚未 ingest」与 GC 的 catalog-orphan 是同一类（无 live ref）；grace 内无 hold/pending 契约则 ingest 与 GC 竞态。
  3. `NH-RA06-B05`：`ObjectStorePort.promote` 吃整段 `bytes`；默认 HTTP 体帽 `MKB_MAX_REQUEST_BYTES=1MiB` 远小于对象帽 256MiB——无流式/分块合同就不能兑现真实 PDF/doc。
- **0.3 总体方向建议**：沿用 S13 内核（CAS path、verify-on-read、unique live catalog、grace+quarantine fence），只建 **受鉴权 upload 缝**（catalog/hold、幂等 replay、与 `local_object` ingest 分账）。**不**把 R2/presign/file-row 当身份。`G-NH-07` 三选项并列，本文不裁决。
- **0.4 如何读本台账**：见模板图例（`✅借` / `🔶部分借` / `⛔反例` / `🆕净新`）。本面主题轴 = `公共表面` / `bytes identity` / `catalog+ref` / `GC grace 竞态` / `read boundary` / `ingest 衔接`。

---

## 1. 方法与证据基线 `[核心]`

> 先证可证性，再下判断。置信：`HEAD 实测 > 仓内文档锚 > 外部参考`。`T-O-376..389` 只 CITE，不改写。

- **1.1 本仓证据（如何测量）**：
  - HEAD：`api/public/routes.py` 全部 `@router.`；`src/contracts/storage/models.py` purpose Literal；`src/storage/{ports,local_store}.py`；`src/services/object_gc.py` + `src/runtime/object_gc.py`；`src/persistence/migrations/001_initial.sql` / `014_ns5_uuid_and_tombstone.sql`；`src/runtime/task/task_create.py`；`src/services/{artifacts,config_snapshots}.py`；`src/runtime/intake/acquisition_ingest.py`；`src/contracts/api/{models,generation}.py`；`src/runtime/config.py`；`api/app.py`；`tests/unit/test_object_gc.py`、`tests/unit/test_ns6_gc_toctou.py`；`tests/e2e/test_source_capability_paths.py`。
  - Baseline：`S13-artifact-storage.md`；glossary `LogicalObjectHandle`；QNA `T-O-385`。
  - legacy-family（只读、不导入运行）：`smind-admin/ingestion/files.ts`、`smind-admin/core/r2.ts`、`smind-skill-clean-universal/services/{io_manager,action_registry}.ts`、`smind-skill-rag-constructor/services/io_manager.ts`。
- **1.2 外部 / 参考来源 + 置信**：

| 原子问题 | 搜索词 | 打开的 primary URL | 版本 / 发布 | 访问日 | 支撑的原子结论 | 限制 / 失败条件 |
|----------|--------|-------------------|-------------|--------|----------------|-----------------|
| resumable + checksum + 过期 | `TUS resumable upload protocol checksum official` | https://tus.io/protocols/resumable-upload.html | tus 1.0.0 · 2016-03-25 | 2026-08-29 | Creation 与 PATCH 分步；Checksum 扩展按块校验；Expiration 回收未完成上传 | Checksum 为扩展非核心；SHA1 为协议最低算法，不是本仓 CAS 身份；路径由实现自定 |
| MPU checksum ≠ 全对象 SHA | `S3 multipart upload ETag checksum official AWS` | https://docs.aws.amazon.com/AmazonS3/latest/userguide/checking-object-integrity-upload.html ；https://docs.aws.amazon.com/AmazonS3/latest/userguide/mpuoverview.html | AWS S3 User Guide（页脚 2026-08-29） | 2026-08-29 | MPU ETag **不是**全对象 MD5/SHA；SHA-256 在 MPU 上只支持 composite；未 complete/abort 的 part 持续计费 | 云对象键模型；不得借 R2/S3 当 MKB identity |
| CAS 身份 digest vs media | `content-addressed storage CAS identity collision media type` | https://github.com/opencontainers/image-spec/blob/main/descriptor.md | OCI image-spec descriptor（GitHub main；规范字段稳定） | 2026-08-29 | blob 身份是 digest；descriptor 另含 size+mediaType；校验应先比 size 再哈希 | mediaType 是描述子字段，**不是** CAS 键；同 digest 不同 media 仍是同一 blob |
| 上传安全反例 | `OWASP unrestricted file upload cheat sheet` | https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html | OWASP Cheat Sheet Series | 2026-08-29 | 不信任 `Content-Type`；文件名不得当身份；必须鉴权；公开取回放大威胁 | 扩展名白名单/杀毒是行业建议，本仓 identity 是 digest 不是 filename |
| 并发 precondition | `Google Cloud storage object generation preconditions official` | https://docs.cloud.google.com/storage/docs/request-preconditions | Cloud Storage docs · Last updated 2026-08-26 UTC | 2026-08-29 | `ifGenerationMatch` / `0`=仅当无 live 对象；失败 `412` | XML MPU **不支持** preconditions（`400 NotImplemented`）；generation 是名字寻址世代，不是 digest |
| orphan/lease GC | （GC 竞态第二源）containerd 官方 GC | https://github.com/containerd/containerd/blob/main/docs/garbage-collection.md | containerd docs/main | 2026-08-29 | 无引用且无 lease 即可被 GC；lease 默认约 24h 防进程中途死亡 | Go/gRPC 栈；标签引用模型不可直搬 |

规范单源已 MARK：TUS 协议正文（tus.io）为 checksum/resume 的规范权威；S3/GCS 为各自官方用户指南，互为独立云厂商。禁止用 SEO 博客单独支撑 S1。

- **1.3 ★ 可复现命令清单（measure-first）**：
```bash
git rev-parse HEAD
# 期望：1221aa1ba3bcc8d5be38f7d2529a052dcf93b256

rg -n '^\s*@router\.' api/public/routes.py
rg -n '^\s*@router\..*(object|upload)|multipart|UploadFile' api/public/routes.py api -g '*.py'
nl -ba src/contracts/storage/models.py | sed -n '12,36p'
nl -ba src/storage/local_store.py | sed -n '17,123p'
nl -ba src/services/object_gc.py | sed -n '107,282p;304,327p'
nl -ba src/persistence/migrations/001_initial.sql | sed -n '837,888p;1799,1811p'
nl -ba src/persistence/migrations/014_ns5_uuid_and_tombstone.sql | sed -n '17,20p'
nl -ba src/runtime/task/task_create.py | sed -n '67,105p'
nl -ba src/runtime/config.py | sed -n '26,72p'
nl -ba src/runtime/intake/acquisition_ingest.py | sed -n '413,455p'

python3 - <<'PY'
from pathlib import Path
import re
text = Path("api/public/routes.py").read_text()
print("public_router_count", len(re.findall(r"^\s*@router\.(get|post|patch|delete|put)\(", text, re.M)))
block = Path("src/contracts/storage/models.py").read_text().split("purpose: Literal[")[1].split("]")[0]
print("purpose_lits", re.findall(r'"([^"]+)"', block))
print("handle", re.search(r'_HANDLE_ID = re.compile\(r"([^"]+)"\)', Path("src/storage/local_store.py").read_text()).group(1))
PY

uv run pytest tests/unit/test_object_gc.py tests/unit/test_ns6_gc_toctou.py -q --tb=line
# 2026-08-29 实测：10 passed
```

- **1.4 范围围栏**：本面**只**覆盖上传合同、S13 bytes 身份、catalog/orphan/GC、read 边界、与 `local_object` ingest 的 handle 交接。**不**拥有 acquire/decode（面 03）、clean（面 04）、publication（面 08）、横切 replay 证明矩阵（面 09 消费本面不变量）。禁止冻结 HTTP 路径、multipart 形状、purpose 字面。

---

## 2. 当前结构分析（HEAD 实测 · measure-first）★ `[核心]`

### 2.1 ★ 冻结分母（FROZEN denominators · HEAD）

> 共享分母引自 [[assessment-index]] §2.2，不得另估。本面新测分母另表。

| 分母 | HEAD 实测值 | 证据锚（`path:line`） | 来源 |
|------|-------------|------------------------|------|
| `D-14` public `/v1` route / object-upload route | `28 / 0` | `api/public/routes.py:56-452`；本面 `rg` + python 计数 28 条，路径含 object/upload/multipart = 0 | `index §2.2` |
| `D-15` S13 purpose / caller-upload purpose | `8 / 0` | `src/contracts/storage/models.py:17-27`；DDL CHECK 同闭集 `001_initial.sql:859-862` | `index §2.2` |
| handle 物理格式（adapter） | `mkbobj:v1:{team_uuid}:{sha256}`；regex `^mkbobj:v1:([0-9a-f-]{36}):([0-9a-f]{64})$` | `src/storage/local_store.py:17-21,101` | 本面新测 |
| `ObjectHandle` 契约 pattern | `^mkbobj:v1:[a-zA-Z0-9._:-]+$`（宽于 adapter） | `src/contracts/storage/models.py:12-13`；`src/contracts/api/models.py:119` | 本面新测 |
| S13/glossary handle 规范 | `mkbobj:v1:<team_uuid>:<stored_object_uuid>`（opaque，**不含 digest**） | `S13-artifact-storage.md` S13-T002；`docs/baseline/spec-glossary.md:530` | 仓内文档锚（与 HEAD 冲突，见 §2.9） |
| 单对象 max size | 默认 `256 MiB` = `268435456`；Settings `object_max_bytes` `ge=1 le=1GiB` | `src/storage/local_store.py:32-34,72-73`；`src/runtime/config.py:58`；`data/config/default.toml:17-18` | 本面新测 |
| HTTP 请求体帽 | 默认 `1 MiB`（`MKB_MAX_REQUEST_BYTES` / `max_request_bytes`） | `src/runtime/config.py:26`；`README.md:210,556` | 本面新测 |
| GC grace 配置项名 | 代码：`Settings.object_gc_grace_seconds`（默认 `86400`，`ge=1`）；服务构造：`orphan_grace`；S13 文档名：`object.orphan_grace` | `src/runtime/config.py:70`；`src/services/object_gc.py:112-125`；`api/app.py:348-351`；`S13-artifact-storage.md:334-336` | 本面新测 |
| GC interval / batch | `object_gc_interval_seconds` 默认 600；`object_gc_batch_size` 默认 100 | `src/runtime/config.py:69-72`；`src/runtime/object_gc.py:19-29` | 本面新测 |
| catalog 无 business-ref | **DDL 允许**（`mkb_stored_objects` 无「必须有 ref」约束）；生产写入路径均 catalog+ref 同 UoW；GC 测试显式插入无 ref 行作为 orphan | `001_initial.sql:837-873`；`src/services/artifacts.py:143-169`；`tests/unit/test_object_gc.py:41-63` | 本面新测 |
| live unique | `(team_uuid, content_digest, size_bytes) WHERE tombstoned_at IS NULL` | `001_initial.sql:1800-1801` 全表 unique → `014_ns5_uuid_and_tombstone.sql:17-20` 改为 live 部分唯一 | 本面新测 |
| Port 方法（HEAD） | `promote(bytes)` / `read_verified` / `delete_if_unreferenced` / `quarantine_object` / `restore_quarantined` / `destroy_quarantined` / `readiness`；**无** `open_write_stream` | `src/storage/ports.py:10-24` | 本面新测 |
| public generation-artifact 读 | 3 条 GET，返回元数据+`logical_handle`，**不**返回对象字节 | `api/public/routes.py:226-294`；`src/contracts/api/generation.py:28-62` | 本面新测 |

### 2.2 轴「公共表面」（HEAD 核验）

- 28 条 `/v1` 路由全挂 `BusinessToken`（`api/public/routes.py:56-454`）。集合是 Team/Task/Gate/restart/lineage/retrieval 与 **generation-artifact 投影**，没有任何 object/upload 路径。内部 `api/internal/routes.py` 同样 0 条 object 路由。
- README 把 `local_object` 标成「已落地（前置条件）」：公共 API **没有**对象上传端点，调用方须经「受信任的内部装载流程」先有 handle（`README.md:211`）。e2e `test_source_capability_paths.py:77-82` 正是测试进程内 `container.storage.promote(...)` 再把 handle 塞进 Task——这不是公共合同。
- `T-O-381`/`T-O-385` 要求公共上传落地；S13 完成定义第 7 条原为「无公网 object API」（`S13-artifact-storage.md:77,430`；S13-T031）。QNA 将其标为 **窄 reopen**（`pre-initial-planning-qna.md:89,768`）：受鉴权 Port 暴露 handle，对象存在仍 ≠ 业务成功。HEAD 尚未实现该 reopen。

### 2.3 轴「bytes identity / handle」（HEAD 核验）

- Adapter 把 handle 写成 `mkbobj:v1:{team_uuid}:{digest}`（`local_store.py:101`），解析时校验 team 与 64-hex digest（`local_store.py:21,107-113`）。跨 team → `OBJECT_AUTH_TEAM_MISMATCH` 403。
- CAS 物理路径：`objects/<team_uuid>/sha256/<aa>/<bb>/<64hex>`（`local_store.py:38-39`）。同 team 同 digest 复用文件；已有文件哈希对不上 → `OBJECT_INTEGRITY_COLLISION` 503（`local_store.py:84-87`）。
- Catalog 幂等键是 **`(team_uuid, content_digest, size_bytes)` live unique**（`014_ns5_uuid_and_tombstone.sql:17-20`）。`media_type` **不在** unique 内。`T-O-385` 明文：同一 team、同一 sha256+size → replay 同一 handle（`pre-initial-planning-qna.md:89,450-451`）。
- `PromoteRequest.purpose` 是 8 元 Literal，**无** caller-upload（`models.py:17-27`）。`LocalObjectStore.promote` **完全不读 purpose**（`local_store.py:71-78` 只传 `team_uuid`/`media_type`）。purpose 只在 `mkb_object_references` 写入时生效（`artifacts.py:164-169`）。
- Handle 合同 pattern 宽于 adapter（允许 `._:-` 任意段）。S13-T002 / glossary 则要求 **stored_object_uuid**、禁止 digest 进 handle。HEAD 注释自称「pre-transaction identity」，catalog 以后「可以更 opaque」（`local_store.py:17-20`）——公共上传若把今日 handle 直接交给调用方，就把 digest 冻成对外身份。这与 `T-O-385`「同一 sha256+size → 同一 handle」相容，与 S13-T002 字面冲突。只登记，不裁决。

### 2.4 轴「promote / catalog / ref」（HEAD 核验）

- **Bytes-first 已落地**：`promote` 先写盘（staging `mkstemp` → `fsync` → `os.replace` → `fsync` dir），返回 `ObjectStat`；注释写明未写 catalog+ref 则「不是业务可用」，TX 失败留下 orphan 给 GC（`local_store.py:25-29,71-105`）。
- **Catalog 不在 Port 内**：所有 `INSERT INTO mkb_stored_objects` 发生在服务层（`artifacts.py:157-169`、`config_snapshots.py:338-368`、acceptance/generation 等同构）。模式是：`live_stored_object_uuid` 按 digest+size 查找 → 无则 uuid7 插入 catalog → **立刻**插入一条 live ref。
- **今日 promote 绑定业务创建**：`task_create.py:70-72` 注释：object promotion **只发生在真正 new Task**；exact replay 不得制造新 orphan。`config_snapshots.py:145-150` 在 Task UoW 之前 promote inline/config/manifest；rollback 只留未引用 CAS。随后 `_catalog_object` 在 Task UoW 里补 catalog+`process_io` ref（`config_snapshots.py:323-368`）。这证明：**没有独立 upload 事务**。
- 无 ref 的 catalog 行：DDL 允许；GC 测试 `_seed_orphan` 只插 `mkb_stored_objects`、零 `mkb_object_references`（`test_object_gc.py:48-62`），过 grace 后即被收集。因此「catalog-without-business-ref」**已经是 orphan 类**，不是第三种合法稳态。
- Tombstone 后同一 digest 可再插新 `stored_object_uuid`（部分 unique 只约束 live；`test_object_gc.py:285-303`）。若对外 handle 含 digest，replay 仍可返回同一 handle 字符串；若对外 handle 含 uuid，tombstone 后再上传会换身份——与 `T-O-385` 张力，见 `NH-RA06-B12`。

### 2.5 轴「GC / grace / 竞态」（HEAD 核验）

- Scanner 只查 **已 catalog、未 tombstone、created_at ≤ now-grace、无 live ref** 的行（`object_gc.py:143-161`）。**磁盘上已 promote、从未 catalog 的字节对 GC 不可见**。
- grace 默认 24h；`orphan_grace <= 0` 构造期 `ValueError`（`object_gc.py:116-120`；`test_object_gc.py:274-279` 23h59m 不收集、0 grace 拒绝）。与 S13-T026 一致。
- Delete fence：TX1 recheck blocker → `quarantine_object`（rename 出 CAS）→ TX2 再 recheck → 无 blocker 则 proof+tombstone 后 `destroy_quarantined`；TX2 见 live ref 则 `restore_quarantined`（`object_gc.py:189-282,8-12`）。`test_ns6_gc_toctou.py:69-77` 证明 quarantine 窗口插入 live ref → `LIVE_REFERENCE` 且字节恢复。缺 quarantine API → `OBJECT_UNAVAILABLE_GC` 503 fail-closed（`object_gc.py:285-291`）。
- Blocker：live ref / `operator_hold` / `backup_hold` / 重复 catalog digest / open cleanup intent 点名该对象（`object_gc.py:304-331`）。
- **对公共上传的含义**：若 upload 只 promote 不 catalog → 磁盘泄漏，ingest 仍可能 `read_verified` 成功（今日 local_object 正是这样）。若 upload 写 catalog 不写 ref → 24h 后与「被放弃的 orphan」无法区分，GC 可删，随后 ingest 得 `OBJECT_MISSING`。grace 本身不能表达「合法等待 ingest」。需要 **live ref 或 hold**（purpose 字面不锁，但必须进入闭集）。

### 2.6 轴「read boundary」（HEAD 核验）

- 内部 `read_verified`：**不查 catalog、不查 live ref**，只解析 handle 的 team+digest 并校验文件哈希（`local_store.py:107-122`）。因此「持有 handle」≈「能读字节」，只要文件还在。
- 公共面已有 **Task 作用域 generation-artifact 元数据读**（`routes.py:226-268`）：返回 `logical_handle`+digest+size，明确「runtime/storage id 不得出界」（`generation.py:1-6,50-54`）。这是「仅业务 artifact read」的**元数据**正例，不是对象字节下载。
- `G-NH-07` 三选项（upload-only / upload+authenticated read / 仅业务 artifact read）均未冻结。HEAD 现状 = 无 upload + 有业务 artifact 元数据读 + 无公共 raw GET。QNA `T-O-385` 只钉上传身份，不钉 raw read（thoughts 叙事要求澄清 public read，非 Truth）。

### 2.7 轴「local_object ingest 衔接」（HEAD 核验）

- Descriptor 只要 `logical_handle` 匹配宽 pattern（`models.py:116-121`）。acquire：`read_verified` 后从字节构造 representation，**不**要求 catalog 行（`acquisition_ingest.py:443-455`）。
- 因此：内部 promote → 立刻 ingest 在 HEAD 上能工作（e2e 如此）。这 **不能**证明公共 upload 合同成立，因为它绕过 catalog/ref/GC/鉴权表面。
- 后续 acceptance 会 **再次** promote raw/clean 文本并在 outcome UoW catalog（`acceptance_snapshot.py:54-67,107-114`）。原始上传字节若未被 catalog+ref，仍可能成为磁盘孤儿。面 03/04/08 拥有 ingest；本面只要求 upload 成功留下 **可被 ingest 消费且 GC 在 grace/hold 内不抢删** 的 handle。

### 2.8 轴「预算 / 流 / 安全」（HEAD 核验）

- 对象帽 256MiB 在 `promote` 入口按 `len(data)` 强制，超限 `OBJECT_BUDGET_SIZE` 413（`local_store.py:72-73`）。整对象进入内存；无 chunked writer。
- 公共 HTTP 默认 1MiB 体上限（`config.py:26`）。把 `promote` 接到 JSON/body 路由会在对象层之前被 413。真实 PDF 与 inline 帽矛盾——这正是 Q5 反对方案 C 的理由（`pre-initial-planning-qna.md:436,457`）。流式/分块形状 **不冻**，但「必须有界、必须在对象层算 SHA-256」是 S13-T012/T020 已有法。
- 无 `UploadFile` / `multipart` 符号（全仓 `*.py` grep 空）。无文件名落盘：CAS 路径不含 caller filename（正例）。无 MIME 白名单、无 malware 扫描（上传面尚未存在）。`expected_sha256` 可选，不匹配则 422（`local_store.py:75-76`）。

### 2.9 轴「规范 vs HEAD 漂移」（登记，不自动覆盖）

| 声称 | HEAD | 失真类型 |
|------|------|----------|
| S13-T002 / glossary：handle = team+`stored_object_uuid`，不含 digest | handle = team+sha256 | 执行漂移；`T-O-385` 又要求按 sha256+size replay 同一 handle |
| S13-T022 Port：`open_write_stream` / `finalize_write` / `open_verified_read` | `promote(bytes)` / `read_verified` 全量 bytes | 窄实现；对 256MiB 公共上传可能不够 |
| S13 完成定义第 7 条 / T031：无公网 object API | 代码仍无；QNA `T-O-385` 窄 reopen 尚未落地 | 冻结≠已实现 |
| 「有 ObjectStorePort/GC 即有上传」（index §2.4 已校正） | route/purpose/catalog-on-upload = 0 | 高估 |
| initial `NH2-01`「暴露 promote」 | promote 忽略 purpose、不写 catalog | 叙事/初判；本面证伪「直接暴露即可」 |

---

## 3. 借鉴锚定矩阵（Reference Anchor Matrix）★ `[核心]`

| 借鉴点 | 来源锚（`path:line` / URL） | 借鉴 verdict | 借什么 / 不借什么 |
|--------|------------------------------|--------------|--------------------|
| team-scoped digest handle + CAS path | `src/storage/local_store.py:17-21,38-39,101` · `RA-06-HEAD-01` | `✅借`（本仓已有） | 借 team 命名空间与 digest 路径。不把 digest-in-handle 自动升级为已冻对外身份（与 S13-T002 冲突，见 `NH-RA06-B07`） |
| verify-on-read + digest/team fail-closed | `local_store.py:75-76,84-87,107-122` · `RA-06-HEAD-02/05/06` | `✅借` | 借读时再哈希、team mismatch 403、expected digest 422。不借「无 catalog 也能读」作为公共合同 |
| live unique `(team,digest,size)` | `014_ns5_uuid_and_tombstone.sql:17-20`；`artifacts.py:27-35` · `RA-06-HEAD-03` | `✅借` | 借幂等分母，对齐 `T-O-385`。不把 `media_type` 放进身份 |
| GC grace>0 + quarantine fence + restore | `object_gc.py:8-12,116-120,189-282`；`test_ns6_gc_toctou.py:69-77` · `RA-06-HEAD-04/10` | `✅借` | 借 TX1/TX2 + quarantine。不把「无 live ref」直接当成「可删的废弃上传」 |
| bytes-first：promote 后才 catalog | `local_store.py:25-29`；`task_create.py:70-72`；`artifacts.py:1-8` · `RA-06-HEAD-07` | `✅借` | 借对象存在≠业务成功。不借「promote 绑定 Task create」作为唯一入口 |
| 业务 artifact 元数据读 | `api/public/routes.py:226-268`；`generation.py:1-6` · `RA-06-HEAD-08` | `🔶部分借` | 借 Task 作用域、鉴权、不泄漏 path。不把 metadata GET 当成 raw bytes 下载，也不预判 `G-NH-07` |
| `local_object` 已能消费 handle | `acquisition_ingest.py:443-455`；`models.py:116-121` · `RA-06-HEAD-09` | `🔶部分借` | 借衔接点：ingest 只吃 handle。不借「无 catalog 的内部 promote」冒充公共 upload DoD |
| 无 public upload / 无 caller purpose / 无 multipart | `routes.py:56-452`；`models.py:17-27`；全仓无 `UploadFile` · `RA-06-HEAD-11..14` | `⛔反例`（本仓缺口） | 钉住「内核≠产品面」。禁止把 Port 当 HTTP |
| GC 看不见未 catalog 字节；无 ref catalog = orphan | `object_gc.py:146-161`；`test_object_gc.py:41-63` · `RA-06-HEAD-15/16` | `⛔反例`（对 upload 竞态） | 证明直接暴露 promote 不够 |
| `read_verified` 不查 catalog | `local_store.py:107-122` · `RA-06-HEAD-17` | `⛔反例`（若开放 raw read） | 公共 read 必须另加授权/live-ref 策略，不能直接导出 Port |
| 1MiB HTTP vs 256MiB 对象；整段 `bytes` | `config.py:26,58`；`ports.py:12` · `RA-06-HEAD-18` | `⛔反例` | 公共上传需要有界流，形状不冻 |
| handle digest vs S13 uuid | `local_store.py:21` vs `S13-artifact-storage.md` S13-T002；glossary `:530` · `RA-06-HEAD-19` | `⛔反例`（规范冲突） | 只登记；执行阶段对齐，不在本文改 Truth |
| RAG 两步 init + `pending_upload` + confirm（**不是** static 流） | `context/legacy-family/smind-admin/ingestion/files.ts:370-460`（`handleRagFileInitiate`）+ `:463-568`（`handleRagFileConfirm`） · `RA-06-LEGACY-01` | `🔶部分借` | **借**：字节进仓与业务 ingest 分离；pending 状态。**不借**：file 行当 identity、R2 key、presign 对公网、confirm 后自动入 clean 队列。**禁止**用 static initiate `:247-283`（`workflow_uuid: ''`、跳过工作流）当可借 ingest 正例——那条并入 `RA-06-LEGACY-03` |
| R2 key = `{team}/{purpose}/{file_uuid}.ext` | `files.ts:104-107`（`generateR2ObjectKey`） · `RA-06-LEGACY-02` | `⛔反例` | 不借路径/扩展名/file_uuid 当 CAS 身份（`T-O-42` / S13-T009）。`r2.ts:104-107` 只是 presign docstring，不是路径公式 |
| `static_upload` 跳过工作流，initiate 返回空 `workflow_uuid`，confirm 后 `ready` | `files.ts:198-283`（initiate，`:247-283` 曾被错锚成可借两步 ingest）+ `:19-22,322-325,354-361`（confirm→`ready`） · `RA-06-LEGACY-03` | `⛔反例` | 不借「上传即 ready / 无 admitted clean / 跳过工作流」。与 `T-O-385` 上传≠Item、`T-O-386` 仍须 clean 冲突 |
| confirm 只 `head` 对象存在，不核 digest | `files.ts:318-320,496-498`；`r2.ts:175-183` · `RA-06-LEGACY-04` | `⛔反例` | 不借存在性当完整性；本仓必须 SHA-256 |
| clean 假定 `source_file` 已在 R2 | `smind-skill-clean-universal/services/io_manager.ts:117-131`；`action_registry.ts:146` · `RA-06-LEGACY-05` | `🔶部分借` | 借「文件已进场再 clean」。不借 R2 binding/`r2_key` slot |
| constructor 假定上游 JSON 已在 R2 | `smind-skill-rag-constructor/services/io_manager.ts:125-148` · `RA-06-LEGACY-06` | `⛔反例`（对本面） | 证明遗产整链以 key 为运输；MKB 只传 handle。不回流 constructor |
| TUS：创建资源 vs PATCH 字节；块 checksum；未完成过期 | https://tus.io/protocols/resumable-upload.html Creation/Checksum/Expiration · 访问日 2026-08-29 · `RA-06-WEB-01` | `🔶部分借` | 借分步、块校验失败丢弃、过期回收 **机制**。不借 tus URL/头/SHA1 最低算法/公网协议当 MKB API |
| S3：全对象 checksum vs MPU composite ETag；必须 complete 或 abort | AWS S3 integrity + mpuoverview · 访问日 2026-08-29 · `RA-06-WEB-02` | `🔶部分借` | 借「分块校验 ≠ 对象身份哈希」；未完成分块必须回收。不借 bucket/key/ETag 身份 |
| OCI descriptor：digest 是 CAS；size 先核；mediaType 独立 | https://github.com/opencontainers/image-spec/blob/main/descriptor.md · `RA-06-WEB-03` | `🔶部分借` | 借 digest 身份 + size 防碰撞空间 + media 非键。**不借** OCI 镜像分发规范进 S13。`✅借` 留给 HEAD unique(digest,size)。§7 仍记录「digest+size 语义已在本仓」 |
| OWASP File Upload：鉴权、不信 Content-Type、随机名、体/尺寸限制、勿公开取回 | https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html · `RA-06-WEB-04` | `🔶部分借` | 借鉴权/尺寸/不信 MIME/不用文件名当身份。杀毒/扩展名白名单不自动成为本仓 DoD；CAS 已不用原名 |
| GCS generation-match；`0` = 仅当无 live | https://docs.cloud.google.com/storage/docs/request-preconditions · `RA-06-WEB-05` | `🔶部分借` | 借「条件写防重试误删/误盖」。本仓身份是 digest 不是 generation；CAS 覆盖本就被禁 |
| containerd lease：无引用即 GC；lease 保住「将要用」的 blob | https://github.com/containerd/containerd/blob/main/docs/garbage-collection.md · `RA-06-WEB-06` | `🔶部分借` | 借「未引用但合法的对象必须有 hold/lease」。不借 containerd 标签键与调度器 |
| `T-O-385` 上传=S13 handle，不创造 Item | `pre-initial-planning-qna.md:89,444-464` · `RA-06-BASELINE-01` | `✅借`（产品法） | 只 CITE。不把 QNA 当已实现 |
| S13 无公网 CRUD/presign | `S13-artifact-storage.md:77,430` S13-T031 · `RA-06-BASELINE-02` | `✅借` + 窄 reopen | 借「无浏览器对象面 / 无 presign」。reopen 只到受鉴权 handle |
| purpose 闭集 8；扩展须登记 | `S13-artifact-storage.md:274-286`；`models.py:17-27` · `RA-06-BASELINE-03` | `✅借` | 借闭集纪律。**不锁**新字符串（`T-P-NH-8`） |

> 无适用先例处已在 §8.2 标 `🆕`（公共 upload 事务、catalog/hold 与 ingest 分账、流式有界写与 1MiB HTTP 的缝）。不硬凑第五云厂商。

---

## 4. 缺口 / 断点台账 ★ `[核心]`

| 编号 | 缺口 / 断点 | 严重度 | 证据（`path:line`） | 影响 |
|------|-------------|--------|----------------------|------|
| `NH-RA06-B01` | 无受鉴权公共上传表面；object-upload route=0 | `S1 阻断` | `api/public/routes.py:56-452`；`README.md:211`；`D-14` | `T-O-381/385` 四通道真实文件无法由调用方喂入；pdf/doc 仍依赖内部 promote |
| `NH-RA06-B02` | 无 caller-upload/pending purpose；8 元闭集无「尚未 ingest 的合法所有者」 | `S1 阻断` | `models.py:17-27`；`001_initial.sql:859-862`；`D-15` | 即使接上 HTTP，ref CHECK 也无法表达 upload 成功；purpose 字面不锁但必须登记 |
| `NH-RA06-B03` | catalog-without-ref ≡ GC orphan；grace 内 upload→ingest 无 fence 契约 | `S1 阻断` | `object_gc.py:146-161,318-327`；`test_object_gc.py:41-63,274-277` | 24h 后 GC 可删仍待 ingest 的对象；或反过来永远不 catalog 则泄漏 |
| `NH-RA06-B04` | 未 catalog 的 promote 字节对 GC 不可见 | `S1 阻断` | `local_store.py:25-29,71-105` vs `object_gc.py:146-150` | 直接暴露 promote：Task/upload 失败留下永久磁盘孤儿 |
| `NH-RA06-B05` | 无流式写；HTTP 1MiB vs 对象 256MiB | `S1 阻断` | `ports.py:12`；`local_store.py:71-73`；`config.py:26,58` | 真实 PDF/docx 无法经公共 HTTP 进入 CAS；inline 扩二进制已被 Q5-C 否 |
| `NH-RA06-B06` | public object **read** 边界未裁（`G-NH-07`） | `S1 阻断`（产品法） | `routes.py:226-268` 仅元数据；`local_store.py:107-122` 无 catalog 闸 | 若误开 raw GET，持 handle 即可读；若 upload-only，调用方如何确认字节需另定义（stat vs 再 ingest） |
| `NH-RA06-B07` | handle 身份：HEAD digest vs S13 uuid vs `T-O-385` replay | `S2 重要` | `local_store.py:21,101`；S13-T002；QNA `:89` | 公共响应若提前冻错身份，tombstone 后再传会分裂 |
| `NH-RA06-B08` | 同 digest/size、不同 `media_type`：unique 不区分；promote 回传 caller media 但不更新 catalog | `S2 重要` | `014_*.sql:17-20`；`local_store.py:100-105`；`artifacts.py:27-35` | 声明 MIME 与 CAS 身份分账不清；嗅探（面 03）与上传声明可能分叉 |
| `NH-RA06-B09` | Port 无 `open_write_stream`；与 S13-T022 漂移 | `S2 重要` | `ports.py:10-24` vs S13-T022 | 256MiB 全内存 promote 在公共面不可接受 |
| `NH-RA06-B10` | `local_object` ingest 不要求 catalog/live-ref | `S2 重要` | `acquisition_ingest.py:443-455` | 任何能猜/持有 `mkbobj:v1:{team}:{digest}` 的进程可读字节（team 匹配即可） |
| `NH-RA06-B11` | 上传安全合同未写：filename、Content-Type、malware、未鉴权读 | `S2 重要` | `api/public/routes.py:56-452`（无 upload 处理器）；`local_store.py:38-39`（路径不含原名，正例）；OWASP CS = `RA-06-WEB-04` | 新表面必须 fail-closed；否则面 09 无法冻结 |
| `NH-RA06-B12` | tombstone 后可新 `stored_object_uuid`；并发第二 catalog 依赖 unique | `S2 重要` | `test_object_gc.py:285-303`；`001_initial.sql:1800-1801`→014 部分唯一 | 需 typed Conflict；与 `T-O-383` 上传幂等/冲突法对齐（面 09 消费） |

---

## 5. 跨功能系统一致性 ★ `[核心]`

- **5.1 整体形态一句话**：公共上传是 S13 的受鉴权入口，只产出不可变 handle+digest+size；S04 身份仍只由随后 `intake.ingest` + `local_object` 产生；GC 只回收「无 live ref 且过 grace」的对象——因此 upload 成功必须留下 **可被 ingest 看见、且在 grace 内不被当垃圾** 的 ref/hold，而不是把 Port.promote 挂到 HTTP。

- **5.2 功能间一致性契约（不变量 C1..Cn）**：

| 编号 | 不变量 | 跨哪些面/模块 | 违反后果 |
|------|--------|----------------|----------|
| `NH-C-50` | 上传成功 ≠ Item/Source/Revision；随后另一次 `intake.ingest` | `06` 拥有；`03/04/08` 消费 handle | OCR 失败留下 Item；lifecycle CRUD 污染（Q5-B 已否） |
| `NH-C-51` | 同一 team + 同一 sha256+size → replay 同一 handle（`T-O-385`/`T-O-383`） | `06`/`09` | 重复字节制造幽灵 catalog；指纹 replay 破裂 |
| `NH-C-52` | 对象存在 ≠ 业务成功；bytes-first：usable handle 仅在 catalog 策略满足后 | `06`/`S13`/`S04` | 磁盘文件被当成 acceptance |
| `NH-C-53` | CAS 身份 = team + digest（+size 入 catalog unique）；`media_type` 非身份 | `06`/`03` | MIME 分叉制造假冲突或覆盖 |
| `NH-C-54` | GC：grace>0；删前 fence recheck；见新 live ref 必须 restore；禁止 0 grace | `06`/`09` | 刚上传或刚 ingest 的字节被抢删 |
| `NH-C-55` | verify-on-read；team/handle 不匹配 fail-closed；digest mismatch 不得当成功 | `06`/`03`/`05` | 错 team 读；损坏字节进入 decode |
| `NH-C-56` | 零 CF/R2/presign/对象浏览器；遗产 key 不得进 wire（`T-O-42/377`） | `06` 全仓 | 绿地破坏 |
| `NH-C-57` | purpose 必须在闭集；新上传所有者须登记；字符串本态不锁 | `06`/`S13` | 无主对象或绕过 CHECK |
| `NH-C-58` | ingest 只消费 handle+digest+size；本面不创造 Intake 五类身份 | `06`→`03/04/08` | 上传面偷写 S04 |
| `NH-C-59` | 公共 raw object read 不是默认；若开放必须鉴权且不得用文件名/path；今日 generation-artifact 读是元数据不是字节 | `06`/`08`/`G-NH-07` | 未鉴权读、DoS、把 CAS 当 CDN |

- **5.3 数据 / 控制流贯穿图**：
```text
[caller, authenticated]
        |  NH 净新：upload contract（路径不冻）
        |  有界 stream → SHA-256 → size cap
        v
 LocalObjectStore.promote / CAS path     -- HEAD 已有
        |  仍非 usable
        v
 S12 UoW: upsert mkb_stored_objects
          + live ref (purpose 闭集内，字面 OPEN)
        |  提交后才是 T-O-385 handle
        v
 handle + digest + size  -->  caller
        |
        |  无 ingest：grace 后 GC 候选（须能与「仍待 ingest」区分 → hold/ref）
        v
 Task create request_intent=intake.ingest
 source_kind=local_object + logical_handle     -- 面 03/08
        v
 acquire: read_verified(team, handle)           -- 面 03
        v
 acceptance 才写 Source/Item/Revision           -- 面 04/08
        v
 另增 intake_* purpose 的 live ref；upload hold 可 release

GC: catalogued ∧ no live ref ∧ age>=grace
    → TX1 fence → quarantine → TX2 proof/tombstone or restore
```

- **5.4 与邻面消费 / 提供**（index §1.2）：
  - **提供给 03**：handle 可 `read_verified`；声明 media 与 sniff 分账（`NH-C-53`）。
  - **提供给 08**：upload 不创建 Item；ingest Task 才进入 lifecycle。
  - **提供给 09**：upload 幂等/冲突、GC TOCTOU、tombstone 后再传。
  - **不提供**：HTTP 路径、purpose 字面、是否 raw GET（`G-NH-07`）。

---

## 6. 净新契约 / 架构边界草案 `[核心]`

> 草案，非冻结。不写 HTTP 路径、不写 purpose 字符串、不选 multipart 引擎。

- **6.1 净新聚合 / 解耦点**：
  - `NH-N-06-01` **AuthenticatedUploadSession**：与 Task 解耦的「字节进仓」聚合。成功输出 `ObjectStat`（handle+sha256+size[+可选 media]），**零** Intake 身份。
  - `NH-N-06-02` **UploadHold / pending live-ref**：把「已成功上传、尚未 ingest」从 orphan 类中分出。可用已有 `operator_hold` **或** 新登记 purpose（字面 OPEN）。
  - `NH-N-06-03` **BoundedWrite**：相对今日 `promote(bytes)` 的流式有界写（对齐 S13-T012，不冻 chunk 库）。
  - `NH-N-06-04` **UploadAdmission ≠ TaskCreate**：打破 `task_create.py:70-72`「只为 new Task promote」的唯一入口，但不删除 Task 路径上的 inline staging。

- **6.2 净新契约叙述规格**：

| 项 | 草案（非冻） |
|----|----------------|
| 输入 | 鉴权后的 team；有界字节流；可选 `expected_sha256`；可选声明 media；**不要** caller filename 当身份 |
| 输出 | handle + sha256 + size；幂等 replay 同一 handle；冲突 typed（`T-O-383`） |
| 成功 | bytes 在 CAS 且（待裁）catalog+live ref/hold 已提交。**不是** Item |
| 失败 | 超 cap → budget；digest 不符 → integrity；team 不符 → auth；半写 → 仅 staging/orphan |
| 随后 | 另一次 `intake.ingest` + `local_object.logical_handle` |
| 无随后 | grace 后可 GC；若仍在 hold 内则不可 GC |
| 读 | 见 `G-NH-07`：upload-only / upload+authenticated read / 仅业务 artifact read |

- **6.3 架构边界（与既有 / 相邻面）**：
  - 内：只通过 `ObjectStorePort` + S12 UoW；禁止 pathlib 进 public contracts。
  - 外：禁止 presign、R2、对象浏览器、未鉴权 GET。
  - 与 inline：inline 仍可走 Task 前 promote（已有）；大文件不得靠抬 `MKB_MAX_REQUEST_BYTES` 冒充上传面。
  - 与面 03：acquire 继续 `read_verified`；是否强制 catalog 存在由设计补钉，本面只标 `NH-RA06-B10`。

---

## 7. Substrate-fit / 技术路线过滤 ★ `[核心]`

本仓过滤：单体 Python 3.12 FastAPI、local Turso、S03 七表无环、eq-only 守卫、S13 bytes-first、`T-O-42` 绿地、禁止 CF/R2/SMCP/动态 plugin/自由表达式。

| 借鉴点 | 原机制（参考处） | 是否冲突本仓路线 / 约束 | 落地形态（降级 / 重映射 / 直采） |
|--------|------------------|--------------------------|-----------------------------------|
| HEAD CAS/verify/GC fence | `local_store.py` / `object_gc.py` | 不冲突 | **直采**内核；只加 upload 缝 |
| HEAD `promote(bytes)` HTTP 化 | `ports.py:12` | 冲突：1MiB 体帽、全内存、无 catalog | **重 substrate**：有界流 + 同 UoW catalog/hold；禁止「把 Port 挂路由」 |
| legacy init/confirm | `files.ts` pending_upload | 部分：两步可映射；R2/presign/file_uuid 冲突 `T-O-42` | **降级**为「promote 事务」+「ingest Task」两步；不借 presign |
| legacy static_upload | `files.ts:322` ready 无 workflow | 冲突 `T-O-385/386` | **反例**；禁止跳过 ingest/clean |
| TUS | tus.io 1.0.0 | 协议栈/URL/SHA1 非本仓 API | **降级**为机制：未完成过期、块校验失败丢弃、创建与传字节分离 |
| S3 MPU / ETag | AWS 官方 | 云键、composite checksum、计费模型 | **降级**：对象身份必须是 **全对象 SHA-256**，不得用 part-ETag；未完成写必须回收 |
| OCI descriptor | image-spec descriptor.md | 规范不是 S13；语义可映射 | **重映射**：digest+size 已在 HEAD unique；**不**引入 OCI 栈。verdict=`🔶部分借` |
| GCS generation | request-preconditions | generation 是名字寻址 | **重映射**到 digest unique + typed conflict；不引入 generation 列 |
| containerd lease | garbage-collection.md | 标签/gRPC 冲突 | **重映射**到 `mkb_object_references` live ref / hold |
| OWASP 扩展名白名单 | File Upload CS | 本仓不执行上传文件；解析在面 03/05 | **降级**：鉴权、尺寸、不信 MIME、原名不进 path；扩展名/杀毒不在本面冻结 |
| 公网 presign PUT | legacy `r2.ts` | 硬冲突 `T-O-42`、S13-T031 | **禁止** |

---

## 8. 反例坑表 + 净新表 `[核心]`

### 8.1 反例坑表 ⛔

| 反例 | 来源锚 | 为什么不可借 |
|------|--------|--------------|
| 直接把 `ObjectStorePort.promote` 暴露为公共 HTTP | `ports.py:12`；`task_create.py:70-72` | 不写 catalog/ref、忽略 purpose、整段内存、无独立幂等表面 |
| 上传即创建 IntakeItem | QNA Q5-B；`T-O-385` | 失败 OCR 留下业务身份 |
| 无独立上传、把大文件塞进 Task JSON | QNA Q5-C；`config.py:26` | 1MiB 帽；无法复用 handle 做 rebuild |
| R2 key / `{file_uuid}.ext` / 文件名当身份 | `files.ts:104-107`；OWASP Filename Safety | 与 CAS 相反；path traversal / 覆盖 |
| 信任 `Content-Type` / 原文件名 | OWASP CS Content-Type / Filename | 可伪造；本仓应以 digest 为身份、media 为声明 |
| 未鉴权读 / 把上传对象放进 webroot | OWASP Public File Retrieval；S13-T031 | DoS、非法内容托管、绕过 Team |
| confirm 只 HEAD 存在性 | `files.ts:496-498` | 无 SHA-256；半写/错对象会被当成功 |
| `static_upload` 跳过 workflow | `files.ts:19-22,322` | 无 admitted clean；与四通道 completeness 冲突 |
| MPU ETag 当全对象 digest | AWS integrity note | ETag 是 part-MD5 的 MD5；与 `T-O-385` sha256 不符 |
| GC 无 grace / 无 recheck | S13-T026；containerd 无 lease 即删 | 合法 in-flight 上传被删 |
| 跨 team 复用同一 CAS 文件 | `local_store.py:38-39`；S13-T010 | 已禁；保持 |
| presign 对公网 / Cloudflare R2 | `r2.ts:110-163`；`T-O-42` | 绿地硬禁 |
| 用文件名/uploader 路径当权威 | legacy `generateStaticFileR2Key` | 本仓权威是 catalog+digest |
| monkeypatch promote 冒充公共上传 e2e | `test_source_capability_paths.py:77-82` | 内部装载 ≠ `T-O-376` 公共上传到位 |

### 8.2 净新表 🆕

| 项 | 为什么无先例 | 草案落点 |
|----|--------------|----------|
| 受鉴权公共上传只返回 S13 handle、同事务留下非 orphan 的合法未 ingest 态 | HEAD 无表面；legacy 用 file 行+R2；云厂商用 bucket key | §6 `NH-N-06-01/02` |
| 在 1MiB HTTP 帽与 256MiB CAS 之间的有界流，且身份是全对象 SHA-256 | HEAD `promote(bytes)`；TUS/S3 是外栈 | §6 `NH-N-06-03`；形状不冻 |
| upload 与 Task create 解耦的 admission | 今日 promote 只服务 new Task | §6 `NH-N-06-04` |
| `G-NH-07` 三选一的产品读面 | QNA 未冻 raw read | §10.2 |

---

## 9. 验收格栅草案（防假绿）`[核心]`

> 落地验收归下游。此处封堵 fake-green。禁止：内部 `storage.promote` 冒充公共上传；空 body 当成功；Task succeeded 当「文件已进 CAS」；503 当通道 DoD。

| 功能 F | 收口目标（一句话可验证） | Test-ID（拟） | 测试层 | 防假绿要点 |
|--------|--------------------------|----------------|--------|------------|
| 受鉴权上传创造 handle | 鉴权调用上传真实字节，响应含 handle+sha256+size；DB 无 Source/Item/Revision 新行 | `NH-A-06-01` | 集成 | 禁止只 assert 函数返回；必须查三表零 Intake 行 |
| 幂等 replay | 同 team 同 sha256+size 两次上传 → 同一 handle，不新增 live catalog 行 | `NH-A-06-02` | 集成 | 第二次不得 insert 第二 live unique；冲突 typed |
| 上传≠ingest | 仅上传后 retrieval/search 不得命中该文件 | `NH-A-06-03` | default-root e2e | 禁止用 Task succeeded 代替 |
| 随后 local_object ingest | 用返回 handle 建 `intake.ingest`，acquire 读到相同 digest | `NH-A-06-04` | default-root e2e | 禁止测试里 `container.storage.promote` |
| catalog/hold 存在 | 上传成功后存在 catalog 行 **且** 有 live ref 或显式 hold，使 GC 在 grace 内 `collect_candidates` 不选中 | `NH-A-06-05` | 集成 | 禁止只 promote 不查 ref |
| GC 不抢删 in-flight | 上传后立即跑 scanner（age<grace）→ 0 deleted；过 grace 仍 hold → `HOLD`/`LIVE_REFERENCE` | `NH-A-06-06` | 集成 | 复用 `test_ns6_gc_toctou` 模式，对象改为「上传会话」 |
| 无 ingest 过 grace | 释放 hold 且 age≥grace → quarantine+proof+tombstone；`read_verified` 404 | `NH-A-06-07` | 集成 | 不得硬 `unlink` 绕过 quarantine |
| digest mismatch | 提供错误 expected digest → integrity 失败，CAS 不留下错误终态 | `NH-A-06-08` | 单元 | |
| team mismatch | 他队 handle 读/传 → 403，不回字节 | `NH-A-06-09` | 单元/集成 | |
| 超对象帽 | >`object_max_bytes` → budget 413，无 catalog | `NH-A-06-10` | 单元 | 不得靠抬 HTTP 帽绕过对象帽 |
| 超 HTTP 帽但未开流 | 在流式合同落地前，>1MiB 请求不得被说成「上传已支持」 | `NH-A-06-11` | 集成 | 防把 413 写成通道完成 |
| 并发双传 | 并行同字节 → 一方 replay 或 typed conflict，无不同内容覆盖 | `NH-A-06-12` | 集成 | 对齐 S13-A02 |
| 跨 team 同 digest | 不复用 path/row | `NH-A-06-13` | 单元 | S13-A03 |
| 无公开未鉴权 GET | 无 token 不得读对象字节；generation-artifact 路由仍须 token | `NH-A-06-14` | 集成 | OWASP 未鉴权读 |
| 不信 MIME/filename | 声明 media 与嗅探分账；原名不出现在 object_root 路径 | `NH-A-06-15` | 单元 | 路径扫描 `..`、原名 |
| 公共表面分母 | `@router` 计数含 upload 后必须更新 index `D-14`；本文件不写路径字符串 | `NH-A-06-16` | 单元 | 防静默加路由 |
| 面 09 消费 | upload 路径纳入 fail-loud/replay 矩阵，不得用 monkeypatch storage | `NH-A-06-17` | retrieval-facet mega（后） | 本面只草案；面 09 汇总 |

---

## 10. 优先级建造建议 + owner-gate 候选 `[核心]`

- **10.1 建造顺序（依赖序，分批不一次性深做）**：

| 顺序 | 工作簇 | 依赖 | 复用判定 |
|------|--------|------|----------|
| `P0-a` | 钉 upload 成功的 catalog+ref/hold 语义（仍无 HTTP） | `NH-C-52/54/57`；`G-NH-07` 不阻塞内核 | `♻️重 substrate`（在 promote+GC 上加 hold） |
| `P0-b` | 有界写（stream/chunk）与全对象 SHA-256、size cap | `NH-RA06-B05/B09` | `♻️重 substrate` / 部分 `🆕` |
| `P0-c` | 受鉴权公共上传表面（路径不冻）只返回 handle+digest+size | `P0-a/b`；`T-O-385` | `🆕净新` |
| `P1-a` | 证明 upload 不写 Item；随后 `local_object` ingest e2e（真文件，非内部 promote） | 面 03/08 衔接 | `✅复用` ingest；`🆕` 公共入口 |
| `P1-b` | GC：in-flight hold vs 真 orphan；tombstone 后再传 replay | `test_object_gc` / toctou | `✅复用` fence；扩用例 |
| `P2` | 按 `G-NH-07` 裁决补或不补 authenticated raw read | owner-gate | 待裁 |
| 不做 | 暴露 promote、presign、R2、上传即 Item、扩 inline 二进制当上传 | — | `⛔` |

- **10.2 owner-gate 候选（只 MARK 不裁决 → 上交 index §4 / 下游决策登记）**：

| gate-ID | 决策点 | 候选选项（不预设倾向） | 影响 |
|---------|--------|------------------------|------|
| `G-NH-07` | public object surface | `upload-only` / `upload+authenticated read` / `仅业务 artifact read` | 安全边界、GC、是否允许持 handle 拉字节；QNA 未冻 raw read |
| `G-NH-16` | 上传成功是否必须写 catalog+live ref/hold | `catalog+pending/hold ref（合法非 orphan）` / `只 promote 字节、靠 grace 赌 ingest` / `catalog 无 ref（今日 GC 候选类）` | 直接决定 `NH-RA06-B03/B04`；三选项并列，**无推荐赢家** |

> purpose 字面继续 OPEN（`T-P-NH-8`）。不把外部 TUS/S3 偏好冻进本仓。`G-NH-16` 只 MARK、无推荐赢家；index §4 v0.2 已登记本 gate（仍不裁决）。`G-NH-11` 留给面 02 seal 事务。

---

## 11. 核验记录 `[核心]`

| 锚点（host-ID） | 是否核验 | 方式（grep/read/run） | 备注 / 修正 |
|------------------|----------|------------------------|--------------|
| HEAD `1221aa1` | `✅` | `git rev-parse HEAD` | `1221aa1ba3bcc8d5be38f7d2529a052dcf93b256` 与 index §2.2 一致 |
| `D-14` 28/0 | `✅` | `rg` + python 数 `@router.(get\|post\|patch\|delete\|put)` | 28；object/upload/multipart 路径 0。`dict[str, object]` 命中是类型注解不是路由 |
| `D-15` 8/0 | `✅` | read `models.py:17-27` | 8 Literal；无 caller-upload。DDL CHECK 同步 |
| `local_store.py` promote/read | `✅` | read `:17-193` | 行号相对 PROMPT「71-123」未漂；quarantine 在 139+ |
| `object_gc.py` | `✅` | read 全文 | 实际在 `src/services/object_gc.py`（非 `src/runtime/storage/`）；runtime 仅 scanner |
| DDL unique | `✅` | read `001_initial.sql:837-873,1800-1801`；`014:17-20` | **修正**：live unique 已迁到 014 部分索引，不能只引 001 的全表 unique |
| `task_create.py:70-72` | `✅` | read `:67-105,379-428` | 注释仍在；promote 由 `config_snapshots.prepare` 触发 |
| public generation-artifact | `✅` | read `routes.py:226-294`；`generation.py:28-62` | 元数据读正例，非字节 |
| `local_object` acquire | `✅` | read `acquisition_ingest.py:413-455` | 不查 catalog |
| Settings caps | `✅` | read `config.py:26,58,69-72`；`app.py:212,348-351` | grace 项名 `object_gc_grace_seconds` |
| GC 单测 | `✅` | `uv run pytest tests/unit/test_object_gc.py tests/unit/test_ns6_gc_toctou.py -q` | 2026-08-29：**10 passed**。index 所列 intake pytest 未跑（非本面分母） |
| QNA `T-O-385` | `✅` | read `:89,415-464,768,802,813` | 只 CITE |
| S13 domain-truth | `✅` | read 完成定义、T002/T022/T026/T031、E05/E07 | 无公网 API 被窄 reopen |
| glossary handle | `✅` | grep `mkbobj` | uuid 形态 vs HEAD digest |
| legacy files.ts / r2.ts | `✅` | read `handleRagFileInitiate:370-460`、`handleRagFileConfirm:463-568`、`handleStaticFileInitiate:198-283`、`generateR2ObjectKey:104-107` | **修正**：LEGACY-01 不得锚 static initiate；`r2.ts:104-107` 是 presign docstring |
| legacy clean `source_file` | `✅` | grep+read `io_manager.ts:117-131`；`action_registry.ts:146` | 假定 R2 已在 |
| constructor `io_manager` | `✅` | read `:125-148` | 假定 `r2_key` |
| WEB TUS | `✅` | `web_search` + `web_fetch` tus.io protocol | 2016-03-25 v1.0.0；Checksum 扩展；Expiration |
| WEB S3 | `✅` | `web_fetch` integrity + mpuoverview | MPU ETag 非全对象哈希；必须 complete/abort |
| WEB OCI descriptor | `✅` | `web_fetch` descriptor.md | digest 身份；size+mediaType 描述子 |
| WEB OWASP | `✅` | `web_fetch` File Upload CS | 不信 Content-Type；原名危险；未鉴权读 |
| WEB GCS preconditions | `✅` | `web_fetch` request-preconditions | 2026-08-26；XML MPU 无 precondition |
| WEB containerd GC | `✅` | `web_fetch` garbage-collection.md | lease 保住未引用 blob |
| 「暴露 promote 即可」叙事 | `✅` | 对照 HEAD catalog/GC | **修正**：证伪。index §2.4 失真校正成立 |

未核：live 供应商、真实公网上传流量、malware 扫描产品（本面 OOS）。index 共享 pytest 包（`test_intake_*`）未作为本面分母复跑。

---

## 12. 收尾 Verdict 与交接 `[核心]`

- **本面裁定**：S13 **内核可复用**，公共上传 **产品缝净新**。`D-14=28/0`、`D-15=8/0` 仍是阻断水位。必须先回答 catalog/hold 与 `G-NH-07`，再谈 HTTP 形状。禁止把内部 `promote`、legacy presign 或 MPU ETag 写成方案赢家。
- **交接下游**：缺口台账（§4）→ 规划；净新契约（§6）→ 设计；owner-gate `G-NH-07`/`G-NH-16`（§10.2）→ `pre-charter-qna.md`；验收格栅（§9）→ 执行计划与面 09。
- **冻结前置**：review-fleet 交叉；`G-NH-07`/`G-NH-16` 仍只 MARK；任何把 analysis 标 `frozen` 的行为禁止在本轮发生。HEAD 若改 `D-14/D-15` 须先修订 index。

必须回答（面 PROMPT）的短答：

1. **产品面是 upload-only、upload+authenticated read、还是仅业务 artifact read？** — `G-NH-07` 三选项并列，不裁决。HEAD 接近「无 upload + 仅业务 artifact **元数据**读」。`T-O-385` 强制要有 upload，未强制 raw GET。
2. **catalog orphan 在何事务创建？upload 成功是否必须写 catalog？** — 今日 catalog 在 **业务 UoW**（Task/outcome/acceptance）与第一条 live ref **一起**写；orphan 测试行是无 ref catalog。upload 成功是否必须写 catalog 是 `G-NH-16`，不裁决；但「只 promote」已被 GC 可见性反例否定为可默认。
3. **grace 内 upload→ingest 与 GC 如何防竞态？** — 现成机制：grace>0 + TX1/TX2 + quarantine restore。缺的是 **合法未 ingest 的 live ref/hold**。无此则与 orphan 同级。
4. **同 digest/size/media 差异如何返回？CAS 身份？** — 身份是 **team + sha256**（handle）与 catalog unique **(team, sha256, size)**。media **不是**身份；差异不得制造第二 live 行。返回值应 replay 同一 handle；声明 media 如何与 catalog 已存 media 对账属执行（不冻）。
5. **为什么「直接暴露 promote」不能自动解决 catalog/GC/竞态？** — promote 不写 catalog、忽略 purpose、GC 要么看不见（泄漏）要么把无 ref catalog 当垃圾、无流式、绑定 Task 创建、`read_verified` 无 ref 闸。这些是独立缝，不是 HTTP 包装。

---

## 附录 A · 修订历史

| 版本 | 日期 | 作者 | 主要变更 |
|------|------|------|----------|
| v0.1 | 2026-08-29 | Grok analysis-fleet / review-fleet | 初稿（measure-first + 三渠道正反例 + 缺口台账）；状态 `draft` |
| v0.2 | 2026-08-29 | Grok fix-fleet | 吸收已核实 review：R2-I01 拆开 RAG/static 两步 ingest 嵌合体；R2-I07 删 r2.ts 张冠李戴行号；R3-I09 WEB-03 降为 `🔶部分借`；R4-I01 `G-NH-11` 重编号 `G-NH-16`。状态仍 `draft` |

## 附录 B · 渠道事实核查登记

| ID | 渠道 | 原子句 |
|----|------|--------|
| `RA-06-HEAD-01` | HEAD | 正例：handle `mkbobj:v1:{team}:{sha256}`，CAS 按 team/digest 分目录 |
| `RA-06-HEAD-02` | HEAD | 正例：`read_verified` 再哈希，失败 `OBJECT_INTEGRITY_DIGEST` |
| `RA-06-HEAD-03` | HEAD | 正例：live unique `(team, content_digest, size_bytes)` |
| `RA-06-HEAD-04` | HEAD | 正例：GC quarantine + TX2 restore |
| `RA-06-HEAD-05` | HEAD | 正例：`expected_sha256` 不匹配 422 |
| `RA-06-HEAD-06` | HEAD | 正例：team mismatch 403 |
| `RA-06-HEAD-07` | HEAD | 正例：bytes-first，TX 失败只留 orphan |
| `RA-06-HEAD-08` | HEAD | 正例：generation-artifact 鉴权元数据读 |
| `RA-06-HEAD-09` | HEAD | 正例：`local_object` 以 handle 取字节 |
| `RA-06-HEAD-10` | HEAD | 正例：grace=0 拒绝；默认 24h |
| `RA-06-HEAD-11` | HEAD | 反例：public upload route=0 |
| `RA-06-HEAD-12` | HEAD | 反例：caller-upload purpose=0 |
| `RA-06-HEAD-13` | HEAD | 反例：promote 为内部 Port 且忽略 purpose |
| `RA-06-HEAD-14` | HEAD | 反例：无 multipart/UploadFile |
| `RA-06-HEAD-15` | HEAD | 反例：GC 只扫已 catalog 行 |
| `RA-06-HEAD-16` | HEAD | 反例：无 ref catalog ≡ orphan |
| `RA-06-HEAD-17` | HEAD | 反例：`read_verified` 不查 catalog/ref |
| `RA-06-HEAD-18` | HEAD | 反例：1MiB HTTP vs 256MiB 对象；全内存 promote |
| `RA-06-HEAD-19` | HEAD | 反例：handle 含 digest，与 S13-T002 uuid 冲突 |
| `RA-06-HEAD-20` | HEAD | 反例：promotion 绑定 new Task，非独立 upload |
| `RA-06-LEGACY-01` | LEGACY | 部分借：RAG `handleRagFileInitiate/Confirm` pending 分离；不借 static `:247-283` |
| `RA-06-LEGACY-02` | LEGACY | 反例：R2 key 身份 |
| `RA-06-LEGACY-03` | LEGACY | 反例：static_upload 跳过 workflow |
| `RA-06-LEGACY-04` | LEGACY | 反例：HEAD 存在性当确认 |
| `RA-06-LEGACY-05` | LEGACY | 部分借：clean 假定文件已进场（R2 slot） |
| `RA-06-LEGACY-06` | LEGACY | 反例：constructor 以 `r2_key` 为运输 |
| `RA-06-WEB-01` | WEB | 部分借：TUS 分步/checksum/expiration |
| `RA-06-WEB-02` | WEB | 部分借：S3 全对象 checksum vs MPU ETag；abort 未完成 |
| `RA-06-WEB-03` | WEB | `🔶部分借`：OCI digest+size 语义映射 HEAD unique；不借 OCI 栈 |
| `RA-06-WEB-04` | WEB | 部分借：OWASP 鉴权/不信 MIME/原名/公开读风险 |
| `RA-06-WEB-05` | WEB | 部分借：GCS precondition；限制：MPU 无 precondition |
| `RA-06-WEB-06` | WEB | 部分借：containerd lease 保住未引用 blob |
| `RA-06-BASELINE-01` | BASELINE | `T-O-385` 上传=handle≠Item |
| `RA-06-BASELINE-02` | BASELINE | S13 无公网 CRUD；窄 reopen |
| `RA-06-BASELINE-03` | BASELINE | purpose 闭集扩展须登记 |

每条 `RA-*` 的置信：HEAD 实测 > 仓内文档 > 外部。substrate-fit 见 §3/§7。命中缺口见 §4。
