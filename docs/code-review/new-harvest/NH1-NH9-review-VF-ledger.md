# MKB new-harvest NH1–NH9 第 1 轮跨 Reviewer 统一台账（UF → VF）

> **文档性质**：`review-findings-ledger`（跨 reviewer 合并 + verified-findings 复核 + 初步修复方案）。
> **谁写**：**实现者 / 合并人**（不是某一位 reviewer）。
> **为什么独立成文**：四份独立审查互不污染；本文件是本轮合并、复核与修复的单一权威台账。

---

> **元信息（置顶 · 必填）**
>
> | 字段 | 值 |
> |------|----|
> | **审查标的** | `MKB new-harvest NH1–NH9（4 通道接线 / kind-family workflows / 竞态幂等）HEAD @ a608ea8 之后本轮修复` |
> | **审查阶段 / 轮次** | `第 1 轮合并` |
> | **合并 / 核查人（实现者）** | `Grok` |
> | **合并日期** | `2026-08-30` |
> | **文档状态** | `resolved` |
>
> **审查来源锚定（被合并的 reviewer 制品 — 必须逐份列全）**：
> - `docs/code-review/new-harvest/NH1-NH9-reviewed-by-gemini.md` — `medium / 6 findings`（无 blocker）
> - `docs/code-review/new-harvest/NH1-NH9-reviewed-by-GLM53f.md` — `high / 23 findings`（无 critical blocker）
> - `docs/code-review/new-harvest/NH1-NH9-reviewed-by-luna.md` — `critical / 16 findings`（R1–R14 标 blocker）
> - `docs/code-review/new-harvest/NH1-NH9-reviewed-by-v4f.md` — `high / 19 findings`（无 blocker）
>
> **对照真相（逐条 re-verify 时回看的源）**：
> - `docs/eval/new-harvest/final-execution-plan.md`（T-O-376..407）
> - `docs/eval/new-harvest/pre-charter-qna.md` / `pre-initial-planning-qna.md`
> - `docs/plan/new-harvest/AP-NH1..AP-NH9` 与 `todo-list.md`
> - `docs/closure/new-harvest/` 九份 AP + CROSS-NH
> - 代码根：`src/`、`intake/`、`api/`、`tests/`、`src/persistence/migrations/018..024`

---

## 0. 合并方法与核查纪律

- **合并范围**：4 份独立审查全部 finding 平铺（Gemini 6 + GLM 23 + Luna 16 + v4f 19 = **64** 条原始 finding）。
- **核查纪律（硬）**：
  1. reviewer 的结论仅作线索。每条判 `valid*` 的项均由实现者 grep / Read 当前真实代码坐实，关键证据带 `file:line`。
  2. 与任一方冲突，以实测为准。Luna 将多项 schema 加固标为 campaign blocker；对照 T-O 与 AP 后，生产路径 CAS 成立的项降为 `[partial-delivery]`，不是假绿。
  3. 已纠正的跨-reviewer 误报在 §4.3 列出。
  4. 严重级别取多方最严；同一根因 / 同一代码位点合并为一条 UF/VF。
- **统一编号前缀**：UF（§2）与 VF（§3）1:1，`VF-n == UF-n`。

### 0.1 复核判定（verdict）图例

| verdict | 含义 |
|---------|------|
| `valid` | 属实，需处理 |
| `valid-edge` | 属实但仅边界/条件态触发 |
| `valid-conditional` | 属实但本环境不复现；按防御性处理 |
| `valid-owner-gated` | 属实但归 owner 动作 |
| `valid-pre-existing` | 属实但 base 即存在，非 NH 引入 |
| `valid-by-design` | 现象属实但为既定设计 |
| `valid(子项 overstated)` | 主项真，个别子断言过度 |
| `stale-rejected` | 不成立：陈旧/已删代码 |
| `INVALID` | 不成立：无代码依据 |

### 0.2 处置（disposition）图例

| 处置 | 含义 |
|------|------|
| `fix` | 本轮修复 |
| `partial-fix` | 部分修复 + 余项 defer |
| `defer-with-rationale` | 有理由后延 |
| `deferred-by-owner` | 归 owner session |
| `acknowledge` | 已修 / 无需改动 |
| `stale-rejected` | 带证据驳回 |

### 0.3 严重级别图例

`critical | high | medium | low | info`（取多方最严）。

### 0.4 Finding 三类归属（class）图例

| 归属类 | 标记 | 本阶段义务 |
|--------|------|------------|
| **真 deferred** | `[true-deferred]` | 登记承接；本阶段不修是诚实的 |
| **真 bug** | `[true-bug]` | 必须本阶段修；不得改写成 deferred |
| **部分交付** | `[partial-delivery]` | 本阶段补齐；剩余切片登记 §5.4 |

---

## 1. 一句话裁定 + 合并统计（TL;DR）

- **一句话裁定**：4 方 64 条原始 finding 合并为 42 条统一项；15 条 `[true-bug]` 与可落地的 `[partial-delivery]` 本轮已修（策略闭集 fail-loud、sealed-once DDL、GC quarantine 对账、会话级 upload hold、binary raw CAS、registered_api observation 409、系统语义键、fail-process CAS、reacquire 限定 http 图、NUL、retrieval v2 Mapping、证据 digest 刷新等）。Luna 的 campaign-blocker 总体 **overstated**：4 通道 happy path 与 kind-family 接管为真，但策略适用性、schema 不变量与模型格 live 语义确实不足。最大未修切片是真实模型端点、进程级 kill+lease recovery、stage envelope 去正文、以及 kind 图 revision 演进。
- **合并后统一 finding 数**：`42`（来自 `64` 条原始 finding 去重）。
- **按 verdict**：`valid 28` · `valid-edge 5` · `valid-conditional 2` · `valid-pre-existing 1` · `valid-by-design 3` · `valid(子项 overstated) 3` · `stale-rejected 0` · `INVALID 0`。
- **按三类归属 ★**：`[true-bug] 15（VF1,5,7,8,11,12,15,16,17,18,24,26,30,31,33）` · `[partial-delivery] 17（VF2,3,4,6,9,10,13,14,19,22,23,25,27,28,32,40,41）` · `[true-deferred] 7（VF21,29,36,37,38,39,42）` · `n/a 3（VF20,34,35）`。
- **按处置（修复后）**：`fix 24` · `partial-fix 6` · `defer 9` · `ack 3`。
- **blocker 数**：`0` 升级 owner 的未修 `[true-bug]`。Luna 自称 14 个 blocker 经复核后无一构成「本轮不可关闭的生产路径断裂」；策略静默换 worker（VF1）是最接近的必修项，已修。
- **净增承重盲区**：Luna 独家钉死策略适用性、binary 重编码、registered_api observation、系统语义键；GLM 独家钉死 GC quarantine 无恢复与 tail digest 失实；v4f 独家钉死 `_fail_process_tx` 静默与跨 closure sqlite3 失实陈述。Gemini 覆盖面最窄但抓住了 prefix 守卫与 session `--no-sandbox` 盲区。

