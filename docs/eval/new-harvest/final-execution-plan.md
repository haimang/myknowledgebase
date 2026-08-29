# new-harvest —— Final Execution Plan（planning · 站③ final）by GPT

> **stage**：`final`（站③·冻结/权威）· **作者**：`GPT`（panel：`Grok second-opinion via frozen pre-charter-qna`）· **时间**：`2026-08-29`
> **本链 scope-fence**：阶段族 `new-harvest` 下 `intake-four-channel-live` 链站③；把四 source kind、10 clean strategy、3 registered-api operation 经真实 acquire/decode/clean、S04 semantics、既有 publication/retrieval 收成可执行闭集。
> **文档性质（自宣告）**：**取代 [`initial-planning.md`](initial-planning.md) + [`proposed-planning.md`](proposed-planning.md)**，作 action-plan 制作前唯一执行基线；本文冻结零决策，仅 CITE frozen QNA、reference-anchor 与 HEAD。
> **输入权威次序（NORMATIVE）**：冻结 QNA（pre-initial + pre-charter）> HEAD `1221aa1` 实测 > reference-anchor/design artifacts。
> **下游消费者**：§11.A 枚举的 `AP-NH1..AP-NH9` 九份 action-plan；每份头部须逐字引用本 final 与对应台账 ID 区间。
> **文档状态**：`frozen / v1.0`
> **Truth cutoff**：foundational `T-O-376..389` + execution `T-O-390..407` + reference-checked `T-R-NH-01..27`。

---

## 0. TL;DR `[核心]`

- **核心论点**：new-harvest 的执行对象已经从“选择候选方案”切换为 9 个有序 AP：NH1 验证 owner-chosen substrate并修 proof baseline；NH2/NH3 建 kind graph、typed representation history 与 actual S05；NH4/NH5 并行建设 upload 和 semantic/retrieval；NH6 交付真实本地 runtime；NH7 激活 10+3 vertical slices；NH8 闭合七意图/exact-clean/compat；NH9 只做 closed-set、race/crash/security 总验。每个 AP 自带 A/B/C/D 四台账，任何较低测试层、503、monkeypatch、Task success 或 publication flag 均不能顶替产品终态。
- **本态相对 proposed 做了什么**：① critique 19 个承重点，2 个 `CORRECT`、7 个 `REFINE`、其余 `CONFIRM`；② 注入 frozen `T-O-390..407` 和 final HEAD `T-R-NH-22..27`；③ 将 9 AP 的 82 个稳定工作 ID 全部配齐四台账；④ 冻结 DAG、migration IDs、17 个 anti-fake-green gate 与 9 份 action-plan 路径。
- **最承重修正**：现 `full_task` retry 即使创建新 generation 也复制 exact sealed actual；existing-object 使用新 cleaner 不在 NH v1（`T-O-401`）。旧 `s05_binding_digest` 不得 backfill actual；new actual 选边后与 Outcome 同 UoW sealed-once（`T-O-390/400`）。

---

## 1. Reference anchors / 输入与依据 `[核心]`

| 输入 | 类型 | 提供了什么 | 锚点 |
|---|---|---|---|
| `pre-initial-planning-qna.md` | `frozen foundational QNA` | 四通道、三轴、late-bind、kind family、reacquire、upload、clean/g0、semantic ledger | `T-O-376..389 / Q1..Q9` |
| `pre-charter-qna.md` v1.0 | `frozen execution QNA` | graph/S05/runtime/upload/semantics/security/lifecycle/test chosen branch | `T-O-390..407 / Q10..Q27` |
| `proposed-planning.md` | `proposed` | 21 T-R、9 AP/82 works、两级 DAG、matrix/FG/W IDs | §2/§6/§7/§9 |
| RA01 | `reference-anchor` | graph algebra、kind identity、merge、compat | `NH-RA01-B* / NH-A-01-*` |
| RA02 | `reference-anchor` | two-stage S05、seal/recovery | `NH-RA02-B* / NH-A-02-*` |
| RA03 | `reference-anchor` | representation/reacquire/opaque/print | `NH-RA03-B* / NH-A-03-*` |
| RA04 | `reference-anchor` | 10/9/3 clean、prompt、zero/member | `NH-RA04-B* / NH-A-04-*` |
| RA05 | `reference-anchor` | runtime supply/readiness/security/license | `NH-RA05-B* / NH-A-05-*` |
| RA06 | `reference-anchor` | public upload/catalog/hold/GC | `NH-RA06-B* / NH-A-06-*` |
| RA07 | `reference-anchor` | semantic authority/S06/facets/channel | `NH-RA07-B* / NH-A-07-*` |
| RA08 | `reference-anchor` | publication/query/seven intents/exact-clean | `NH-RA08-B* / NH-A-08-*` |
| RA09 | `reference-anchor` | replay/race/compat/fake-green | `NH-RA09-B* / NH-A-09-*` |
| HEAD `1221aa1` | `HEAD 实测` | 目标 Truth 尚未实施；旧 alias、两 restart scope、NOOP投影、upload/supply缺口仍在 | §2.2 `T-R-NH-22..27` |

---

## 2. 规划真相台账（Planning Truth Register · 终态全集）★ `[核心·锁死]`

### 2.1 真相全表（append-only · 截至 final）

| Truth-ID | 类型 | 子类型 | 真相内容（一句话） | 来源 | 析出态 | 下游约束 |
|---|---|---|---|---|---|---|
| `T-O-376` | owner-gated | foundational/completeness | 四通道真实 Process→可检索；503/假接线/0815-R7不算完成 | pre-initial QNA | initial | NH7/NH9 L3+L4 |
| `T-O-377` | owner-gated | foundational/fence | 四 kind；intake为变换SSOT；零CF/SMCP；禁action_branch | pre-initial QNA | initial | 全 AP redline |
| `T-O-378` | owner-gated | foundational/honesty | 假PDF、OCR盗码、monkeypatch、空clean均不得冒充完成 | pre-initial QNA | initial | NH3/NH6/NH9 |
| `T-O-379` | owner-gated | foundational/three-axis | kind×acquire×strategy；caller禁workflow_key | pre-initial QNA | initial | NH2/NH7 |
| `T-O-380` | owner-gated | foundational/experiment | unit/e2e属completeness；experiment发车日OPEN | pre-initial QNA | initial | NH9骨架非DoD |
| `T-O-381` | owner-gated | foundational/live-matrix | 10 strategy+3 operation live-to-vector；upload与七意图纳入 | pre-initial QNA | initial | NH4/NH7/NH8/NH9 |
| `T-O-382` | owner-gated | foundational/late-bind | 表示已知后闭集晚绑工人，结果进evidence/digest | pre-initial QNA | initial | NH2/NH3 |
| `T-O-383` | owner-gated | foundational/fail-loud | 绑定后不换工人；失败无向量；replay/conflict/upload同法 | pre-initial QNA | initial | 全 AP failure law |
| `T-O-384` | owner-gated | foundational/declarative | 同revision预声明live边，registered guard/control选边，选后seal | pre-initial QNA | initial | NH2/NH3 |
| `T-O-385` | owner-gated | foundational/upload | upload只造S13 handle/digest/size；不造Item；随后独立ingest | pre-initial QNA | initial | NH4 |
| `T-O-386` | owner-gated | foundational/clean | 四通道同一admitted clean；g0=clean；promptA仅LLM | pre-initial QNA | initial | NH7 |
| `T-O-387` | owner-gated | foundational/graph-cardinality | 三single kind图+scatter；mode/media不再选图 | pre-initial QNA | initial | NH2 |
| `T-O-388` | owner-gated | foundational/reacquire | 绑定前有限声明式正向再获取；decode观察；print诚实 | pre-initial QNA | initial | NH2/NH3/NH7 |
| `T-O-389` | owner-gated | foundational/semantic | 五维+tags四通道进S04、不进g0；stub不得complete | pre-initial QNA | initial | NH5/NH7 |
| `T-R-NH-01` | reference-checked | denominator | HEAD=13 single、7 public、6 unselectable、2 scatter | `lsrag_definition.py:929-1069` | proposed | NH1/NH2 inventory |
| `T-R-NH-02` | reference-checked | graph | 单input仅一binding且无selected merge | `workflow/models.py:496-497`; RA01 | proposed | NH1/NH2 |
| `T-R-NH-03` | reference-checked | selector | mode/media仍选7 profile，6图不可达 | `config_snapshots.py:500-516`; RA01 | proposed | NH2 |
| `T-R-NH-04` | reference-checked | S05 conflict | 创建时domain填s05且无UPDATE | `src/runtime/task/task_create.py:179-180`; `src/persistence/migrations/001_initial.sql:245-246` | proposed | NH1/NH3 |
| `T-R-NH-05` | reference-checked | evidence | evidence单槽、reacquire/representation guard=0 | `acquisition_ingest.py:89,660`; RA03 | proposed | NH2/NH3 |
| `T-R-NH-06` | reference-checked | representation | literal PDF、OCR盗码、无print、opaque UTF-8 | `src/runtime/intake/types.py:144-220`; RA03 | proposed | NH3/NH6 |
| `T-R-NH-07` | reference-checked | delivered-clean | 10/9/3 pure闭集在，33 tests绿 | `strategies.py:15-151`; RA04 | proposed | NH7勿重写 |
| `T-R-NH-08` | reference-checked | prompt | 7 LLM策略与三套promptA默认哈希冲突 | `strategies.py:57-147`; RA04 | proposed | NH1/NH7 |
| `T-R-NH-09` | reference-checked | runtime | 默认root 0/0、无专用依赖、S11/CLI不能运binary | `api/app.py:330-345`; RA05 | proposed | NH1/NH6 |
| `T-R-NH-10` | reference-checked | security | readiness只探名单，隔离/license/CVE未闭 | `health.py:16-25`; RA05 | proposed | NH6/NH9 |
| `T-R-NH-11` | reference-checked | upload | S13内核在，public upload/purpose=0 | `api/public/routes.py:56-452`; RA06 | proposed | NH4 |
| `T-R-NH-12` | reference-checked | upload-lifecycle | promote不写catalog/ref，全内存；orphan/GC缝 | `storage/ports.py:10-24`; RA06 | proposed | NH4 |
| `T-R-NH-13` | reference-checked | semantics | API六元组在，非API实际五维=0且stub complete | `acceptance_snapshot.py:589-615`; RA07 | proposed | NH5 |
| `T-R-NH-14` | reference-checked | projection | S06不读S04、facet=0、channel撞名 | `generation_construct.py:330-343`; RA07 | proposed | NH5 |
| `T-R-NH-15` | reference-checked | delivered-tail | g0/tail/proof/pointer/lifecycle CAS已在 | `vector_publish_commit.py:57-191`; RA08 | proposed | NH7/NH8勿重写 |
| `T-R-NH-16` | reference-checked | fake-green | search缺namespace、API无search、source测试patch+running | RA08/09 | proposed | NH1/NH9 |
| `T-R-NH-17` | reference-checked | lifecycle | rebuild/metadata仍跑inline deterministic clean | `clean_preflight.py:28-127`; RA08 | proposed | NH8 |
| `T-R-NH-18` | reference-checked | assurance | CAS/compat在，但actual/upload/mega证明红 | RA09 | proposed | NH1/NH9 |
| `T-R-NH-19` | reference-checked | test-law | L1/L2/L3/L4不可互换 | RA09 `NH-C-88` | proposed | 全 AP |
| `T-R-NH-20` | reference-checked | substrate-fit | 外部/legacy只借机制失败法，不借栈 | 九面§7 | proposed | 全 AP |
| `T-R-NH-21` | reference-checked | intent-algebra | 七意图非7×4，只有ingest按kind | `api/models.py:278-286`; RA08 | proposed | NH8 |
| `T-O-390` | owner-gated | execution/two-stage-S05 | policy/actual分账；旧列隔离且不backfill；new actual sealed-once SSOT | pre-charter Q10 | final | NH1/NH3/M-NH-01 |
| `T-O-391` | owner-gated | execution/merge | registered optional-port selected-output CONTROL，durable selection、exactly-one | pre-charter Q11 | final | NH1/NH2 |
| `T-O-392` | owner-gated | execution/representation | typed fact/history rows与Process Outcome同UoW，唯一权威 | pre-charter Q12 | final | NH2/NH3/M-NH-02 |
| `T-O-393` | owner-gated | execution/runtime-boundary | local binary ports与model-bound S11 multimodal分账 | pre-charter Q13 | final | NH1/NH6 |
| `T-O-394` | owner-gated | execution/semantic-authority | generic四字段必填非unknown；API mapper SSOT；禁自动unknown | pre-charter Q14 | final | NH5 |
| `T-O-395` | owner-gated | execution/channel | semantic_channel/vector_channel分名；旧schema窄兼容 | pre-charter Q15 | final | NH5/M-NH-06/08 |
| `T-O-396` | owner-gated | execution/object-surface | public upload+stat，无raw GET；跨team403 | pre-charter Q16 | final | NH4 |
| `T-O-397` | owner-gated | execution/exhausted-zero | 独立exhausted_zero，非indexed success、零产物、proof+empty | pre-charter Q17 | final | NH7/NH9 |
| `T-O-398` | owner-gated | execution/scope | 有界Workflow substrate留NH1–NH3，禁通用引擎扩张 | pre-charter Q18 | final | DAG/NH1/NH2 |
| `T-O-399` | owner-gated | execution/isolation | parser/OCR无网subprocess；browser non-root禁no-sandbox；supply证据门 | pre-charter Q19 | final | NH6/NH9 |
| `T-O-400` | owner-gated | execution/seal-UoW | route Outcome+actual CAS+clean eligibility同UoW | pre-charter Q20 | final | NH3/NH9 |
| `T-O-401` | owner-gated | execution/restart | full_task exact actual；rebuild replay clean；existing upgrade OOS NH v1 | pre-charter Q21 | final | NH3/NH8 |
| `T-O-402` | owner-gated | execution/main-text | decode observer三态；absent路由，unknown fail-closed | pre-charter Q22 | final | NH2/NH3/NH7 |
| `T-O-403` | owner-gated | execution/browser | render/print共享binary但分capability/profile/budget/readiness | pre-charter Q23 | final | NH6/NH7 |
| `T-O-404` | owner-gated | execution/upload-UoW | catalog+upload_pending hold同UoW后才返回handle | pre-charter Q24 | final | NH4/M-NH-05 |
| `T-O-405` | owner-gated | execution/intent-errors | 七意图applicability+code闭集；非法格不建Task/Process | pre-charter Q25 | final | NH8 |
| `T-O-406` | owner-gated | execution/test-charter | 四层不可互换；waiver只延期不降层 | pre-charter Q26 | final | 全 AP |
| `T-O-407` | owner-gated | execution/exact-clean | rebuild/metadata guard旁路clean；新clean仅未来ingest | pre-charter Q27 | final | NH8/M-NH-09 |
| `T-R-NH-22` | reference-checked | HEAD-实测/S05 | HEAD仍把domain写入NOT NULL s05且无actual状态 | `src/runtime/task/task_create.py:179-180`; `src/persistence/migrations/001_initial.sql:245-246` | final | NH1 stop gate；NH3必须migration |
| `T-R-NH-23` | reference-checked | HEAD-实测/restart | restart_scope仅full_task/atomic；full_task复制exact旧列 | `src/persistence/migrations/001_initial.sql:198-219`; `src/runtime/task/task_commands.py:237-311` | final | CORRECT Q21；NH3/NH8 |
| `T-R-NH-24` | reference-checked | HEAD-实测/zero | NOOP仍映射succeeded且无exhausted_zero disposition | `runtime_outcome.py:505-509` | final | NH7/NH9 |
| `T-R-NH-25` | reference-checked | HEAD-实测/upload | public upload/stat route与upload purpose仍为0 | `api/public/routes.py:56-452`; `storage/models.py:17-27` | final | NH4 |
| `T-R-NH-26` | reference-checked | HEAD-实测/runtime | default root仍无browser/clean_llm，依赖无PDF/browser/OCR | `api/app.py:330-345`; `pyproject.toml:13-21` | final | NH1/NH6 |
| `T-R-NH-27` | reference-checked | HEAD-实测/semantic | public descriptor仍无五维，retrieval仍无semantic facet keys | `api/models.py:107-144`; `retrieval/models.py:14-34` | final | NH5 |