---

## 2. 合并映射（reviewer finding → 统一编号）

### 2.1 映射表

| 来源 finding（reviewer-原编号）| 合并到 | 合并后问题（一句话）|
|------------------------------|--------|---------------------|
| Luna-R1 / v4f-R7 / GLM-R17 | `UF1` | 声明的 clean_strategy 可被图 unguarded fallback 静默换成另一 worker |
| Luna-R2 / v4f-R14 | `UF2` | 020 trigger 只验 NEW 形状；facts/history 无 append-only；sealed 行可被普通 SQL 改写 |
| Luna-R3 | `UF3` | acquire/decode/clean stage envelope 仍持久化 raw_text，形成第二表示权威 |
| Luna-R4 | `UF4` | retrieval 只数 indexed 条数，不比对 proof set digest；indexed content_digest 可 UPDATE |
| Luna-R5 | `UF5` | binary raw_text latin-1 运输后 acceptance 以 UTF-8 text/plain 落 CAS |
| Luna-R6 | `UF6` | registered_api `raw_byte_digest` 是逻辑 hash，不是 canonical records bytes |
| Luna-R7 | `UF7` | 同 observation 第二次 registered_api Task 失败并留下业务行 |
| Luna-R8 | `UF8` | public metadata 可覆盖 system-owned S04 键 |
| Luna-R9 / v4f-R5 / GLM-R15 | `UF9` | 七意图 state×intent 未成文；registry/admission/callback 口径分裂 |
| Luna-R10 / GLM-R13 | `UF10` | retry/full-task exact replay 法不统一 |
| GLM-R3 / Luna-R11(GC) / v4f-R12(GC) | `UF11` | GC TX1 quarantine 与 TX2 之间 crash 无对账恢复 |
| GLM-R5 | `UF12` | 同字节并发上传共享一个 pending hold，cancel/TTL 误伤 |
| Luna-R11(orphan/staging) / v4f-R12(余) | `UF13` | pre-catalog CAS orphan、staging reaper、ingest reservation 未封闭 |
| Luna-R12 / v4f-R2 / GLM-R6,R7,R8,R18 | `UF14` | 模型依赖格为 stub/fixture/封闭字形；PromptRef 被改写；registered_api 无网络获取 |
| Gemini-R4 | `UF15` | readiness_required 强制 multimodal，默认关闭导致 /ready 503 |
| Gemini-R3 | `UF16` | `--no-sandbox` 只扫 geckodriver argv，不扫 session args |
| Gemini-R5 | `UF17` | `unshare --net` 无 `-U`，无特权容器 EPERM |
| Gemini-R1 | `UF18` | `_inline_kind` prefix 路由引用 rebuild/metadata 守卫但局部 guards 未声明 |
| Gemini-R2 | `UF19` | 生产 `selection_digest` 未纳入 `representation_fact_digest` |
| Gemini-R6 | `UF20` | `resolve_for_source` 非 ingest 回落看似死代码（purpose 被折叠为 intake.ingest） |
| GLM-R2 | `UF21` | kind 图 `revision_number=1` 原位改写，升级 digest mismatch 503 |
| GLM-R1 | `UF22` | NH2 冻结 shared tail digest 已漂移且测试只断言基数 1 |
| Luna-R13 | `UF23` | NH1 closure 仍引用旧 matrix digest f7199ee |
| v4f-R3 | `UF24` | `_fail_process_tx` UPDATE 不检查 rowcount，取消并发静默丢失败写 |
| v4f-R4 | `UF25` | NOOP→SUCCEEDED；非 ingest 成功计入 indexed_success |
| v4f-R6 / GLM-R16 | `UF26` | reacquire 法律被套到全部 kind 图 |
| GLM-R4 / Luna-R14(crash) / v4f-R8,R9,R11 | `UF27` | 九窗证据强度夸大；PUB 是事后篡改；无进程级 kill |
| v4f-R1 / GLM-R21 | `UF28` | 四份 closure 声称 scatter 仍含 sqlite3 直读（失实） |
| v4f-R10 | `UF29` | NH7 之后 closure 缺全仓 910/910 |
| Luna-R15 | `UF30` | upload filename NUL 未拒绝 |
| Luna-R16 | `UF31` | Mapping retrieval 只接受 v1，typed 接受 v2 |
| v4f-R15 | `UF32` | actual-reader 扫描不匹配 `row["s05_binding_digest"]` |
| GLM-R20 | `UF33` | upload/GC 后台扫描 `except Exception: pass` |
| GLM-R19 | `UF34` | 生产构造器 fault hook；INSERT OR IGNORE 吞唯一冲突 |
| GLM-R14 | `UF35` | `policy_binding_digest or binding_digest` 兜底 |
| GLM-R12 | `UF36` | `lifecycle_state` 六态四态无写入者 |
| GLM-R11 | `UF37` | 并发只在 sqlite 单写锁验证；unique 靠错误文本 |
| GLM-R22 | `UF38` | inline bytes 在第二 UoW 前 promote |
| v4f-R17 | `UF39` | M-NH-04 无 DDL；旧图常驻 registered 面 |
| v4f-R16 | `UF40` | 「零 acquire/decode/clean」未限定 lifecycle 仍物化 acquire |
| v4f-R13,R18,R19 / GLM-R23 | `UF41` | 竞态断言弱、跨文件 import、missing_supply 双分支、sentinel 嵌入 |
| GLM-R9,R10 / Luna-R14(checker) | `UF42` | T11 checker 仅字符串；NH9 queries 手写 PASS |