### 2.2 ★ HEAD-实测真相（修正前序前提）`[核心·锁死]`

| Truth-ID | HEAD 事实（实测锚） | 对前序前提的修正 | 触发处置 |
|---|---|---|---|
| `T-R-NH-22` | `s05=domain`、NOT NULL、无seal state | QNA冻结不等于schema已改 | NH1先migration spike；NH3不得直接写业务逻辑 |
| `T-R-NH-23` | full_task复制exact且无upgrade scope | “new generation可清actual”错误 | NH3保持full_task exact；NH8禁借rebuild upgrade |
| `T-R-NH-24` | NOOP→succeeded | terminal enum不能表达产品zero | NH7新增result disposition/metrics/L4断言 |
| `T-R-NH-25` | upload/stat=0 | S13内核不等于public面 | NH4必须从public auth route验证 |
| `T-R-NH-26` | default root supply=0 | Protocol/handler存在不等于live | NH1 smoke、NH6真实供给、NH7 L3 |
| `T-R-NH-27` | semantic caller/facet=0 | S04表存在不等于四通道可滤 | NH5 contract+projection+query |

### 2.3 contract-surface-freeze `[核心]`

- **Workflow**：kind-only resolver；registered selected-output CONTROL；optional ports；eq-only fact guards；old-pin exact compat。
- **Binding/evidence**：policy vs actual；typed history；Outcome同UoW seal；full_task exact；existing upgrade OOS。
- **Runtime**：local ports vs S11 multimodal；isolated/native security/readiness；render/print分capability。
- **Public API**：upload+stat无raw GET；semantic/vector channel分名；seven-intent非法格422/409+code。
- **Product terminal**：`exhausted_zero` 独立；rebuild/metadata exact clean；L1–L4不可互换。

---

## 3. 辨证审核（critique proposed）+ 调整溯因 ★ `[核心]`

| item-ID | 裁定 | 处置 | 驱动真相 | 依据 |
|---|---|---|---|---|
| `P-DAG-9AP` | `CONFIRM` | 保留9 AP与82 work IDs | `T-O-398/406` | Q18/Q26 |
| `P-NH1-stop` | `REFINE` | NH1验证chosen branch；任一承重spike失败必须reopen，不可换duplication | `T-O-391/398` | Q11/Q18 |
| `P-S05-schema` | `CORRECT` | 旧列逻辑隔离；new actual显式state/digest/seal；旧行永久unverifiable | `T-O-390`; `T-R-NH-22` | Q10/HEAD |
| `P-merge` | `REFINE` | CONTROL candidate ports optional，只投影durable selection，禁scatter wait | `T-O-391` | Q11 |
| `P-fact-history` | `REFINE` | fact/history与各Outcome同UoW，不允许事后补写 | `T-O-392` | Q12 |
| `P-runtime-boundary` | `REFINE` | OCR按PromptRef/model budget分类，pool数不锁 | `T-O-393` | Q13 |
| `P-semantic-unknown` | `CORRECT` | generic四字段nonunknown必填；API禁自动unknown | `T-O-394`; `T-R-NH-27` | Q14/HEAD |
| `P-channel` | `REFINE` | 新schema双键；旧schema仅original/summary机械迁移 | `T-O-395` | Q15 |
| `P-object-surface` | `CONFIRM` | upload+stat，无raw GET；跨team403 | `T-O-396` | Q16 |
| `P-zero` | `REFINE` | 独立exhausted_zero，不复用metadata no_change/NOOP | `T-O-397`; `T-R-NH-24` | Q17/HEAD |
| `P-workflow-scope` | `CONFIRM` | substrate留NH且有界 | `T-O-398` | Q18 |
| `P-isolation` | `REFINE` | browser禁no-sandbox；parser无网；owner具名豁免 | `T-O-399` | Q19 |
| `P-seal-uow` | `CONFIRM` | route+actual+eligibility同UoW | `T-O-400` | Q20 |
| `P-restart` | `CORRECT` | full_task exact；existing-object upgrade移出NH v1 | `T-O-401`; `T-R-NH-23` | Q21/HEAD/S03/S05 calibration |
| `P-shell-fact` | `REFINE` | observer在decode、version进digest | `T-O-402` | Q22 |
| `P-browser-supply` | `CONFIRM` | 共享binary、分capability/profile/budget | `T-O-403` | Q23 |
| `P-upload-uow` | `CONFIRM` | catalog+pending hold后才usable | `T-O-404` | Q24 |
| `P-intent-errors` | `REFINE` | admission非法格不建Task/Process | `T-O-405` | Q25 |
| `P-test-charter` | `CONFIRM` | waiver只延期、不降层 | `T-O-406` | Q26 |
| `P-exact-clean` | `REFINE` | intent guard真正旁路，禁no-op cleaner | `T-O-407` | Q27 |

- **承重 CORRECT 摘要**：① `T-O-390` 把旧 s05 列从“未来 actual”纠正为 legacy alias；② `T-O-394` 关闭 generic/API 自动 unknown；③ `T-O-401` 纠正“new generation可重绑”，冻结full_task exact并把existing upgrade移出NH v1。

---

## 4. 范围与非范围（execution-ready 定档）`[核心]`

### 4.1 In-Scope

| ID | execution-ready 范围 | 主 AP | Truth |
|---|---|---|---|
| `S-NH-F1` | chosen graph/binding/fact/runtime smoke与可信test baseline | NH1 | `T-O-390..393/398..400/406` |
| `S-NH-F2` | kind graph、merge CONTROL、resolver、compat | NH2 | `T-O-379/384/387/391/398` |
| `S-NH-F3` | typed history、representation、reacquire、actual S05/restart | NH3 | `T-O-388/390/392/400..402` |
| `S-NH-F4` | authenticated upload+stat、bounded CAS、pending hold、GC | NH4 | `T-O-385/396/404` |
| `S-NH-F5` | strict semantic authority、S06 overlay、facet/query naming | NH5 | `T-O-389/394/395` |
| `S-NH-F6` | real local parser/browser/OCR/Vision/DU supply与安全 | NH6 | `T-O-393/399/403` |
| `S-NH-F7` | 10 strategy+3 operation vertical live-to-retrieval | NH7 | `T-O-376/381/386/397` |
| `S-NH-F8` | 七意图、exact-clean、publication lifecycle、old-pin | NH8 | `T-O-401/405/407` |
| `S-NH-F9` | closed-set、race/crash/security/compat/retrieval mega | NH9 | `T-O-383/406` |

### 4.2 Out-of-Scope / 延后

- `O-NH-01` live connector/cookie/tunnel、第五 kind、caller workflow_key、action_branch。
- `O-NH-02` cuts/g0算法重开、按通道复制tail、前端/answer generation。
- `O-NH-03` existing-object new-cleaner/validator upgrade；未来须新owner-gate（`T-O-401`）。
- `O-NH-04` raw object GET/list/presign/browser；未来导出另reopen（`T-O-396`）。
- `O-NH-05` experiment发车/评分；骨架非DoD（`T-O-380`）。
- `O-NH-06` 通用Workflow JOIN/DSL/自由表达式/loader；云OCR/CF/R2/SMCP runtime。