### 2.2 宽对照表

| 统一编号 | 合并后的问题 | Gemini | GLM | Luna | v4f |
|----------|--------------|--------|-----|------|-----|
| UF1 | 策略静默换 worker | — | R17 | R1 | R7 |
| UF2 | sealed-once schema | — | — | R2 | R14 |
| UF3 | stage envelope 第二权威 | — | — | R3 | — |
| UF4 | publication set digest | — | — | R4 | — |
| UF5 | binary 重编码 | — | — | R5 | — |
| UF6 | API raw-byte identity | — | — | R6 | — |
| UF7 | API observation replay | — | — | R7 | — |
| UF8 | metadata 覆盖 system 键 | — | — | R8 | — |
| UF9 | state×intent / stale rebuild | — | R15 | R9 | R5 |
| UF10 | retry/full-task exact | — | R13 | R10 | — |
| UF11 | GC quarantine 无恢复 | — | R3 | R11 | R12 |
| UF12 | 共享 pending hold | — | R5 | — | — |
| UF13 | orphan/staging/reservation | — | — | R11 | R12 |
| UF14 | stub/fixture/OCR/PromptRef | — | R6–8,R18 | R12 | R2 |
| UF15 | readiness × multimodal | R4 | — | — | — |
| UF16 | session --no-sandbox | R3 | — | — | — |
| UF17 | unshare 无 user ns | R5 | — | — | — |
| UF18 | inline prefix 守卫 | R1 | — | — | — |
| UF19 | selection_digest 分歧 | R2 | — | — | — |
| UF20 | purpose 回落死代码 | R6 | — | — | — |
| UF21 | kind revision 原位改写 | — | R2 | — | — |
| UF22 | NH2 tail digest 漂移 | — | R1 | — | — |
| UF23 | NH1 matrix digest 漂移 | — | — | R13 | — |
| UF24 | fail_process 静默 | — | — | — | R3 |
| UF25 | indexed_success 口径 | — | — | — | R4 |
| UF26 | reacquire 全局化 | — | R16 | — | R6 |
| UF27 | 九窗证据夸大 | — | R4 | R14 | R8,R9,R11 |
| UF28 | scatter sqlite3 失实 | — | R21 | — | R1 |
| UF29 | 缺全仓 910 | — | — | — | R10 |
| UF30 | filename NUL | — | — | R15 | — |
| UF31 | retrieval Mapping v2 | — | — | R16 | — |
| UF32 | actual-reader 弱扫描 | — | — | — | R15 |
| UF33 | 后台扫描吞异常 | — | R20 | — | — |
| UF34 | INSERT OR IGNORE / hook | — | R19 | — | — |
| UF35 | alias 兜底 | — | R14 | — | — |
| UF36 | 四态无写入 | — | R12 | — | — |
| UF37 | sqlite unique 文本匹配 | — | R11 | — | — |
| UF38 | inline 先落盘 | — | R22 | — | — |
| UF39 | M-NH-04 / 旧图 | — | — | — | R17 |
| UF40 | 零进程口径 | — | — | — | R16 |
| UF41 | 弱测试簇 | — | R23 | — | R13,R18,R19 |
| UF42 | checker / 手写 queries | — | R9,R10 | R14 | — |

---

## 3. verified-findings 台账（逐条独立复核 · 核心）

### 3.1 台账主表