---

## 5. 跨阶段贯穿主题（冻结版）`[核心]`

- **技术红线**：三轴分账；事实先durable再route/seal；不热切；不复制tail；无silent skip/unknown；无raw object；无no-sandbox。
- **治理红线**：schema/security/public-contract分别独立review；owner waiver只能延期；NH1证伪即reopen final。
- **migration inventory**：`M-NH-01` actual S05；`M-NH-02` fact/history；`M-NH-03` merge/control；`M-NH-04` kind/compat；`M-NH-05` upload pending；`M-NH-06` facets；`M-NH-07` prompt catalog；`M-NH-08` retrieval naming/namespace；`M-NH-09` exact-clean/lifecycle。
- **assurance thread**：每AP适用L1–L4和F/R/C/S标签，NH9不第一次发现功能缺口。

---

## 6. DAG（关键路径 + 并行窗）—— 冻结版 `[核心]`

```text
AP-NH1 chosen-shape validation + proof baseline
  ├─ fail ─▶ STOP / reopen T-O + final（禁止静默换方案）
  ├─▶ AP-NH4 public upload ────────────────────────────────────┐
  ├─▶ AP-NH5 semantic ledger + retrieval facets ──────────────┤
  └─▶ AP-NH2 graph/kind/merge ─▶ AP-NH3 fact/history/S05 ─▶ AP-NH6 runtime ─┐
                                                                            ▼
                             AP-NH7 10+3 vertical activation（local入口另需NH4）
                                                ▼
                             AP-NH8 lifecycle/exact-clean/compat
                                                ▼
                             AP-NH9 closed-set assurance/closure
```

### 6.1 DAG 调整溯因

| DAG 变更 | 相对 proposed | 驱动真相 | 说明 |
|---|---|---|---|
| 删除pre-charter gate节点 | gates OPEN→全部CLOSED | `T-O-390..407` | final直接冻结chosen branch |
| NH1 stop/reopen升级硬门 | 建议→NORMATIVE | `T-O-391/398/406` | spike失败不能继续或换方案 |
| NH3禁止upgrade分支 | upgrade待裁→OOS | `T-O-401`; `T-R-NH-23` | full_task exact；不扩第八intent |
| NH4固定无raw read | 条件分支→upload+stat | `T-O-396/404` | AP不再设计raw GET候选 |
| NH5 strict unknown | caller/derive OPEN→严格规则 | `T-O-394/395` | contract可直接冻结 |
| NH7 zero分名 | terminal OPEN→exhausted_zero | `T-O-397` | metrics/result/L4明确 |
| NH8彻底旁路clean | skip/no-op OPEN→guard bypass | `T-O-407` | 不建no-op worker |

---

## 7. 逐下游 action-plan 工作台账（每 AP 锁死 A/B/C/D）`[核心·锁死]`

> 工作量 `XS/S/M/L/XL` 为相对复杂度；PASS evidence 四元组统一为 `commit SHA + test/query ID PASS + Truth/Q引用 + UTC`。下列 9 节与 §11.A 1:1。

### 7.1 `AP-NH1` · Chosen-shape validation 与 proof baseline（Q10–Q13/Q18–Q20/Q26）

**台账 A · 工作清单**

| 编号 | lane/类型 | 工作项 | 工作内容（有序子步） | 量 | 复用 | 风险 | Truth |
|---|---|---|---|---|---|---|---|
| `NH1-01` | inventory | 冻结执行分母 | a)脚本枚举4/10/9/3/13/2/16；b)输出old key/revision/digest/active Execution；c)与RA分母diff为零 | S | ✅ | med | `T-R-NH-01/03` |
| `NH1-02` | harness | PersistencePort recovery | a)删测试sqlite3直读；b)加Port查询；c)fan-in crash后经真实UoW恢复 | M | ♻️ | high | `T-R-NH-16/18`; `T-O-406` |
| `NH1-03` | harness | Retrieval namespace | a)创建Layer-A namespace fixture；b)请求带key/uuid；c)断言HTTP/disposition/hit/proof | M | ♻️ | high | `T-R-NH-16`; `T-O-406` |
| `NH1-04` | spike | Merge CONTROL | a)注册optional candidate ports；b)持久化selection；c)CONTROL投影单output；d)测零/双命中、缺fact、环 | L | ♻️/🆕 | high | `T-O-391/398` |
| `NH1-05` | spike | S05 schema/seal | a)建legacy/new样本；b)unsealed→sealed CAS；c)同seal replay/异seal conflict；d)传播只读actual | L | ♻️/🆕 | high | `T-O-390/400/401` |
| `NH1-06` | spike | Runtime smoke | a)真实PDF text；b)SPA render+print；c)binary model request；d)记录pin/limits/license/CVE/error | L | 🆕 | high | `T-O-393/399/403` |
| `NH1-07` | matrix | 两张合法矩阵 | a)registry生成strategy矩阵；b)生成七意图applicability；c)非法格有disposition；d)禁止笛卡尔积 | M | ✅/🆕 | med | `T-O-397/405`; `T-R-NH-07/21` |
| `NH1-08` | migration | Prompt inventory | a)列三promptA id/hash/readers；b)列旧snapshot refs；c)输出M-NH-07变更/兼容清单 | S | ✅/♻️ | med | `T-R-NH-08`; `T-O-386` |
| `NH1-09` | evidence | Foundation pack | a)收集spike/harness结果；b)按✅/♻️/🆕/⛔归档；c)发布NH2–NH6 versioned interfaces；d)失败即stop | M | 🆕 | high | `T-O-398/406` |

**台账 B · reference-anchor 清单**

| 锚 ID | 来源 | 落点 | 借鉴类型 | 处置 | 备注 |
|---|---|---|---|---|---|
| `NH1-A01` | `src/contracts/workflow/models.py:496-497` | 单port单binding | ⛔反例 | ♻️保围栏、🆕CONTROL | 禁one-of自由binding |
| `NH1-A02` | `src/runtime/workflow/runtime_outcome.py:88-137` | Outcome同UoW CAS | ✅正例 | ✅复用线性化点 | actual尚未接入 |
| `NH1-A03` | `src/runtime/task/task_create.py:179-180` | domain冒充s05 | ⛔反例 | 🆕actual schema | `T-R-NH-22` |
| `NH1-A04` | `tests/e2e/test_registered_api_scatter.py:26-33,366-367` | sqlite3-on-Turso | ⛔反例 | ♻️Port化 | recovery假红/假绿 |
| `NH1-A05` | `api/app.py:330-345`; `pyproject.toml:13-21` | default supply=0 | ⛔反例 | 🆕smoke | smoke非live DoD |
| `NH1-A06` | RA01/02/05 §6/§9 | 净新contract/test grid | 🔶参考 | 🆕spike | 不引外部runtime |

**台账 C · 测试用例**

| Test-ID | 验证什么 | 类型 | 层 | 来源 | 映射 | PASS证据 |
|---|---|---|---|---|---|---|
| `NH1-T01` | 分母/compat inventory稳定 | 短途 | unit/契约 | 🆕枚举脚本 | `NH1-01→inventory` | SHA+脚本EXIT0+`T-R-NH-01`+UTC |
| `NH1-T02` | fan-in recovery无sqlite3直读 | spike | L2集成 | ♻️现e2e | `NH1-02→recovery` | SHA+pytest node PASS+Q26+UTC |
| `NH1-T03` | namespace search真实命中 | spike | L2/L4 | ♻️现e2e | `NH1-03→query` | SHA+HTTP/query PASS+`T-R-NH-16`+UTC |
| `NH1-T04` | selected CONTROL exactly-one | spike | L1/L2 | 🆕graph test | `NH1-04→merge` | SHA+零/一/双node PASS+Q11+UTC |
| `NH1-T05` | unsealed/seal/replay/conflict | spike/F | L2 | 🆕binding test | `NH1-05→S05` | SHA+crash nodes PASS+Q10/Q20+UTC |
| `NH1-T06` | PDF/browser/multimodal实弹 | spike/S | L3 | 🆕supply smoke | `NH1-06→feasible` | SHA+3 smoke PASS+Q13/Q19+UTC |
| `NH1-T07` | legal/illegal matrix生成 | 短途 | L1契约 | 🆕matrix test | `NH1-07→manifest` | SHA+matrix digest PASS+Q17/Q25+UTC |

**台账 D · 收口评估方案与标准**

| 收口目标 | 评估方式 | PASS标准 | 证据形态 |
|---|---|---|---|
| harness可信 | NH1-T02/T03 | 无disk I/O、无422、无running超时 | test report+query payload |
| chosen graph可行 | NH1-T04 | exactly-one且不复制tail/重跑guard | compiled digest+route rows |
| chosen S05可行 | NH1-T05 | old/unsealed/sealed三类可分，二次异seal冲突 | migration snapshot+CAS log |
| runtime形态可行 | NH1-T06 | 真实binary/process成功并有负例 | pin/SBOM/smoke report |
| 下游接口冻结 | NH1-T01/T07+review | NH2–NH6均有versioned input/output/error | interface pack+review signoff |

- **DoD硬闸**：NH1-T01..T07全PASS；任何chosen shape被证伪立即STOP并reopen final。
- **NOT-成功识别**：mock Protocol、503、单unit、复制图、任意64hex、修测试期待值均不算通过。

### 7.2 `AP-NH2` · Workflow kind family、merge 与 compat（Q11/Q12/Q18/Q22）

**台账 A · 工作清单**

| 编号 | lane/类型 | 工作项 | 工作内容（有序子步） | 量 | 复用 | 风险 | Truth |
|---|---|---|---|---|---|---|---|
| `NH2-01` | graph | SelectedOutputControl | a)manifest/schema；b)optional ports；c)durable selection projection；d)exactly-one failures | L | ♻️/🆕 | high | `T-O-391` |
| `NH2-02` | guard | Representation predicates | a)登记三态/媒体谓词；b)route projection；c)eq-only；d)缺键/未知fail | M | ♻️ | high | `T-O-392/402` |
| `NH2-03` | identity | 3 single+scatter definitions | a)共享tail源；b)每kind合法边；c)scatter保持root/child；d)compile | XL | ♻️ | high | `T-O-387/398` |
| `NH2-04` | route | 多acquire/decode/clean边 | a)不同step；b)forward/no-cycle；c)每step一次；d)接merge | L | ♻️/🆕 | high | `T-O-384/388/391` |
| `NH2-05` | resolver | kind-only public resolve | a)移除mode/media选key；b)起点转fact；c)caller禁key；d)unknown fail | M | ♻️ | high | `T-O-379/387` |
| `NH2-06` | fence | 停三槽factory/暗dispatch | a)registry映射；b)图声明process；c)handler校验；d)未声明409 | L | ♻️ | high | `T-O-382/384` |
| `NH2-07` | compat | old/new coexistence | a)保留old plans；b)new unselected旧key；c)compiled lookup；d)retirement telemetry | L | ✅/♻️ | high | `T-O-398/401`; `M-NH-04` |
| `NH2-08` | architecture | 禁止面扫描 | a)public无workflow_key；b)零action_branch；c)禁表达式；d)tail唯一性 | S | ✅ | med | `T-O-377/379/398` |

**台账 B · reference-anchor 清单**

| 锚 ID | 来源 | 落点 | 借鉴类型 | 处置 | 备注 |
|---|---|---|---|---|---|
| `NH2-A01` | `src/contracts/workflow/models.py:373-525` | compiler/binding | ✅/⛔ | ♻️扩CONTROL | 保无环/unique |
| `NH2-A02` | `src/runtime/workflow/runtime_materialize.py:101-168` | typed context | ✅正例 | ♻️加fact projection | 缺键false |
| `NH2-A03` | `src/workflows/lsrag_definition.py:881-1069` | 13 profile factory | ⛔反例 | ♻️kind family | 不复制tail |
| `NH2-A04` | `src/services/config_snapshots.py:492-516` | mode/media选图 | ⛔反例 | ♻️改起点fact | `T-R-NH-03` |
| `NH2-A05` | `src/runtime/workflow/runtime_core.py:591-625` | compiled pin | ✅正例 | ✅复用 | old plan must remain |
| `NH2-A06` | RA01 `RA-01-WEB-*` | XOR/join失败法 | 🔶参考 | 🆕本仓CONTROL | 不借外部引擎 |

**台账 C · 测试用例**

| Test-ID | 验证什么 | 类型 | 层 | 来源 | 映射 | PASS证据 |
|---|---|---|---|---|---|---|
| `NH2-T01` | source_kind唯一选图 | 短途 | L1/L2 | 🆕resolver tests | `NH2-05` | SHA+4kind PASS+Q7/Q18+UTC |
| `NH2-T02` | merge一选一/零双失败 | spike | L1/L2 | 🔱NH1-T04 | `NH2-01` | SHA+CONTROL suite PASS+Q11+UTC |
| `NH2-T03` | representation guard fail-closed | 短途 | L1/L2 | 🆕guard tests | `NH2-02` | SHA+present/absent/unknown PASS+Q22+UTC |
| `NH2-T04` | forward/no-cycle/每step一次 | 短途 | L1 | ♻️compiler tests | `NH2-04` | SHA+cycle/duplicate reject PASS+Q8+UTC |
| `NH2-T05` | all legal edges caller可达 | 集成 | L2 | 🆕registry test | `NH2-03/05` | SHA+matrix edge PASS+T-O-381+UTC |
| `NH2-T06` | old pin与new graph共存 | compat/C | L2 | 🔱compat tests | `NH2-07` | SHA+old sequence PASS+Q18+UTC |
| `NH2-T07` | 禁workflow_key/表达式/branch | architecture | L1 | 🆕scan tests | `NH2-08` | SHA+scan EXIT0+T-O-377+UTC |

**台账 D · 收口评估方案与标准**

| 收口目标 | 评估方式 | PASS标准 | 证据形态 |
|---|---|---|---|
| kind-only | NH2-T01/T05 | public resolver不消费mode/media，合法边全可达 | registry dump+tests |
| one shared tail | NH2-T02+definition scan | kind图不复制per-strategy tail | compiled graph digest report |
| deterministic route | NH2-T03/T04 | fact缺失/unknown不选，环/重复拒注册 | unit logs |
| compat | NH2-T06 | old Execution按旧compiled digest跑完 | event/process sequence |
| redlines | NH2-T07 | 零caller key/action_branch/free expression | scan artifact |

- **DoD硬闸**：NH2-T01..T07全PASS；kind definitions激活前完成compat review。
- **NOT-成功识别**：6张图能bootstrap、`resolve_by_key`成功、human_review类比、scatter join复用都不算完成。

### 7.3 `AP-NH3` · Representation history、reacquire 与 actual S05（Q10/Q12/Q20–Q22/Q27）

**台账 A · 工作清单**

| 编号 | lane/类型 | 工作项 | 工作内容（有序子步） | 量 | 复用 | 风险 | Truth |
|---|---|---|---|---|---|---|---|
| `NH3-01` | schema | RepresentationFact | a)字段闭集/version；b)Outcome UoW append；c)UUID/digest refs；d)projection | L | ♻️/🆕 | high | `T-O-392/402`; `M-NH-02` |
| `NH3-02` | history | AcquireDecodeHistory | a)ordinal append；b)step unique；c)path digest；d)recovery read | L | 🆕 | high | `T-O-392` |
| `NH3-03` | sniff | MIME/opaque/OPC | a)保留mismatch；b)ZIP/OPC；c)binary不UTF8；d)declared/verified分账 | M | ♻️ | med | `T-O-378/388` |
| `NH3-04` | PDF fact | Text-layer observation | a)移除literal权威；b)present/absent/encrypted/corrupt；c)观察/能力分码；d)写fact | M | ♻️ | high | `T-O-378/392` |
| `NH3-05` | print fact | Honest print result | a)验证PDF bytes；b)真实profile；c)budget/evidence；d)clean禁止猜 | M | 🆕 | high | `T-O-388/403` |
| `NH3-06` | reacquire | Declared forward path | a)读fact；b)走图边；c)append history；d)无边/重复/try-all失败 | L | ♻️/🆕 | high | `T-O-388/402` |
| `NH3-07` | migration | Policy/actual split | a)旧列隔离；b)new nullable state/digest；c)legacy unverifiable；d)reader audit | L | 🆕 | high | `T-O-390`; `M-NH-01` |
| `NH3-08` | transaction | Seal CAS | a)聚合path/route/strategy；b)Outcome同UoW；c)eligibility；d)replay/conflict | L | ♻️/🆕 | high | `T-O-400` |
| `NH3-09` | propagation | Actual-only chain | a)ProcessCommand；b)Candidate/Snapshot/Gate/child；c)unsealed拒clean；d)traceback ref | L | ♻️ | high | `T-O-390/400` |
| `NH3-10` | replay | 三窗与full_task | a)seal前crash；b)seal后retry；c)full_task exact copy；d)rebuild不bind/upgrade OOS | L | ♻️/🆕 | high | `T-O-401/407` |

**台账 B · reference-anchor 清单**

| 锚 ID | 来源 | 落点 | 借鉴类型 | 处置 | 备注 |
|---|---|---|---|---|---|
| `NH3-A01` | `src/runtime/intake/acquisition_ingest.py:579-676` | 单槽evidence | ⛔反例 | 🆕rows/history | 不覆盖 |
| `NH3-A02` | `src/runtime/intake/types.py:144-220` | sniff+literal PDF | ✅/⛔ | ♻️sniff、替换PDF | 观察/能力分码 |
| `NH3-A03` | `src/runtime/workflow/runtime_outcome.py:88-137` | Outcome UoW | ✅正例 | ✅/♻️ | fact+seal线性点 |
| `NH3-A04` | `src/runtime/task/task_create.py:179-180` | legacy alias | ⛔反例 | 🆕migration | no backfill |
| `NH3-A05` | `src/runtime/task/task_commands.py:237-311` | full_task exact | ✅正例/值错 | ♻️复制new actual | `T-R-NH-23` |
| `NH3-A06` | `src/runtime/intake/clean_preflight.py:46-127` | handler暗dispatch | ⛔反例 | ♻️图绑定 | 未封禁clean |
| `NH3-A07` | RA02/03 external durable-history anchors | replay/representation原理 | 🔶参考 | 🆕关系实现 | 不引Temporal |

**台账 C · 测试用例**

| Test-ID | 验证什么 | 类型 | 层 | 来源 | 映射 | PASS证据 |
|---|---|---|---|---|---|---|
| `NH3-T01` | fact/history append同UoW | 集成/F | L2 | 🆕 | `NH3-01/02` | SHA+rollback/commit PASS+Q12+UTC |
| `NH3-T02` | sniff/OPC/opaque | 短途 | L1 | ♻️/🆕 | `NH3-03` | SHA+fixture suite PASS+Q12+UTC |
| `NH3-T03` | PDF observation不盗码 | 短途 | L1/L2 | ♻️ | `NH3-04` | SHA+present/absent/encrypted PASS+Q13+UTC |
| `NH3-T04` | honest print fact | 集成 | L2 | 🆕 | `NH3-05` | SHA+PDF/profile PASS+Q23+UTC |
| `NH3-T05` | declared reacquire history=2 | 集成 | L2 | 🆕 | `NH3-06` | SHA+path digest PASS+Q8/Q22+UTC |
| `NH3-T06` | legacy/unsealed/sealed三态 | migration | L2 | 🆕 | `NH3-07` | SHA+migration query PASS+Q10+UTC |
| `NH3-T07` | route+seal同UoW | fault | L2/F | 🆕 | `NH3-08/09` | SHA+W-SEL/SEAL PASS+Q20+UTC |
| `NH3-T08` | full_task exact/rebuild旁路 | replay/C | L2 | 🔱task tests | `NH3-10` | SHA+generation matrix PASS+Q21/Q27+UTC |

**台账 D · 收口评估方案与标准**

| 收口目标 | 评估方式 | PASS标准 | 证据形态 |
|---|---|---|---|
| durable facts | NH3-T01/T02/T03 | 每success step一行且rollback无残行 | DB query+fixture digest |
| finite path | NH3-T05 | 两路径digest不同，同路径稳定，重复step拒绝 | history rows+hash |
| actual truth | NH3-T06/T07 | 旧/unsealed/sealed可分，seal同UoW且single-CAS | migration+fault report |
| propagation | integration query | 所有下游只见actual或unsealed，零domain冒充 | cross-table audit |
| retry law | NH3-T08 | full_task复制exact；rebuild无source worker；upgrade无入口 | execution lineage report |
| representation honesty | NH3-T03/T04 | 无盗码、无常量profile、print真PDF | evidence rows |

- **DoD硬闸**：NH3-T01..T08全PASS；`rg` 新domain/wire对旧`s05_binding_digest`零actual读者。
- **NOT-成功识别**：把旧列nullable、domain backfill、单槽JSON、两提交seal、full_task清actual均为失败。

### 7.4 `AP-NH4` · Authenticated upload+stat 与 object lifecycle（Q16/Q24）

**台账 A · 工作清单**

| 编号 | lane/类型 | 工作项 | 工作内容（有序子步） | 量 | 复用 | 风险 | Truth |
|---|---|---|---|---|---|---|---|
| `NH4-01` | storage | Bounded write | a)stream chunks；b)sha/size；c)cap/expected校验；d)atomic promote/staging cleanup | L | ♻️/🆕 | high | `T-O-385/404` |
| `NH4-02` | UoW | Catalog+pending | a)promote成功；b)同UoW catalog+upload_pending ref；c)commit；d)返回handle | L | ✅/♻️ | high | `T-O-404`; `M-NH-05` |
| `NH4-03` | API | Upload+stat routes | a)auth/team；b)upload request；c)stat fields/disposition；d)无path/name/raw GET | M | 🆕 | high | `T-O-396` |
| `NH4-04` | idempotency | Replay/conflict | a)team+digest+size unique；b)并发双传；c)cross-team403；d)tombstone typed | M | ✅/♻️ | high | `T-O-383/385/396` |
| `NH4-05` | handoff | local_object ingest | a)handle输入；b)read_verified；c)Task UoW独立；d)acceptance后业务ref转换 | M | ✅/♻️ | high | `T-O-385/404` |
| `NH4-06` | GC | Pending/grace/quarantine | a)TTL/cancel release；b)candidate scan；c)TX1 quarantine；d)TX2 recheck restore/tombstone | L | ✅/♻️ | high | `T-O-404` |
| `NH4-07` | public fence | No raw read | a)不注册raw route；b)stat不泄path/name；c)artifact read独立；d)architecture scan | S | ✅/♻️ | med | `T-O-396` |
| `NH4-08` | security | Upload negatives | a)filename/path；b)MIME不信；c)unauth/cross-team；d)oversize/digest mismatch；e)零presign/R2 | M | ✅/♻️ | high | `T-O-377/396/404` |

**台账 B · reference-anchor 清单**