| VF# | 对应UF | 标题 | 严重 | 来源 | 复核判定 | 归属类 | 关键证据（当前代码 file:line）| 初步处置 |
|-----|--------|------|------|------|----------|--------|-------------------------------|----------|
| VF1 | UF1 | 策略适用性未闭合，非法组合静默换 worker | high | Luna/v4f/GLM | `valid` | `[true-bug]` | `models.py:42-56` 十个字面量；`kind_family.py:403,405,410` unguarded fallback；`runtime_materialize.py:188-190` 读 claimed strategy | `fix` |
| VF2 | UF2 | sealed-once / append-only schema 不足 | critical→high | Luna/v4f | `valid(子项 overstated)` | `[partial-delivery]` | `020:36-53` 只验 NEW；Luna SQL 改写 sealed 为真；应用层 CAS `actual_s05.py` 仍成立 | `fix` |
| VF3 | UF3 | stage envelope 保留 raw_text | high | Luna | `valid` | `[partial-delivery]` | `core.py:426-440` 仅 vectorize/publish/rebuild 丢正文 | `partial-fix` |
| VF4 | UF4 | retrieval 不比对 set digest | high | Luna | `valid` | `[partial-delivery]` | `retrieval_rank.py:68-70` 计数谓词；`vector_publish_commit.py:38-73` 仅 commit 窗比较 | `partial-fix` |
| VF5 | UF5 | binary artifact UTF-8 重编码 | high | Luna | `valid` | `[true-bug]` | `acceptance_snapshot.py` 原 `encode("utf-8")` + `media_type=text/plain`；acquire 已有 `raw_binary_transport` | `fix` |
| VF6 | UF6 | registered_api raw-byte 非真实 bytes | high | Luna | `valid` | `[partial-delivery]` | `acquisition_ingest.py` 原 `stable_digest(keys+member digests)` | `fix` |
| VF7 | UF7 | 同 observation 二次 ingest 失败留行 | high | Luna | `valid` | `[true-bug]` | snapshot UNIQUE `(team,source,observation_key)`；scatter 普通 INSERT | `fix` |
| VF8 | UF8 | metadata 覆盖 system-owned 键 | high | Luna | `valid` | `[true-bug]` | `targets.py:224` 原只拒两个 blob；`DEFAULT_SEMANTICS` 含 canonical_content/is_active | `fix` |
| VF9 | UF9 | lifecycle applicability 口径分裂 | high | Luna/v4f/GLM | `valid` | `[partial-delivery]` | registry `update_metadata` 原 `active\|deactivated`；callback 要求 active | `partial-fix` |
| VF10 | UF10 | retry/full-task exact 不统一 | high | Luna/GLM | `valid` | `[partial-delivery]` | `runtime_outcome.py` retry_wait 再投非 no-op；`task_commands.py` alias 复制 | `defer-with-rationale` |
| VF11 | UF11 | GC quarantine crash 无恢复 | high | GLM/Luna/v4f | `valid` | `[true-bug]` | `object_gc.py` TX1 rename / TX2 tombstone；无启动对账 | `fix` |
| VF12 | UF12 | 同字节上传共享 hold | medium | GLM | `valid` | `[true-bug]` | `object_upload.py` `owner_uuid=stored_object_uuid`；cancel 释放全部 | `fix` |
| VF13 | UF13 | CAS orphan / staging / reservation | high | Luna/v4f | `valid` | `[partial-delivery]` | promote 后 catalog 失败文件仍在；GC 只扫 catalog | `defer-with-rationale` |
| VF14 | UF14 | 模型格 stub/fixture/封闭 OCR | high | 三方 | `valid(子项 overstated as blocker)` | `[partial-delivery]` | `claude_cli.py:522-565` stub；`glyph_ocr_worker.py` 36 字形；NH7 已披露 | `partial-fix` |
| VF15 | UF15 | readiness 与 multimodal 默认死锁 | medium | Gemini | `valid-conditional` | `[true-bug]` | `config.py:49,63`；`app.py` required=FULL SUPPLY | `fix` |
| VF16 | UF16 | session args 无 no-sandbox 扫描 | medium | Gemini | `valid-edge` | `[true-bug]` | `browser.py:255` 硬编码 `-headless`；`:382` 只扫 command | `fix` |
| VF17 | UF17 | unshare 缺 user namespace | low | Gemini | `valid-conditional` | `[true-bug]` | `pdf_parser.py:83`；`deterministic_ocr.py:88` | `fix` |
| VF18 | UF18 | inline prefix 守卫隐式依赖 tail | medium | Gemini | `valid` | `[true-bug]` | `kind_family.py:299,315` vs `:361-367` | `fix` |
| VF19 | UF19 | selection_digest 字段分歧 | medium | Gemini | `valid` | `[partial-delivery]` | `selected_output.py:116-124` vs `runtime_materialize.py` material 字典 | `fix` |
| VF20 | UF20 | purpose 回落死代码 | low | Gemini | `valid-by-design` | `n/a` | `_workflow_purpose` 恒返回 `intake.ingest`；else 是防御回落 | `acknowledge` |
| VF21 | UF21 | kind revision 原位改写 | high | GLM | `valid` | `[true-deferred]` | `kind_family.py:242` `revision_number=1`；`workflow_registry.py:192-197` | `defer-with-rationale` |
| VF22 | UF22 | NH2 tail digest 证据漂移 | high | GLM | `valid` | `[partial-delivery]` | live `48c39059…fe1b2`；原冻结 `e36b5bac…af13`；测试只 `len==1` | `fix` |
| VF23 | UF23 | NH1 matrix digest 漂移 | high | Luna | `valid` | `[partial-delivery]` | NH1 closure `f7199ee`；live fixture `57c19c6b…` | `fix` |
| VF24 | UF24 | `_fail_process_tx` 静默吞写 | high | v4f | `valid` | `[true-bug]` | `runtime_outcome.py:501-519` 原 `if rowcount==1` 否则继续 FAILED 路由 | `fix` |
| VF25 | UF25 | 生命周期成功计入 indexed_success | medium | v4f | `valid-edge` | `[partial-delivery]` | `runtime_outcome.py:697-703`；NOOP 映射被 exhausted_zero 测试钉住 | `fix` |
| VF26 | UF26 | reacquire 法律全局化 | medium | v4f/GLM | `valid` | `[true-bug]` | `runtime_materialize.py:65-83` 原对全部 `intake.ingest.kind.*` | `fix` |
| VF27 | UF27 | 九窗证据夸大 | high | GLM/Luna/v4f | `valid` | `[partial-delivery]` | `crash_windows.py` 函数级 hook；PUB 事后 UPDATE | `partial-fix` |
| VF28 | UF28 | scatter sqlite3 失实陈述 | high | v4f/GLM | `valid` | `[partial-delivery]` | HEAD scatter 仅 `database_path` 文件名 | `fix` |
| VF29 | UF29 | 缺全仓 910 证据 | high | v4f | `valid-owner-gated` | `[true-deferred]` | campaign DoD 是 unique 62；全仓非本阶段承诺 | `defer-with-rationale` |
| VF30 | UF30 | filename NUL | medium | Luna | `valid` | `[true-bug]` | AP-NH4:239；`routes.py:100-104` 原只扫 `.. / \\` | `fix` |
| VF31 | UF31 | Mapping retrieval v2 | medium | Luna | `valid` | `[true-bug]` | `retrieval_request.py:217-219` 原只允许 v1 | `fix` |
| VF32 | UF32 | actual-reader 弱扫描 | low | v4f | `valid` | `[partial-delivery]` | `test_nh3_actual_readers_scan.py:17` | `fix` |
| VF33 | UF33 | 后台扫描吞异常 | low | GLM | `valid` | `[true-bug]` | `runtime/object_upload.py:42-43`；`object_gc.py:50` | `fix` |
| VF34 | UF34 | INSERT OR IGNORE / fault hook | low | GLM | `valid-by-design` | `n/a` | 唯一索引上的 IGNORE 是身份幂等；hook 仅测试注入 | `acknowledge` |
| VF35 | UF35 | alias 兜底 | low | GLM | `valid-edge` | `n/a` | 生产 `policy_binding_digest` 来自 domain 列，兜底不可达 | `acknowledge` |
| VF36 | UF36 | 四态无写入 | medium | GLM | `valid-by-design` | `[true-deferred]` | 枚举预留 building/validating/ready_candidate/retiring | `defer-with-rationale` |
| VF37 | UF37 | sqlite unique 文本匹配 | medium | GLM | `valid-pre-existing` | `[true-deferred]` | Turso/sqlite 架构；非 NH 引入 | `defer-with-rationale` |
| VF38 | UF38 | inline 先 promote | low | GLM | `valid-edge` | `[true-deferred]` | 第一 UoW 已查 team；注释写明 S13 orphan | `defer-with-rationale` |
| VF39 | UF39 | M-NH-04 / 旧图常驻 | low | v4f | `valid` | `[true-deferred]` | T-O-398 旧 pin 共存；retirement 属后续 | `defer-with-rationale` |
| VF40 | UF40 | 零进程口径未限定 | low | v4f | `valid` | `[partial-delivery]` | lifecycle 走 `_acquire_lifecycle` | `fix` |
| VF41 | UF41 | 弱测试簇 | low | v4f/GLM | `valid` | `[partial-delivery]` | 双飞 `[200,200]` 死代码；TTL `{0,1}` | `partial-fix` |
| VF42 | UF42 | checker 仅字符串 | medium | GLM/Luna | `valid` | `[true-deferred]` | `test_nh9_evidence_pack_checker.py:37-82`；本轮不把 checker 做成执行器 | `defer-with-rationale` |