| 锚 ID | 来源 | 落点 | 借鉴类型 | 处置 | 备注 |
|---|---|---|---|---|---|
| `NH4-A01` | `src/storage/local_store.py:71-122` | CAS/read_verified | ✅正例 | ✅复用 | promote不等public |
| `NH4-A02` | `src/services/object_gc.py:133-245` | quarantine/recheck | ✅正例 | ✅扩pending | NS6 fence |
| `NH4-A03` | `api/public/routes.py:56-452` | upload/stat=0 | ⛔反例 | 🆕public surface | `T-R-NH-25` |
| `NH4-A04` | `src/storage/ports.py:10-24` | bytes promote Port | 🔶参考 | ♻️bounded stream | 全内存不可public |
| `NH4-A05` | `src/runtime/intake/acquisition_ingest.py:413-455` | local handle read | ✅正例 | ✅handoff | 加catalog/ref fence |
| `NH4-A06` | RA06 WEB TUS/S3/OCI/OWASP | checksum/lease/security | 🔶参考 | 🆕本仓UoW | 不借云key/presign |

**台账 C · 测试用例**

| Test-ID | 验证什么 | 类型 | 层 | 来源 | 映射 | PASS证据 |
|---|---|---|---|---|---|---|
| `NH4-T01` | public upload→handle且零Item | live | L3 | 🆕API e2e | `NH4-01..03` | SHA+HTTP/DB PASS+Q16/Q24+UTC |
| `NH4-T02` | same bytes replay/concurrency | race | L2/L3 | 🆕 | `NH4-04` | SHA+parallel PASS+T-O-383+UTC |
| `NH4-T03` | stat字段/跨team/无raw | 契约/S | L1/L3 | 🆕 | `NH4-03/07/08` | SHA+route/auth PASS+Q16+UTC |
| `NH4-T04` | upload→ingest→retrieval | mega | L3/L4 | 🆕 | `NH4-05` | SHA+handle/query PASS+T-O-385+UTC |
| `NH4-T05` | pending与GC交错 | fault/race | L2/F/R | 🔱GC tests | `NH4-06` | SHA+restore/tombstone PASS+Q24+UTC |
| `NH4-T06` | TTL未ingest回收 | soak | L2 | 🆕fake clock | `NH4-06` | SHA+scanner PASS+T-O-404+UTC |
| `NH4-T07` | oversize/digest/path/MIME | security | L1/L3 | 🆕 | `NH4-08` | SHA+negative suite PASS+Q16+UTC |

**台账 D · 收口评估方案与标准**

| 收口目标 | 评估方式 | PASS标准 | 证据形态 |
|---|---|---|---|
| upload identity | NH4-T01/T02 | commit后同bytes同handle，upload不造S04 identity | HTTP+DB snapshot |
| public boundary | NH4-T03 | upload/stat存在，raw/list/presign=0，跨team403 | route scan+responses |
| ingest handoff | NH4-T04 | upload单独检索空，独立ingest后命中 | Task/query trace |
| GC safety | NH4-T05/T06 | pending不删，release+grace可删，new ref restore | GC proofs |
| bounded security | NH4-T07 | cap/integrity/auth/path全部typed fail | error matrix |

- **DoD硬闸**：NH4-T01..T07全PASS；`FG-NH-10`/public route scan通过。
- **NOT-成功识别**：internal promote、Task inline staging、catalog无ref、raw GET、grace赌竞态均不算完成。

### 7.5 `AP-NH5` · Semantic authority、S06 overlay 与 retrieval facets（Q14/Q15）

**台账 A · 工作清单**

| 编号 | lane/类型 | 工作项 | 工作内容（有序子步） | 量 | 复用 | 风险 | Truth |
|---|---|---|---|---|---|---|---|
| `NH5-01` | API contract | Strict semantic input | a)generic四字段required nonunknown；b)is_active派生；c)API mapper SSOT；d)provenance/conflict422 | L | 🆕 | high | `T-O-394` |
| `NH5-02` | acceptance | Six-tuple gate | a)拒stub/missing；b)写6 rows；c)API regression；d)缺义不得Revision/vector | M | ♻️ | high | `T-O-389/394` |
| `NH5-03` | UoW | Semantic atomicity | a)definition/value/digest；b)blob同源；c)metadata CAS；d)fingerprint | L | ♻️ | high | `T-O-394` |
| `NH5-04` | S06 | System context overlay | a)读S04；b)覆盖五维/tags；c)模型值非权威；d)g0不变 | M | ♻️ | high | `T-O-386/389/394` |
| `NH5-05` | contract | Channel split | a)new双键；b)旧schemaenum adapter；c)deprecation；d)new禁旧/other422 | M | ♻️ | high | `T-O-395`; `M-NH-08` |
| `NH5-06` | projection | Facet rows | a)五维+tags投影；b)definition digest；c)serving revision；d)backfill/migration | L | ♻️ | high | `T-O-389/395`; `M-NH-06` |
| `NH5-07` | retrieval | Typed SQL filters | a)registry keys；b)candidate SQL；c)unknown422；d)禁post-topK filter | M | ✅/♻️ | high | `T-O-395` |
| `NH5-08` | metadata | Semantic refresh | a)inherit clean；b)new six tuple；c)S06/facet切代；d)不clean（交NH8 guard） | M | ✅/♻️ | high | `T-O-394/407` |

**台账 B · reference-anchor 清单**

| 锚 ID | 来源 | 落点 | 借鉴类型 | 处置 | 备注 |
|---|---|---|---|---|---|
| `NH5-A01` | `src/contracts/intake/semantics.py:12-63` | six tuple | ✅正例 | ✅扩四通道 | API样板 |
| `NH5-A02` | `src/runtime/intake/acceptance_snapshot.py:589-615` | source_kind stub | ⛔反例 | ♻️strict gate | `T-R-NH-27` |
| `NH5-A03` | `src/runtime/intake/generation_assemble.py:17-62` | system g0 | ✅正例 | ♻️平行context overlay | 不改g0 |
| `NH5-A04` | `src/runtime/intake/generation_construct.py:330-343` | S06不读semantics | ⛔反例 | ♻️overlay | 模型不权威 |
| `NH5-A05` | `src/services/retrieval/models.py:14-34` | vector channel/3 filters | ⛔反例 | ♻️双键+facets | `T-R-NH-27` |
| `NH5-A06` | RA07 WEB payload/index/filter | facet/query机制 | 🔶参考 | ♻️SQL/sidecar | 不引外部vector DB |

**台账 C · 测试用例**

| Test-ID | 验证什么 | 类型 | 层 | 来源 | 映射 | PASS证据 |
|---|---|---|---|---|---|---|
| `NH5-T01` | generic必填/nonunknown | 契约 | L1 | 🆕 | `NH5-01` | SHA+schema matrix PASS+Q14+UTC |
| `NH5-T02` | API禁自动unknown/冲突 | 契约 | L1/L2 | 🔱provider tests | `NH5-01/02` | SHA+mapper negatives PASS+Q14+UTC |
| `NH5-T03` | acceptance six tuple/no stub | 集成 | L2 | 🆕 | `NH5-02/03` | SHA+DB rows PASS+T-O-389+UTC |
| `NH5-T04` | S06 context=S04且g0=clean | 集成 | L2 | ♻️assemble tests | `NH5-04` | SHA+overlay PASS+Q14+UTC |
| `NH5-T05` | new双channel同请求 | 契约 | L1/L3 | 🆕 | `NH5-05` | SHA+API PASS+Q15+UTC |
| `NH5-T06` | old channel窄迁移/other422 | compat | L1/L3 | 🆕 | `NH5-05` | SHA+legacy schema PASS+Q15+UTC |
| `NH5-T07` | facet命中/排除/unknown | mega | L2/L4 | 🆕 | `NH5-06/07` | SHA+query PASS+T-O-395+UTC |
| `NH5-T08` | metadata切代clean不变 | 集成 | L2/L4 | 🔱metadata tests | `NH5-08` | SHA+digest/facet PASS+Q27+UTC |

**台账 D · 收口评估方案与标准**

| 收口目标 | 评估方式 | PASS标准 | 证据形态 |
|---|---|---|---|
| semantic authority | NH5-T01..T03 | 四kind六元组非stub；generic无unknown；API无自动填空 | schema+DB query |
| S06/g0分账 | NH5-T04 | context逐字等于S04，g0 digest等于clean | structure artifact diff |
| channel contract | NH5-T05/T06 | 新双键共存，旧键仅原枚举，other422 | API responses |
| facets | NH5-T07 | realm等可在候选SQL命中/排除，unknown key失败 | query plan+results |
| metadata | NH5-T08 | new Revision语义切代，clean digest/object不变 | lineage+query |

- **DoD硬闸**：NH5-T01..T08全PASS；`FG-NH-07`与channel compatibility gate通过。
- **NOT-成功识别**：source_kind stub、空context、模型realm、post-filter、按值猜axis、API `or unknown`均为失败。

### 7.6 `AP-NH6` · Local runtime supply、readiness 与安全（Q13/Q19/Q23）

**台账 A · 工作清单**

| 编号 | lane/类型 | 工作项 | 工作内容（有序子步） | 量 | 复用 | 风险 | Truth |
|---|---|---|---|---|---|---|---|
| `NH6-01` | registry | Supply identities | a)parse/render/print/OCR/model caps；b)versions；c)limits；d)readiness keys | M | ♻️/🆕 | high | `T-O-393/403` |
| `NH6-02` | parser | PDF text supply | a)isolated no-net process；b)ToUnicode/compressed；c)limits/kill；d)typed absent/encrypted | L | 🆕 | high | `T-O-399` |
| `NH6-03` | browser | Render supply | a)non-root sandbox；b)S16 egress；c)DOM/profile；d)timeout/cap | L | 🆕 | high | `T-O-399/403` |
| `NH6-04` | browser | Print supply | a)shared binary；b)separate cap/profile；c)PDF evidence；d)budget/readiness | L | 🆕 | high | `T-O-403` |
| `NH6-05` | S11 | Multimodal request | a)PromptRef/model；b)media+digest/handle；c)bounded bytes；d)adapter/probe | XL | ♻️/🆕 | high | `T-O-393` |
| `NH6-06` | OCR/Vision | Capability bindings | a)deterministic vs model classification；b)engine/model pin；c)empty/bad/timeout；d)no cloud/latest | L | 🆕 | high | `T-O-393/399` |
| `NH6-07` | budget | Gates/backpressure | a)cap keys；b)limits；c)full→zero calls；d)metrics | M | ♻️ | med | `T-O-393/403` |
| `NH6-08` | health | Real readiness | a)binary/model/data；b)positive fixture；c)negative fixture；d)component state | M | ♻️/🆕 | high | `T-O-399` |
| `NH6-09` | supply-chain | Pin/SBOM/CVE | a)inventory/license；b)CVE baseline；c)upgrade/rollback；d)owner waiver registry | L | 🆕 | high | `T-O-399` |
| `NH6-10` | wiring | Default root | a)config inject；b)no test mutation；c)startup/readiness；d)typed missing supply | M | ♻️ | high | `T-O-376/399` |

**台账 B · reference-anchor 清单**

| 锚 ID | 来源 | 落点 | 借鉴类型 | 处置 | 备注 |
|---|---|---|---|---|---|
| `NH6-A01` | `src/contracts/inference/models.py:96-108` | text-only request | ⛔反例 | ♻️multimodal | explicit contract |
| `NH6-A02` | `src/runtime/inference/claude_cli.py:505-508` | binary拒绝 | ✅诚实负例 | ✅保持 | 不当OCR fallback |
| `NH6-A03` | `api/app.py:244-266,330-345` | gates/缺注入 | ✅/⛔ | ♻️wiring | `T-R-NH-26` |
| `NH6-A04` | `src/runtime/http_acquisition.py:182-208` | egress policy | ✅正例 | ✅供browser | 每redirect复核 |
| `NH6-A05` | `src/llm_adapters/local_vllm.py:276-295` | models-list probe | ⛔反例 | 🆕实弹probe | 名单不足 |
| `NH6-A06` | RA05 parser/browser/OCR official/advisory | capability+失败法 | 🔶参考 | 🆕local隔离 | 不锁库名 |