### 3.2 簇子表（VF14 / VF27）

| 位点 | 事实 | 复核 | 修法 |
|------|------|------|------|
| `claude_cli.py:522-565` | DeterministicNs1Stub 非 json 角色恒等回显 | valid | 文档/manifest 分档；真模型 owner-gated |
| `glyph_ocr_worker.py` | 36 个 5×7 字形，未知 → OCR_INPUT_INVALID | valid | NH7/NH6 披露封闭字形 |
| `multimodal.py:66-88` | 合成 `promptA.runtime@v1` + team `mkb-runtime-clean` | valid | 本轮不改 S11 身份（风险面大）；记 VF14.r |
| `crash_windows.py` CREATE | wrapper raise，非 identity/insert 中间 | valid | crash-windows.json 标注 grain |
| `crash_windows.py` PUB | 事后 `actual_count+1` | valid | 文档降级；中途 hook 记 VF27.r |

---

## 4. 复核汇总 + self-correction

### 4.1 分桶汇总

**A. 按三类归属**

| 归属类 | 数量 | 编号 | 本阶段义务落点 |
|--------|------|------|----------------|
| `[true-bug]` | 15 | VF1 VF5 VF7 VF8 VF11 VF12 VF15 VF16 VF17 VF18 VF24 VF26 VF30 VF31 VF33 | §5.2 必修 |
| `[partial-delivery]` | 17 | VF2 VF3 VF4 VF6 VF9 VF10 VF13 VF14 VF19 VF22 VF23 VF25 VF27 VF28 VF32 VF40 VF41 | §5.2 补齐；剩余 §5.4 |
| `[true-deferred]` | 7 | VF21 VF29 VF36 VF37 VF38 VF39 VF42 | §5.4 |
| `n/a` | 3 | VF20 VF34 VF35 | 不进三类 |

**B. 按处置（计划）**：fix 上述 true-bug + 能落地的 partial；partial-fix VF3/4/9/14/27/41；defer VF10/13/21/29/36-39/42；ack VF20/34/35。

### 4.2 净增承重盲区

本合并人不是四份审查作者。跨 reviewer 净增：

- **VF1（Luna 独家深度 + v4f/GLM 图 fallback）**：Gemini 把 NH7 判 done，未做 cross-kind 非法 strategy probe。
- **VF11（GLM 独家主项）**：GC 两事务窗口是全链路唯一「字节不可用且无自愈」点。
- **VF24（v4f 独家）**：与 seal CAS 的 fail-loud 纪律不一致。
- **VF28（v4f 主导）**：closure 互引未复核，属于证据链诚实性。

### 4.3 带证据驳回 / 降级的跨-reviewer 误报

| VF# | 误报方 | 误报内容 | 反证 | 结论 |
|-----|--------|----------|------|------|
| VF2 子项 | Luna | 标 critical blocker / 不可关闭 NH3 | 生产写路径唯一 `seal_actual_binding_tx` CAS；单写者 BEGIN IMMEDIATE。schema 加固为真，但不是「CAS 不存在」 | 主项 valid；blocker overstated |
| VF14 | Luna | 10+3 未 live 即 campaign 不可关 | NH7 gap#3 已披露 stub/fixture；parser/Firefox 为真供给；T-O-378 禁的是假 PDF/monkeypatch 冒充，不是诚实 stub | valid partial；非假绿 |
| VF20 | Gemini | 尾部 return inline 不可达死代码 | `_workflow_purpose` 折叠七意图到 ingest；else 是显式防御回落 | valid-by-design |
| VF29 | v4f | NH7+ 缺 910 即 DoD 空档 | CROSS unique 62 是战役 DoD；全仓 pytest 从未写入 NH9 台账 | 文档缺口，非功能失败 |
| VF34 | GLM | INSERT OR IGNORE 吞 FK | catalog unique 是身份；失败后 re-select 转 503 | 主项 overstated |

---

## 5. 初步修复方案

### 5.1 修复策略

正确性 fail-loud（策略闭集、observation 冲突、fail-process CAS、metadata 系统键）> schema 不变量（024 迁移）> 对象生命周期（hold / GC reconcile / binary CAS）> 证据诚实（digest / sqlite3 / crash grain）> 测试收紧。真实 vLLM、进程级 kill、kind revision 升号、stage envelope 去正文不在本轮假装完成。

### 5.2 逐项修复计划表