**台账 C · 测试用例**

| Test-ID | 验证什么 | 类型 | 层 | 来源 | 映射 | PASS证据 |
|---|---|---|---|---|---|---|
| `NH6-T01` | PDF compressed/CID/absent/encrypted | spike/S | L2/L3 | 🆕 | `NH6-02` | SHA+fixture PASS+Q19+UTC |
| `NH6-T02` | parser无网/资源kill/API存活 | security | L2/S | 🆕 | `NH6-02/09` | SHA+isolation PASS+T-O-399+UTC |
| `NH6-T03` | SPA render真实DOM/profile | live | L3 | 🆕 | `NH6-03` | SHA+browser PASS+Q23+UTC |
| `NH6-T04` | print真PDF/独立budget | live | L3 | 🆕 | `NH6-04` | SHA+PDF PASS+Q23+UTC |
| `NH6-T05` | browser non-root/no-sandbox/egress | security | L2/L3/S | 🆕 | `NH6-03/04/09` | SHA+policy PASS+Q19+UTC |
| `NH6-T06` | multimodal bytes/handle+PromptRef | 集成 | L2/L3 | 🆕 | `NH6-05/06` | SHA+adapter PASS+Q13+UTC |
| `NH6-T07` | OCR/Vision empty/bad/timeout | fault | L1/L2 | 🆕 | `NH6-06` | SHA+typed errors PASS+Q13+UTC |
| `NH6-T08` | backpressure零下游调用 | race | L1/L2/R | ♻️gate tests | `NH6-07` | SHA+metrics PASS+Q13+UTC |
| `NH6-T09` | readiness正负一致 | soak | L2/L3 | 🆕 | `NH6-08/10` | SHA+health PASS+Q19+UTC |
| `NH6-T10` | license/SBOM/CVE/waiver完整 | contract | L1 | 🆕manifest check | `NH6-09` | SHA+inventory EXIT0+Q19+UTC |

**台账 D · 收口评估方案与标准**

| 收口目标 | 评估方式 | PASS标准 | 证据形态 |
|---|---|---|---|
| PDF supply | NH6-T01/T02 | 真提取、typed absent、恶意样本不杀API | process/fixture report |
| browser supply | NH6-T03..T05 | DOM/PDF各自真实，non-root sandbox+egress | profile+security report |
| model supply | NH6-T06/T07 | bytes/handle+PromptRef，空/错不成功 | invocation evidence |
| budget/readiness | NH6-T08/T09 | 满载零调用；component与实际在场一致 | metrics+health snapshot |
| supply trust | NH6-T10 | 每binary/model有pin/license/SBOM/CVE/waiver | signed inventory |
| default wiring | NH6-T03/T04/T06/T09 | create_app无需patch可达供给 | startup+e2e logs |

- **DoD硬闸**：NH6-T01..T10全PASS；`FG-NH-11`和S16 review签收。
- **NOT-成功识别**：import/which/models-list、Protocol fake、root/no-sandbox、cloud OCR、浮动latest、测试后赋port均不算完成。

### 7.7 `AP-NH7` · 10+3 vertical activation（Q17 + foundational live matrix）

**台账 A · 工作清单**

| 编号 | lane/类型 | 工作项 | 工作内容（有序子步） | 量 | 复用 | 风险 | Truth |
|---|---|---|---|---|---|---|---|
| `NH7-01` | matrix | Activation manifest | a)registry生成合法格；b)identity分账；c)非法409/422；d)fixture/test层 | M | ✅/🆕 | med | `T-O-381/405` |
| `NH7-02` | contract | Admitted clean | a)统一nonempty schema；b)digest/evidence；c)LLM加PromptRef；d)API双digest六元组 | M | ✅/♻️ | high | `T-O-386` |
| `NH7-03` | prompt | PromptA alignment | a)canonical catalog；b)旧refs兼容；c)hash校验；d)drift failure | M | ♻️ | high | `T-O-386`; `M-NH-07` |
| `NH7-04` | deterministic | Inline/static lane | a)inline/doc；b)HTTP static；c)PDF-first；d)empty fail；e)publish/query | M | ✅/♻️ | med | `T-O-376/381` |
| `NH7-05` | PDF | Text-layer lane | a)upload/HTTP PDF；b)verified fact；c)pdf.text_layer；d)semantic/tail/query | M | ♻️ | high | `T-O-378/381` |
| `NH7-06` | browser | Render lane | a)declared/static-shell route；b)real DOM；c)web deterministic/LLM；d)query | L | ♻️ | high | `T-O-388/402/403` |
| `NH7-07` | print | Browser-print lane | a)URL→print fact；b)PDF clean；c)no HTML sanitizer；d)query | L | ♻️ | high | `T-O-388/403` |
| `NH7-08` | multimodal | DU/OCR/Vision lanes | a)5 strategies合法表示；b)real binary/model；c)empty fail；d)各自query | XL | ♻️ | high | `T-O-393/399` |
| `NH7-09` | API | 3 operation+zero | a)strict map；b)bad member fail；c)child publication/query；d)exhausted_zero | L | ✅/♻️ | high | `T-O-397` |
| `NH7-10` | product proof | First-publication closure | a)actual S05；b)S04 six tuple；c)g0/S06；d)proof/pointer；e)namespace+facet query | L | ✅/♻️ | high | `T-O-376/389/406` |

**台账 B · reference-anchor 清单**

| 锚 ID | 来源 | 落点 | 借鉴类型 | 处置 | 备注 |
|---|---|---|---|---|---|
| `NH7-A01` | `src/contracts/intake/strategies.py:15-160` | 10 strategy definitions | ✅正例 | ✅生成matrix | 非笛卡尔积 |
| `NH7-A02` | `intake/__init__.py:20-132` | 9 capability dispatch | ✅正例 | ✅保留handlers | 禁重写 |
| `NH7-A03` | `intake/api/registry.py:73-148` | 3 API strict map | ✅正例 | ✅preservation | live fetch OOS |
| `NH7-A04` | `src/runtime/intake/clean_preflight.py:46-127` | process→strategy反推 | ⛔反例 | ♻️actual graph binding | 一process多strategy |
| `NH7-A05` | `src/runtime/intake/vector_publish_commit.py:57-191` | publication tail | ✅正例 | ✅复用 | query仍必需 |
| `NH7-A06` | `tests/e2e/test_source_capability_paths.py:99-101,166-168` | patch/running | ⛔反例 | 🆕default-root tests | `FG-NH-01` |
| `NH7-A07` | `tests/e2e/test_registered_api_scatter.py:209-373` | publication_ready/zero | ✅/⛔ | ♻️加query/disposition | `T-R-NH-24` |

**台账 C · 测试用例**

| Test-ID | 验证什么 | 类型 | 层 | 来源 | 映射 | PASS证据 |
|---|---|---|---|---|---|---|
| `NH7-T01` | matrix/identity/illegal combos | 契约 | L1 | 🆕 | `NH7-01/02` | SHA+matrix PASS+T-O-381+UTC |
| `NH7-T02` | prompt hash/drift/deterministic no-model | 集成 | L1/L2 | 🔱clean tests | `NH7-03/04` | SHA+invocation counts PASS+Q6+UTC |
| `NH7-T03` | inline/static→retrieval | live/mega | L3/L4 | 🔱source e2e | `NH7-04/10` | SHA+query PASS+T-O-376+UTC |
| `NH7-T04` | PDF text→retrieval | live/mega | L3/L4 | 🆕 | `NH7-05/10` | SHA+real PDF query PASS+Q1+UTC |
| `NH7-T05` | browser DOM→retrieval | live/mega | L3/L4 | 🆕 | `NH7-06/10` | SHA+SPA query PASS+Q23+UTC |
| `NH7-T06` | print PDF→retrieval | live/mega | L3/L4 | 🆕 | `NH7-07/10` | SHA+print query PASS+Q23+UTC |
| `NH7-T07` | 5 multimodal strategies | live/mega | L3/L4 | 🆕 | `NH7-08/10` | SHA+5 lanes PASS+Q13/Q19+UTC |
| `NH7-T08` | 3 API members→query | live/mega | L3/L4 | 🔱scatter e2e | `NH7-09/10` | SHA+3 operation query PASS+Q1+UTC |
| `NH7-T09` | exhausted_zero独立disposition | 集成/mega | L2/L4 | 🔱zero test | `NH7-09` | SHA+zero/proof/metrics PASS+Q17+UTC |
| `NH7-T10` | empty/bad member/worker failure零向量 | fault | L1/L3/L4 | ♻️/🆕 | `NH7-02/08/09` | SHA+negative query PASS+T-O-383+UTC |

**台账 D · 收口评估方案与标准**

| 收口目标 | 评估方式 | PASS标准 | 证据形态 |
|---|---|---|---|
| 10+3合法矩阵 | NH7-T01..T09 | 每合法格至少一L3+L4正例，非法格fail | manifest+test map |
| clean contract | NH7-T02/T10 | 正文非空，evidence/digest/PromptRef适用且失败零向量 | clean artifacts |
| source lanes | NH7-T03..T07 | default root无patch，从真实input到query | Task/Process/query trace |
| API lanes | NH7-T08/T09 | 每operation member命中；zero独立且零产物 | child proof+result |
| semantic/publication | NH7-T10 + cross-query | actual/S04/g0/S06/proof/pointer/facet可回溯 | evidence chain |
| fake-green | scan+L3/L4 | 无503/patch/empty/publication flag顶替 | FG report |

- **DoD硬闸**：NH7-T01..T10全PASS；10+3 manifest无waiver覆盖foundational completeness。
- **NOT-成功识别**：33 unit、函数/图存在、503、Task succeeded、publication_ready、无namespace query均不算live。

### 7.8 `AP-NH8` · 七意图、exact-clean、publication lifecycle 与 compat（Q21/Q25/Q27）

**台账 A · 工作清单**

| 编号 | lane/类型 | 工作项 | 工作内容（有序子步） | 量 | 复用 | 风险 | Truth |
|---|---|---|---|---|---|---|---|
| `NH8-01` | contract | 七意图applicability | a)合法输入/state/terminal；b)422/409 code；c)admission拒绝；d)不建Task | M | ✅/🆕 | high | `T-O-405` |
| `NH8-02` | graph | Rebuild exact-clean | a)intent guard旁路；b)读frozen artifact；c)零acquire/decode/clean；d)digest exact | L | ♻️ | high | `T-O-401/407` |
| `NH8-03` | metadata | No-change/changed | a)no-change短路；b)changed new Revision；c)inherit clean；d)semantic/tail切代 | L | ✅/♻️ | high | `T-O-394/407` |
| `NH8-04` | lifecycle | deactivate/reactivate/delete | a)withdraw同UoW；b)reactivate不restore；c)delete tombstone；d)query negatives | M | ✅/♻️ | high | `T-O-405` |
| `NH8-05` | index | index.rebuild | a)active scope；b)new generation；c)无Revision/source/clean；d)stale排除 | M | ✅ | med | `T-O-405/407` |
| `NH8-06` | API Item | Shared lifecycle | a)API item target；b)同single services；c)无child kernel；d)七意图测试 | L | ♻️ | high | `T-O-405` |
| `NH8-07` | compat | Old/new retirement | a)old pin跑完；b)new Task kind-only；c)telemetry；d)有界retire/rollback | L | ✅/♻️ | high | `T-O-398/401`; `M-NH-04` |
| `NH8-08` | lineage | Restart/rebuild matrix | a)Process/full_task exact；b)rebuild clean replay；c)index untouched；d)upgrade入口=0 | M | ♻️ | high | `T-O-401/407` |