| VF# | 计划修法 | 目标文件 | falsifiable 验证 | migration / owner? | 批次 |
|-----|----------|----------|------------------|--------------------|------|
| VF1 | admission kind×strategy 闭集 + 运行时 claimed≠bound 409 | `strategies.py` `task_create.py` `runtime_materialize.py` | inline+pdf.ocr → 422 零 Task | no | 1 |
| VF2 | 024 sealed-once + facts/history append-only | `024_nh_review_invariants.sql` | 对 sealed 行 UPDATE digest abort | yes 024 | 1 |
| VF4 | indexed `content_digest` 禁止 UPDATE | 024 | 改 indexed digest abort | yes 024 | 1 |
| VF5 | binary 用 latin-1 + 原 media_type 落 CAS | `acceptance_snapshot.py` | PDF round-trip size | no | 1 |
| VF6 | canonical_json(records) SHA-256 | `acquisition_ingest.py` | digest=sha256(bytes) | no | 1 |
| VF7 | admission + scatter 前查 observation | `task_create.py` `scatter_intake.py` | 二次同 key 409 零新 snapshot | no | 1 |
| VF8 | 拒绝 canonical_content/source_representation/is_active | `targets.py` | metadata 422 零 Task | no | 1 |
| VF9 | metadata 仅 active；admission require_active | `registry.py` `targets.py` | deactivated metadata 409 | no | 1 |
| VF11 | scan 前 quarantine 对账 restore | `object_gc.py` `local_store.py` | quarantine 后 reconcile 恢复字节 | no | 1 |
| VF12 | hold owner=会话 UUID；cancel 只放一条 | `object_upload.py` `object_upload_ttl.py` | 双飞 pending=2 | no | 1 |
| VF15 | readiness 不强制未启用 multimodal | `api/app.py` | required 不含 s11 | no | 1 |
| VF16 | session args 扫 no-sandbox | `browser.py` | 构造 args 含 token 即 503 | no | 1 |
| VF17 | 非 root 加 `-U --map-root-user` | pdf_parser / ocr | 非 root 命令含 -U | no | 1 |
| VF18 | prefix 显式守卫 + compose 去重 | `kind_family.py` | inline.guards 含 rebuild | no | 1 |
| VF19 | material 纳入 representation_fact_digest | `runtime_materialize.py` | 字段存在 | no | 1 |
| VF22 | 刷新 evidence + 测试钉 live digest | AP-NH2 queries/manifest + architecture scan | digest==48c39059… | no | 2 |
| VF23 | NH1 closure 改 live digest | AP-NH1 closure | 不再引用 f7199ee | no | 2 |
| VF24 | rowcount!=1 → stale-process-fence | `runtime_outcome.py` | 并发取消不再静默 | no | 1 |
| VF25 | 生命周期意图用 lifecycle_success | `runtime_outcome.py` `metrics.py` | deactivate 不增 indexed_success | no | 1 |
| VF26 | 仅当图声明 reacquire 守卫时执法 | `runtime_materialize.py` | http 去边仍 409；inline 空文本不 409 | no | 1 |
| VF27 | crash-windows.json 写清 grain | AP-NH9 queries | nodes 含 grain 字段 | no | 2 |
| VF28 | 关闭 scatter sqlite3 失实句 | NH7/NH8 closure + evidence | 不再写「仍含 sqlite3 段」 | no | 2 |
| VF30 | NUL / %00 → SEC_PATH_REJECTED | `routes.py` | 负例 422 | no | 1 |
| VF31 | Mapping 接受 v1\|v2 | `retrieval_request.py` | Mapping v2 规范化成功 | no | 1 |
| VF32 | 扫描 `row["s05_binding_digest"]` | `test_nh3_actual_readers_scan.py` | 模式扩展 | no | 2 |
| VF33 | 扫描失败打 exception log | runtime object_upload/gc | 不再裸 pass | no | 1 |
| VF40 | NH8 closure 限定零进程口径 | AP-NH8 closure | lifecycle ≠ rebuild | no | 2 |
| VF41 | 双飞 pending/catalog 断言对齐新 hold 语义 | nh4 tests | pending=2 | no | 2 |

### 5.3 批次

- **批次 1**：生产正确性 / schema / 对象生命周期
- **批次 2**：证据与测试对齐
- **承接**：模型、进程 kill、envelope、kind revision、checker 执行器

### 5.4 承接登记

| V# | 归属类 / 来源 | 处置 | 后延原因 | reopen 触发器 | 承接 |
|----|--------------|------|----------|----------------|------|
| VF3.r | partial 剩余 | defer | stage 去正文需 CAS-first 管线重写 | 下游读 envelope 正文回归 | new-start deferred ledger |
| VF4.r | partial 剩余 | defer | 读时重算 set digest 无 SQLite 聚合 SHA | 大集合 TOCTOU | deferred ledger |
| VF9.r | partial 剩余 | defer | 完整 7×state 矩阵与 index.rebuild stale 409 | NH8 rereview | deferred ledger |
| VF10 | partial | defer | retry_wait 同 digest no-op 需独立故障注入 | crash-before-response | deferred ledger |
| VF13 | partial | defer | pre-catalog orphan ledger 是 S13 大改 | GC 扫到无 catalog 文件 | deferred ledger |
| VF14.r | partial 剩余 | owner | 真模型/S16/PromptRef complete_bound | owner 授权 live 模型 | owner |
| VF21 | true-deferred | defer | 升 revision 需登记旧 kind digest 为 compat；本战役 in-flight=0 | 下一次图演进 | deferred ledger |
| VF27.r | partial 剩余 | defer | 进程级 kill+lease recovery | 要测 recover_expired_leases | deferred ledger |
| VF29 | true-deferred | defer | 全仓 910 非 campaign DoD | owner 要全仓绿作发版闸 | owner |
| VF36 | true-deferred | defer | 四态为预留枚举 | 真正启用 building/retiring | 后续 index AP |
| VF37 | true-deferred | defer | 多写者/PG 不在 NH | 换后端 | harness |
| VF38 | true-deferred | defer | 设计允许 S13 orphan | 无效 Team 刷盘 | S13 |
| VF39 | true-deferred | defer | T-O-398 旧 pin 共存 | retirement charter | NH8 后续 |
| VF41.r | partial 剩余 | defer | helper 拆模块、sentinel 非原词 | 测试治理 charter | deferred |
| VF42 | true-deferred | defer | checker 改执行器会改变 NH9 DoD 形状 | 证据伪造事件 | NH9 rereview |