**台账 B · reference-anchor 清单**

| 锚 ID | 来源 | 落点 | 借鉴类型 | 处置 | 备注 |
|---|---|---|---|---|---|
| `NH8-A01` | `src/contracts/api/models.py:278-286` | 七意图闭集 | ✅正例 | ✅扩applicability | 不做28格 |
| `NH8-A02` | `src/runtime/intake/acquisition_intents.py:25-93` | frozen clean input | ✅正例 | ✅复用 | 现图仍reclean |
| `NH8-A03` | `src/runtime/intake/clean_preflight.py:28-127` | rebuild再clean | ⛔反例 | ♻️guard bypass | 禁no-op worker |
| `NH8-A04` | `src/services/intake_lifecycle/lifecycle_apply.py:34-134` | withdraw/reactivate | ✅正例 | ✅复用 | 加L4 query |
| `NH8-A05` | `src/runtime/intake/index_rebuild_plan.py:23-32` | index generation | ✅正例 | ✅复用 | 无Revision |
| `NH8-A06` | `src/runtime/task/task_commands.py:237-311` | full_task exact | ✅正例 | ♻️复制new actual | upgrade OOS |

**台账 C · 测试用例**

| Test-ID | 验证什么 | 类型 | 层 | 来源 | 映射 | PASS证据 |
|---|---|---|---|---|---|---|
| `NH8-T01` | 七意图合法/非法code | 契约 | L1/L2 | 🆕matrix | `NH8-01` | SHA+422/409 PASS+Q25+UTC |
| `NH8-T02` | rebuild零source/process且clean exact | 集成/mega | L2/L4 | 🔱rebuild e2e | `NH8-02` | SHA+process/query PASS+Q27+UTC |
| `NH8-T03` | metadata no-change/changed | 集成/mega | L2/L4 | 🔱metadata e2e | `NH8-03` | SHA+revision/digest/facet PASS+Q27+UTC |
| `NH8-T04` | deactivate→query empty | live | L3/L4 | 🔱lifecycle tests | `NH8-04` | SHA+withdraw/query PASS+Q25+UTC |
| `NH8-T05` | reactivate仍empty直到publish | live | L3/L4 | 🔱reactivate e2e | `NH8-04` | SHA+pointer/query PASS+Q25+UTC |
| `NH8-T06` | delete tombstone/rebuild conflict | live | L3/L4 | 🆕e2e | `NH8-04` | SHA+409/query PASS+Q25+UTC |
| `NH8-T07` | index.rebuild同正文新generation | live/compat | L3/L4 | 🔱index e2e | `NH8-05` | SHA+generation/query PASS+Q25+UTC |
| `NH8-T08` | API Item七意图 | mega | L3/L4 | 🆕 | `NH8-06` | SHA+API lifecycle PASS+Q25+UTC |
| `NH8-T09` | old pin/new kind共存 | compat | L2/C | 🔱compat tests | `NH8-07` | SHA+old/new sequence PASS+Q18+UTC |
| `NH8-T10` | full_task/rebuild/index/upgrade矩阵 | replay | L2/C | 🆕 | `NH8-08` | SHA+lineage PASS+Q21/Q27+UTC |

**台账 D · 收口评估方案与标准**

| 收口目标 | 评估方式 | PASS标准 | 证据形态 |
|---|---|---|---|
| applicability | NH8-T01 | 非法格admission拒绝且零Task/Process | API/DB audit |
| exact-clean | NH8-T02/T03 | rebuild/metadata零clean Process，artifact/digest exact | process query+hash |
| lifecycle | NH8-T04..T08 | pointer/serving/vector/query与状态一致，single/API同法 | transition+query pack |
| index rebuild | NH8-T07 | 新generation、零Revision/source/clean、旧代不命中 | pointer/vector rows |
| compat | NH8-T09 | old pin完成、新Task只kind graph | execution sequences |
| restart law | NH8-T10 | full_task exact；upgrade入口0；rebuild/index分账 | restart ledger |

- **DoD硬闸**：NH8-T01..T10全PASS；`M-NH-09`及compat retirement review签收。
- **NOT-成功识别**：no-op cleaner、仅DB状态、reactivate恢复旧serving、28格、existing upgrade混入retry/rebuild均为失败。

### 7.9 `AP-NH9` · Closed-set assurance 与 immutable closure evidence（Q26）

**台账 A · 工作清单**

| 编号 | lane/类型 | 工作项 | 工作内容（有序子步） | 量 | 复用 | 风险 | Truth |
|---|---|---|---|---|---|---|---|
| `NH9-01` | manifest | Closed-set generator | a)读registries；b)合法格；c)预期path/actual/semantic/query/negative；d)冻结digest | L | 🆕 | high | `T-O-381/406` |
| `NH9-02` | replay | Task/intake/concurrent create | a)same replay；b)different409；c)double-flight；d)object refs | M | ✅/♻️ | high | `T-O-383` |
| `NH9-03` | fail-loud | Bad-input matrix | a)empty/bad media/member；b)unknown keys；c)missing supply；d)negative query | L | ✅/♻️ | high | `T-O-378/383` |
| `NH9-04` | crash | W-window injection | a)CREATE/SEL/SEAL；b)PROCESS/FANIN；c)PUB/OUTBOX；d)effect-once | XL | ♻️/🆕 | high | `T-O-400/406` |
| `NH9-05` | object race | Upload/GC | a)parallel upload；b)pending/TTL；c)quarantine+newref；d)tombstone/reupload | L | ✅/♻️ | high | `T-O-404` |
| `NH9-06` | scatter | zero/member/child/fanin | a)exhausted；b)bad member；c)child fail；d)crash repair；e)query | L | ✅/♻️ | high | `T-O-397` |
| `NH9-07` | compat | Old pin+actual | a)old graph；b)new graph；c)unknown digest；d)legacy alias不当actual | L | ✅/♻️ | high | `T-O-390/398/401` |
| `NH9-08` | product | Retrieval-facet mega | a)每knowledge格；b)namespace；c)proof/trace/facet；d)stale/lifecycle排除 | XL | ✅/♻️ | high | `T-O-376/389/406` |
| `NH9-09` | security | Runtime closure | a)missing deps；b)malicious PDF/URL；c)backpressure；d)SBOM/CVE/waiver | L | ♻️ | high | `T-O-399/406` |
| `NH9-10` | evidence | Immutable pack | a)commit；b)test/query outputs；c)fixture/migration digests；d)waivers；e)UTC | M | 🆕 | med | `T-O-406` |
| `NH9-11` | experiment | Readiness skeleton | a)matrix/run schema；b)preflight；c)日期/分数空；d)不进closure join | S | ♻️ | low | `T-O-380` |

**台账 B · reference-anchor 清单**

| 锚 ID | 来源 | 落点 | 借鉴类型 | 处置 | 备注 |
|---|---|---|---|---|---|
| `NH9-A01` | `src/runtime/task/task_create.py:67-140` | fingerprint/CAS | ✅正例 | ✅扩新路径 | conflict负测缺 |
| `NH9-A02` | `src/runtime/workflow/runtime_outcome.py:46-182` | process fence/retry | ✅正例 | ✅fault windows | actual新接 |
| `NH9-A03` | `src/runtime/workflow/runtime_scatter.py:320-474` | fan-in/child proof | ✅正例 | ♻️Port/query | sqlite反例另测 |
| `NH9-A04` | `src/services/retrieval/retrieval_rank.py:38-76,339-433` | dual fence | ✅正例 | ✅mega | facets来自NH5 |
| `NH9-A05` | `tests/e2e/test_source_capability_paths.py:99-101,166-168` | patch/running | ⛔反例 | 🆕L3 | 不修期待值 |
| `NH9-A06` | legacy catch/empty/R2 finalizer | silent success | ⛔反例 | 🆕negative grids | 零runtime回流 |
| `NH9-A07` | RA09 Temporal/Kafka/DST anchors | replay/EOS/fault limits | 🔶参考 | ♻️本仓CAS/fixtures | 不引外部引擎 |

**台账 C · 测试用例**

| Test-ID | 验证什么 | 类型 | 层 | 来源 | 映射 | PASS证据 |
|---|---|---|---|---|---|---|
| `NH9-T01` | manifest覆盖82 works/10+3/七意图 | 契约 | L1 | 🆕 | `NH9-01` | SHA+manifest EXIT0+Q26+UTC |
| `NH9-T02` | Task/intake replay/conflict | race | L2/L3 | 🔱identity tests | `NH9-02` | SHA+parallel PASS+T-O-383+UTC |
| `NH9-T03` | empty/bad/unknown零向量 | fault | L1/L3/L4 | ♻️/🆕 | `NH9-03` | SHA+negative query PASS+Q3+UTC |
| `NH9-T04` | CREATE/SEL/SEAL/PROCESS windows | fault | L2/F | 🆕 | `NH9-04` | SHA+window suite PASS+Q20+UTC |
| `NH9-T05` | FANIN/PUB/OUTBOX windows | fault | L2/L4/F | 🔱e2e | `NH9-04/06` | SHA+repair/proof PASS+Q26+UTC |
| `NH9-T06` | upload/GC interleavings | race/soak | L2/L3/R | 🔱NH4 tests | `NH9-05` | SHA+interleavings PASS+Q24+UTC |
| `NH9-T07` | zero/member/child failure | mega | L3/L4 | 🔱scatter | `NH9-06` | SHA+result/query PASS+Q17+UTC |
| `NH9-T08` | old pin/new graph/legacy alias | compat | L2/C | 🔱compat | `NH9-07` | SHA+sequence PASS+Q10/Q18+UTC |
| `NH9-T09` | every live lane retrieval/facet | mega | L4 | 🔱NH7 | `NH9-08` | SHA+manifest query PASS+Q26+UTC |
| `NH9-T10` | security/readiness/backpressure | security/soak | L2/L3/S | 🔱NH6 | `NH9-09` | SHA+security pack PASS+Q19+UTC |
| `NH9-T11` | evidence pack completeness | contract | L1 | 🆕checker | `NH9-10` | SHA+pack checker EXIT0+T-O-406+UTC |

**台账 D · 收口评估方案与标准**

| 收口目标 | 评估方式 | PASS标准 | 证据形态 |
|---|---|---|---|
| closed-set coverage | NH9-T01 | manifest含82 works、全部合法格/负格/层级 | manifest digest |
| replay/fault | NH9-T02/T04/T05 | 所有W-window deterministic、无双effect/热切 | fault report |
| object/scatter | NH9-T06/T07 | races不丢bytes/不假Item，zero/child语义正确 | DB/proof/query |
| compat | NH9-T08 | old pin可完结，legacy alias不当actual | execution audit |
| product closure | NH9-T03/T09 | 每应产知识格query+trace+facet，失败格零命中 | mega report |
| security closure | NH9-T10 | isolation/readiness/SBOM/CVE/backpressure全门通过 | security signoff |
| evidence immutability | NH9-T11 | 每AP四元组齐、waiver合规、UTC/commit固定 | evidence pack |

- **DoD硬闸**：NH9-T01..T11全PASS；`FG-NH-01..17`全绿；无未解释S1/过期waiver。
- **NOT-成功识别**：NH9第一次补功能、降低测试层、experiment/0815/live vendor顶替、口头exactly-once均为失败。

---

## 8. Owner decision gates —— gate-closure map `[核心]`

| gate | 冻结 Q / Truth | 下游唯一口径 | 状态 |
|---|---|---|---|
| `G-NH-01` | Q10 / `T-O-390` | policy/actual分账，旧列隔离不backfill，new actual唯一SSOT | `CLOSED` |
| `G-NH-02` | Q11 / `T-O-391` | optional-port registered selected-output CONTROL，exactly-one | `CLOSED` |
| `G-NH-03` | Q12 / `T-O-392` | typed fact/history rows同Outcome UoW、唯一权威 | `CLOSED` |
| `G-NH-04` | Q13 / `T-O-393` | local binary ports vs model-bound S11 multimodal | `CLOSED` |
| `G-NH-05` | Q14 / `T-O-394` | generic nonunknown required；API mapper SSOT；禁自动unknown | `CLOSED` |
| `G-NH-06` | Q15 / `T-O-395` | semantic/vector channel分名，旧schema窄迁移 | `CLOSED` |
| `G-NH-07` | Q16 / `T-O-396` | public upload+stat，无raw GET | `CLOSED` |
| `G-NH-08` | Q17 / `T-O-397` | 独立exhausted_zero、零产物、非indexed success | `CLOSED` |
| `G-NH-09` | Q18 / `T-O-398` | 有界Workflow substrate留NH1–NH3 | `CLOSED` |
| `G-NH-10` | Q19 / `T-O-399` | parser/OCR无网隔离；browser禁no-sandbox；supply门 | `CLOSED` |
| `G-NH-11` | Q20 / `T-O-400` | route+actual+eligibility同Outcome UoW | `CLOSED` |
| `G-NH-12` | Q21 / `T-O-401` | full_task exact；rebuild clean replay；existing upgrade OOS | `CLOSED` |
| `G-NH-13` | Q22 / `T-O-402` | decode main_text_presence三态，unknown fail-closed | `CLOSED` |
| `G-NH-15` | Q23 / `T-O-403` | browser共享binary，render/print分capability | `CLOSED` |
| `G-NH-16` | Q24 / `T-O-404` | catalog+upload_pending同UoW后返回handle | `CLOSED` |
| `G-NH-17` | Q25 / `T-O-405` | 七意图非法格admission fail，不建Task/Process | `CLOSED` |
| `G-NH-18` | Q26 / `T-O-406` | 四层不可互换，waiver只延期 | `CLOSED` |
| `G-NH-19` | Q27 / `T-O-407` | rebuild/metadata intent guard旁路clean | `CLOSED` |

- **结论**：18/18 owner gates CLOSED；`G-NH-14` 保持故意空号（promptA 对齐为执行项），设计阶段无 OPEN 决策，可派生 action-plan。

---

## 9. 测试计划（长程 capstone + evidence pack）`[核心]`

### 9.1 分层与固定测试面

- **A 短途**：各 AP 的 L1 contract/unit、registry、digest、schema、architecture scans。
- **B spike/integration**：L2 UoW/migration/CAS/fault；NH1 chosen-shape、NH3 seal、NH4 GC、NH6 supply。
- **C default-root**：L3 `create_app()`、auth/public routes、真实local binary/model；成功路径零monkeypatch。
- **D mega**：L4 namespace+proof+pointer+serving+traceback+facet；每个知识格必须真实query。
- **固定文件路径**：manifest `tests/fixtures/new_harvest/closed_set_manifest.v1.json`；capstone `tests/e2e/test_new_harvest_closed_set.py`；fault `tests/e2e/test_new_harvest_crash_windows.py`；security `tests/e2e/test_new_harvest_runtime_security.py`。

### 9.2 长程 capstone A–J

| 步 | 场景 | 必证结果 |
|---|---|---|
| A | bootstrap/migration/old pin | old Execution可跑，新Task kind-only，legacy alias不可当actual |
| B | public upload+stat | handle/digest/size/pending，无Item、无raw GET |
| C | inline/static/PDF | deterministic+真text layer到query，空/无层分码 |
| D | browser/print | SPA DOM与PDF print分capability到query，无常量profile |
| E | OCR/Vision/DU | real binary/model、PromptRef、isolation/readiness到query |
| F | registered API | 三operation member query；bad member fail；exhausted_zero零产物 |
| G | semantics | generic strict五维、API mapper、S06 overlay、双channel/facet |
| H | lifecycle | rebuild/metadata exact-clean；deactivate/reactivate/delete/index.rebuild query法 |
| I | replay/crash/race | CREATE/SEL/SEAL/PROCESS/FANIN/PUB/OUTBOX/GC deterministic |
| J | closure | 82 work IDs、L1–L4、FG-NH-01..17、waiver/SBOM/migrations evidence齐 |

### 9.3 Evidence pack 与 DoD

每 AP 产出 `docs/evidence/new-harvest/AP-NHn/`（后续 action-plan 冻结 exact filenames），至少包含：

1. `manifest.json`：commit、Truth/Q、work/test IDs、UTC；
2. `tests.txt`：node IDs、exit code、duration、environment；
3. `queries/`：DB/API/retrieval result与预期；
4. `migrations/`：before/after schema、legacy rows、forward-only proof；
5. `security/`：适用的pin/SBOM/CVE/readiness/waiver；
6. `closure.md`：台账 D逐目标PASS/FAIL与NOT-success扫描。

Campaign DoD = 九个 AP 台账 C全PASS + 台账 D逐项有四元组证据 + capstone A–J全PASS + 无过期waiver/未解释S1。实验发车不在DoD。

---

## 10. 风险登记 `[核心]`

| 风险 | 触发 | 影响 | 缓解 |
|---|---|---|---|
| `R-F01` chosen merge不可行 | NH1零/双命中或compile失败 | 全DAG阻塞 | STOP/reopen，不准duplication |
| `R-F02` 旧s05被误backfill | migration按64hex判断 | 假lineage | legacy unverifiable+reader scan |
| `R-F03` fact/history双SSOT | output JSON与row并存 | route/replay漂移 | row唯一权威，引用-only architecture test |
| `R-F04` old pin绞杀 | 退役旧key/plan过早 | in-flight 409 | compat suite+telemetry+有界retire |
| `R-F05` runtime供应链失败 | license/CVE/binary不可部署 | NH6/NH7阻塞 | NH1 smoke、owner waiver仅延期、替代需reopen |
| `R-F06` browser安全降级 | root/no-sandbox或绕egress | SSRF/逃逸 | S16 hard gate+L3 security test |
| `R-F07` upload误删/泄漏 | 无pending或staging无scanner | 数据丢失/磁盘泄漏 | T-O-404+GC interleavings |
| `R-F08` unknown回流 | caller/mapper自动填 | facet假完整 | schema nonunknown+source scan |
| `R-F09` channel双义 | 同schema按value猜 | query错误 | versioned adapter+422 |
| `R-F10` tail被按lane复制 | vertical开发越界 | proof法分叉 | graph/tail architecture scan |
| `R-F11` rebuild偷reclean | no-op/deterministic worker | digest/actual漂移 | intent guard+process absence test |
| `R-F12` full_task清actual | 以new generation为由 | retry热切 | T-O-401+lineage suite |
| `R-F13` L1替代L3/L4 | 环境困难/耗时 | 假绿 | T-O-406+waiver仅延期 |
| `R-F14` Task/flag顶替query | 沿用旧e2e | 产品终态未证 | namespace L4 mandatory |
| `R-F15` NH9垃圾桶化 | 前AP跳负测 | 末期返工 | 每AP DoD硬闸，不首测功能 |
| `R-F16` scope滑向existing upgrade/connector | 临时需求 | 新状态/intent爆炸 | OOS硬围栏+新owner-gate |

---

## 11. 后继解锁 + action-plan 派生图 `[核心]`

- **解锁价值**：九份 action-plan 可直接从冻结 Truth、DAG、四台账派生，不再需要 owner 选型；后续可把四通道从合同/局部函数水位推进到真实、可过滤、可回放的知识生产闭集。

### 11.A action-plan 派生与排序

| AP簇 | 派生 action-plan 文件 | 台账ID区间 | 时序/依赖 |
|---|---|---|---|
| `7.1 AP-NH1` | `docs/plan/new-harvest/AP-NH1-foundation-contracts-and-proof-baseline.md` | `NH1-01..09 / NH1-A01..06 / NH1-T01..07` | `1`；全链首门，fail→reopen |
| `7.2 AP-NH2` | `docs/plan/new-harvest/AP-NH2-workflow-kind-family-and-merge.md` | `NH2-01..08 / NH2-A01..06 / NH2-T01..07` | `2`；依NH1；与NH4/NH5并行 |
| `7.3 AP-NH3` | `docs/plan/new-harvest/AP-NH3-representation-history-and-s05-binding.md` | `NH3-01..10 / NH3-A01..07 / NH3-T01..08` | `3`；依NH2；与NH4/NH5并行 |
| `7.4 AP-NH4` | `docs/plan/new-harvest/AP-NH4-public-upload-and-object-lifecycle.md` | `NH4-01..08 / NH4-A01..06 / NH4-T01..07` | `2P`；NH1后并行；NH7 local lane前join |
| `7.5 AP-NH5` | `docs/plan/new-harvest/AP-NH5-semantic-ledger-and-retrieval-facets.md` | `NH5-01..08 / NH5-A01..06 / NH5-T01..08` | `2P`；NH1后并行；NH7前join |
| `7.6 AP-NH6` | `docs/plan/new-harvest/AP-NH6-local-runtime-supply-and-security.md` | `NH6-01..10 / NH6-A01..06 / NH6-T01..10` | `4`；依NH3，和NH4/NH5尾部并行 |
| `7.7 AP-NH7` | `docs/plan/new-harvest/AP-NH7-clean-capability-activation.md` | `NH7-01..10 / NH7-A01..07 / NH7-T01..10` | `5`；join NH2/3/5/6，local格另需NH4 |
| `7.8 AP-NH8` | `docs/plan/new-harvest/AP-NH8-intake-lifecycle-and-compatibility.md` | `NH8-01..08 / NH8-A01..06 / NH8-T01..10` | `6`；依NH7/NH5 |
| `7.9 AP-NH9` | `docs/plan/new-harvest/AP-NH9-closed-set-assurance.md` | `NH9-01..11 / NH9-A01..07 / NH9-T01..11` | `7`；join NH4/NH8/all evidence |

> **路径纪律**：上述路径与ID冻结；下游文件头部必须引用本 final、对应Truth区间与四台账，不能重命名/重编号后丢traceability。

---

## 12. Final recommendation `[核心]`

- **推荐序列**：`NH1 → (NH2→NH3→NH6 ∥ NH4 ∥ NH5) → NH7 → NH8 → NH9`。
- **一句话总结**：先证明和建成不可热切的图/事实/binding地基，再并行补字节入口、语义与真实runtime，以10+3 vertical query收敛，最后只用race/crash/compat/evidence关闭战役。

---

## 13. 交叉引用与修订历史 `[可选]`

- **上游**：[`initial-planning.md`](initial-planning.md) · [`proposed-planning.md`](proposed-planning.md) · [`pre-charter-qna.md`](pre-charter-qna.md) · [`reference-anchor/`](reference-anchor/)
- **Truth calibration**：S03/S05/D04/S13/S16/glossary/qna-truth-S05（`T-O-390..407`）。
- **下游**：§11.A 九份 action-plan。

| 版本 | 日期 | 作者 | 主要变更 |
|---|---|---|---|
| `v1.0` | `2026-08-29` | GPT | 冻结版：全态Truth+6条final HEAD实测；critique proposed；9 AP×4台账；18 gate closure；capstone/evidence pack；9份action-plan派生图 |