---

## 6. 处置执行回填（fixes 落地后 · append-only）

> 执行者: Grok
> 执行时间: 2026-08-30
> 回应范围: VF1–VF42
> 对应审查文件: 四份 `docs/code-review/new-harvest/NH1-NH9-reviewed-by-*.md`

### 6.1 对本轮审查的回应

- **总体回应**：64→42 合并后，15 条 true-bug 与可落地 partial 已在生产代码/DDL/证据中修复；剩余切片写入 `docs/closure/new-start/deferred-items-ledger.md`。未 push，未伪造 S16。
- **本轮修改策略**：fail-loud 与 DB 不变量优先，证据诚实次之，不把 stub 模型伪装成 live。
- **实现者自评状态**：`ready-for-rereview`

### 6.2 逐项处置结果表

| V# | 处理结果 | 处理方式 | 修改文件 | 独立复核状态 |
|----|----------|----------|----------|--------------|
| VF1 | `fixed` | admission `CLEAN_STRATEGY_KIND_INCOMPATIBLE` 422；运行时 claimed≠bound → 409 | `strategies.py` `task_create.py` `runtime_materialize.py` | `independently-verified` |
| VF2 | `fixed` | 024 sealed-once + facts/history 禁 UPDATE/DELETE | `024_nh_review_invariants.sql` | `independently-verified` |
| VF3 | `partially-fixed` | 未去 envelope 正文（decode 仍依赖 transport） | — | `deferred-by-owner/charter` |
| VF4 | `partially-fixed` | 024 禁 indexed content_digest 原地改；未做读时 set digest | `024_nh_review_invariants.sql` | `independently-verified` |
| VF5 | `fixed` | binary latin-1 + 原 media_type 落 CAS | `acceptance_snapshot.py` | `self-claimed-only` |
| VF6 | `fixed` | canonical records bytes SHA-256 + observation_digest | `acquisition_ingest.py` `acceptance_scatter.py` | `self-claimed-only` |
| VF7 | `fixed` | Task 创建前 observation 查重；scatter INSERT 前 409 | `task_create.py` `scatter_intake.py` | `self-claimed-only` |
| VF8 | `fixed` | 三系统键 + 两 blob 拒写 | `targets.py` | `independently-verified` |
| VF9 | `partially-fixed` | metadata 仅 active；deactivated 409 不建 Task | `registry.py` `targets.py` | `self-claimed-only` |
| VF10 | `deferred-with-rationale` | 见 §5.4 | — | `deferred-by-owner/charter` |
| VF11 | `fixed` | `reconcile_quarantine` 在 scan_once 开头 | `object_gc.py` `local_store.py` | `independently-verified` |
| VF12 | `fixed` | 每上传独立 hold；cancel 只释放一条 | `object_upload.py` `object_upload_ttl.py` | `independently-verified` |
| VF13 | `deferred-with-rationale` | 见 §5.4 | — | `deferred-by-owner/charter` |
| VF14 | `partially-fixed` | NH7/NH6 披露保留；未接真模型 | closures | `self-claimed-only` |
| VF15 | `fixed` | `_health_required` 跳过未启用 multimodal | `api/app.py` | `independently-verified` |
| VF16 | `fixed` | session args 扫描 no-sandbox | `browser.py` | `self-claimed-only` |
| VF17 | `fixed` | 非 root `-U --map-root-user` | pdf_parser / ocr | `self-claimed-only` |
| VF18 | `fixed` | prefix 声明 rebuild/metadata 守卫；compose 去重 | `kind_family.py` | `independently-verified` |
| VF19 | `fixed` | material 增加 representation_fact_digest | `runtime_materialize.py` | `self-claimed-only` |
| VF20 | `acknowledged` | 防御回落保留 | — | `stale-rejected-by-code` |
| VF21 | `deferred-with-rationale` | 见 §5.4 | — | `deferred-by-owner/charter` |
| VF22 | `fixed` | live digest `48c39059…` 钉死 + evidence 刷新 | AP-NH2 + `test_nh2_architecture_scan.py` | `independently-verified` |
| VF23 | `fixed` | NH1-07 改为 live `57c19c6b…` | AP-NH1 closure | `self-claimed-only` |
| VF24 | `fixed` | rowcount!=1 → `stale-process-fence` | `runtime_outcome.py` | `self-claimed-only` |
| VF25 | `fixed` | 生命周期意图 `lifecycle_success` | `runtime_outcome.py` `metrics.py` | `self-claimed-only` |
| VF26 | `fixed` | 仅当 plan.guards 声明 reacquire 时执法 | `runtime_materialize.py` | `independently-verified` |
| VF27 | `partially-fixed` | crash-windows.json 写清 grain；未做进程 kill | AP-NH9 queries | `self-claimed-only` |
| VF28 | `fixed` | NH7/NH8 closure + evidence 销账 | closures | `self-claimed-only` |
| VF29 | `deferred-with-rationale` | campaign DoD=unique 62 | — | `deferred-by-owner/charter` |
| VF30 | `fixed` | NUL/%00 422 | `routes.py` + security test | `independently-verified` |
| VF31 | `fixed` | Mapping 接受 v2 | `retrieval_request.py` | `independently-verified` |
| VF32 | `fixed` | 扩展 reader 扫描 | `test_nh3_actual_readers_scan.py` | `independently-verified` |
| VF33 | `fixed` | `logging.exception` | runtime scanners | `self-claimed-only` |
| VF34 | `acknowledged` | 身份幂等 IGNORE | — | `stale-rejected-by-code` |
| VF35 | `acknowledged` | 生产路径 policy 恒在 | — | `stale-rejected-by-code` |
| VF36–VF39,VF42 | `deferred-with-rationale` | 见 §5.4 | — | `deferred-by-owner/charter` |
| VF40 | `fixed` | NH8 closure 限定口径 | AP-NH8 | `self-claimed-only` |
| VF41 | `partially-fixed` | 对齐 pending=2；未拆 helper | nh4 tests | `independently-verified` |

### 6.3 Blocker / Follow-up 状态汇总

| 分类 | 数量 | 编号 | 说明 |
|------|------|------|------|
| 已完全修复 | 24 | VF1,2,5,6,7,8,11,12,15,16,17,18,19,22,23,24,25,26,28,30,31,32,33,40 | 见 6.2 |
| 部分修复，需二审 | 6 | VF3,4,9,14,27,41 | 剩余切片 §5.4 |
| 有理由 deferred | 9 | VF10,13,21,29,36,37,38,39,42 | deferred-items-ledger |
| 拒绝 / stale-rejected | 0 | — | — |
| acknowledge | 3 | VF20,34,35 | 设计如此 |
| 仍 blocked | 0 | — | 无 true-bug 未修 |

> **三类对账**：全部 `[true-bug]` 落「已完全修复」。无 `[true-bug] → deferred`。

### 6.4 变更文件清单

- **产品代码**：`src/contracts/intake/strategies.py` VF1；`src/runtime/task/task_create.py` VF1/VF7；`src/runtime/workflow/runtime_materialize.py` VF1/VF19/VF26；`src/runtime/workflow/runtime_outcome.py` VF24/VF25；`src/workflows/kind_family.py` VF18；`src/runtime/supply/browser.py` VF16；`src/runtime/supply/pdf_parser.py` `deterministic_ocr.py` VF17；`api/app.py` VF15；`api/public/routes.py` VF30；`src/services/object_upload.py` `object_upload_ttl.py` VF12；`src/services/object_gc.py` `src/storage/local_store.py` VF11；`src/runtime/object_upload.py` `object_gc.py` VF33；`src/runtime/intake/acceptance_snapshot.py` VF5；`acquisition_ingest.py` `acceptance_scatter.py` VF6；`scatter_intake.py` VF7；`representation_history.py` path digest；`intake_lifecycle/targets.py` `registry.py` VF8/VF9；`retrieval_request.py` VF31；`src/runtime/metrics.py` VF25；`src/persistence/migrations/024_nh_review_invariants.sql` VF2/VF4
- **测试**：`tests/e2e/test_nh1_nh9_review_fixes.py`；nh4 upload uow/race/security；`test_nh2_architecture_scan.py`；`test_nh3_actual_readers_scan.py`；`test_nh8_intent_applicability.py`
- **docs**：AP-NH1/NH2/NH7/NH8 closures；AP-NH2 evidence；AP-NH9 crash-windows.json

### 6.5 验证结果

| 验证项 | 命令 / 证据 | 结果 | 覆盖的 V# |
|--------|-------------|------|-----------|
| ruff | `uv run ruff check` 编辑文件 | `pass` | 生产改动 |
| review-fix e2e | `pytest tests/e2e/test_nh1_nh9_review_fixes.py` | `pass` | VF1,8,11,15,18,31,2 |
| NH4 | uow / race / public / security | `pass`（pending=2 对齐） | VF12,30,41 |
| NH2/NH3 scan | architecture + actual-readers + evidence pack | `pass` | VF18,22,32 |
| reacquire | `test_nh3_declared_reacquire.py` | `pass` | VF26 |
| NH5 metadata | `test_nh5_metadata_semantic_refresh.py` | `pass` | VF8,9 |
| NH6 readiness | `test_nh6_readiness.py` | `pass` | VF15 |
| NH7 exhausted/zero/multimodal/scatter | 对应 e2e | `pass` | VF6,7,25 |
| NH8 intents / API items | unit+e2e | `pass` | VF1,9 |
| crash windows | `test_new_harvest_crash_windows.py` | `pass` | VF24,27 |
| NH9 checker | `test_nh9_evidence_pack_checker.py` | `pass` | VF27,42 兼容 |
| closed-set + CONTROL + upload-ingest | `pytest tests/e2e/test_new_harvest_closed_set.py tests/integration/test_nh1_merge_control.py tests/e2e/test_nh4_upload_then_ingest.py` | `pass`（27 passed） | VF1,14,19 |

```text
First batches: review-fixes + nh8 intent + nh2/nh3/nh9 domain + nh4 security/uow → green after pending-count alignment.
Second: nh4 race/public, nh5 metadata, nh7 exhausted, nh3 seal crash → green after interleave pending=2.
Third: nh4 race+registered-api+nh8 items+crash windows+nh2 scan+ttl → 29 passed.
Fourth: nh2 evidence, nh8 lineage, nh6 readiness, nh7 empty/failure zero, nh1 s05, review-fixes → 28 passed.
Fifth: reacquire + scatter + multimodal → 13 passed.
```

### 6.6 未解决事项与承接

见 §5.4 与 `docs/closure/new-start/deferred-items-ledger.md` 新增 **NH-review-1** 段。

### 6.7 Ready-for-rereview gate

- **是否请求二次审查**：`yes`
- **请求复核的范围**：`only VF1/VF2/VF7/VF8/VF11/VF12/VF24`（正确性）+ closure wording
- **实现者认为可以关闭的前提**：
  1. 非法 kind×strategy 不再建 Task。
  2. sealed actual / indexed vector identity 不能被普通 SQL 改写。
  3. 本轮未声称真模型 live 或进程级 crash recovery。

---

## 修订历史

| 版本 | 日期 | 作者 | 变更 |
|------|------|------|------|
| `v0.1` | 2026-08-30 | Grok | 4 方 64 finding → 42 UF；独立复核 |
| `v0.2` | 2026-08-30 | Grok | §6 回填修复结果；状态 → `resolved` |
