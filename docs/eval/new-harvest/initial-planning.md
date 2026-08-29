# new-harvest —— 初步规划（planning · 站① initial）by Grok

> **stage**：`initial`（站①·开放/速写）
> **作者**：`Grok`（panel：`none`）· **时间**：`2026-08-29`
> **本链 scope-fence**：阶段族 `new-harvest` 下 `intake-four-channel-live` 链站①；**本链覆盖** 把四域清洗通道（`pdf` / `web` / `doc` / `api`）按已冻 foundational 真相接到真实 intake → 真实 Process → 可检索向量；**不含** live 供应商爬虫、第五 source kind、cuts/g0 算法重开、前端、CF/SMCP 栈、实验发车日。
> **文档性质（自宣告）**：设计流程**第①步**；不是 charter、不是 action-plan，**本文件冻结零决策**（仅 CITE 已在 `pre-initial-planning-qna` 冻结的 foundational 真相，见 §2）。文中相位、DAG、AP 切分、工作项、业务簇边界均为 **first-cut / 初判 / 待核**，供后续 executional QNA 与 `planning-proposed` 裁定。**禁止**把本节任何模块名、库选型、`step_key`、HTTP 路径、谓词字面、purpose 字符串读成已冻结。
> **上游权威输入**：[`pre-initial-planning-qna.md`](pre-initial-planning-qna.md) v0.5 `frozen`（`T-O-376..389`）；[`initial-thoughts-by-grok.md`](initial-thoughts-by-grok.md) v0.3；[`initial-thoughts-by-GLM53f.md`](initial-thoughts-by-GLM53f.md) v0.1；HEAD 代码事实；`docs/baseline/**`（D08 Appendix A 不得当今日绿灯）
> **下游消费者**：[[planning-proposed]]（站②，将裁定本文）；后续拟派生 ≥2 份 `docs/plan/new-harvest/*` action-plan（**尚未写、尚未冻结**）
> **phase 命名 & 工作项 ID 方案**：相位 `NH1`–`NH5`；工作项 `NH{n}-01…`（跨态稳定；本态可增补编号，不回收）
> **文档状态**：`draft`

---

## 0. TL;DR `[核心]`

- **核心论点**：new-harvest 的施工对象不是「再写四个清洗器」，而是把已经冻死的产品法——四通道 live-to-vector、三轴、声明式 kind 图、绑定前有限再获取、S13 上传窄 reopen、同一 admitted clean / g0、四通道五维分账——铺成 **可被事实核查的业务簇** 和 **可被后续冻结执行细节的相位 DAG**。HEAD 的 7 张公开 profile、字面量 PDF、从不写 `print_pdf` 的 acquire、创建时即写死的 `s05_binding_digest`、无公网上传、web/pdf 的 FilterMeta stub，都是这些产品法的反面现场，而不是可保留的默认实现。
- **一句话**：先改「图怎么选工人」，再改「字节怎么进门与怎么被看见」，再改「工人怎么真的洗出 clean」，最后把语义和向量尾接上并证明闭集。
- **本态已锚定的 foundational 真相**：有。`pre-initial-planning-qna` 已收口 `T-O-376..389`。本文件只 CITE，不自冻，不把 QNA §10.2 的执行延期项提前冻成方案。

---

## 1. Reference anchors / 输入与依据 `[核心]`

| 输入 | 类型 | 提供了什么 | 锚点 |
|------|------|------------|------|
| `pre-initial-planning-qna.md` v0.5 | `pre-initial-qna / frozen` | 战役产品法闭集；`T-O-376..389`；冲突和解 8 条；执行延期表 §10.2 | 全文；台账 L74–L95；收口 L787–L819 |
| `initial-thoughts-by-grok.md` v0.3 | `eval` | HEAD 缺口、遗产对照、F1–F8 功能清单；**部分取舍已被 QNA 修订**（见 §3） | 尤其 A.2 / B / C / D.5–D.7 |
| `initial-thoughts-by-GLM53f.md` v0.1 | `eval` | 「合同面完备、执行面一个半通道」；decode 后路由决策点 | §0 TL;DR；§2.1 评级 |
| HEAD `intake/` + `src/workflows/lsrag_definition.py` + `src/contracts/workflow/models.py` | `HEAD` | 12 张图、守卫闭集、无环编译器、假 PDF 层、无上传面 | 见各簇「待核现场」 |
| `D08-legacy-capabilities-migration.md` / `S03-workflow-engine.md` / `S05-intake-cleaning.md` / `S13-artifact-storage.md` / `D05-layered-semantic-rag-handbook.md` | `baseline` | 三轴、七表、无公网 object API、promptA/B/C、FilterMeta | 只 CITE 已冻与已校准条文 |
| `context/legacy-family/` | `ReferenceAnchor` | 6 条 `action_branch` 事前选抓取器；dedicated FilterMeta；空成功反例 | `T-O-42`：借语义不借栈 |
| NS9 / 0815-R7 closure | `closure` | 生成面已能吃 admitted clean；R7 4/4 **不是**四通道接通 | `T-O-376` 明文 |

- **纪律继承**：NS 战役的「合同 ≠ done、禁止假绿、禁止 silent skip、retry 不热切图」。new-harvest **不**另起 worker / 状态机 / identity 表。
- **借用骨架**：无同族 `planning-final` 可抄；本文件按 `.adocs/templates/planning-initial.md` 自填。Grok F1–F8 与 GLM 三件事是 **待裁定的 eval**，不是相位真源。

---

## 2. 规划真相台账（Planning Truth Register · 站①）★ `[核心]`

> **Module① · 本态真相切片**。**CITE 已冻结真相，不自冻**。`T-O` 全文以 QNA §1 为准；下表是规划索引。`T-P` 是本态猜想，**未冻结**，待事实核查 / proposed 证实或证伪。

### 2.1 已冻结真相（CITE · 截至本态）

| Truth-ID | 类型 | 子类型 | 真相内容（一句话） | 来源（冻结权威） | 对本链的约束 |
|----------|------|--------|--------------------|------------------|---------------|
| `T-O-376` | `owner-gated` | `foundational / completeness` | 四通道全部接通，禁止诚实未部署；真实文件→真实 Process→可检索向量；NH 不重写 cuts/g0，但必须送到现有 publication/retrieval | QNA Round 1 确认 | 定 §4 In；503 不得当通道 DoD |
| `T-O-377` | `owner-gated` | `foundational / fence` | 零 CF/SMCP 栈；四类 source kind；`intake/` 是变换 SSOT；禁 `action_branch` | QNA 围栏 | 接通 ≠ 搬 Workers |
| `T-O-378` | `owner-gated` | `foundational / honesty` | 字面量 PDF 不得称落地；无层死在 decode 并盗用 OCR 码是谎言；monkeypatch e2e 不是接线；空 `clean_text` 不是成功 | QNA + HEAD | 假实现必须换真路径；本条是谎言清单不是「decode 必须失败」 |
| `T-O-379` | `owner-gated` | `foundational / three-axis` | 坐标 = `source_kind × acquire × clean_strategy`；调用方不得点名 `workflow_key` | QNA；S05 §1.3 | 动态路由 ≠ 开放选图。取值时刻见 `T-O-387/388/382` |
| `T-O-380` | `owner-gated` | `foundational / experiment-schedule` | unit/e2e 属于 completeness；**.experiment 发车日不在 QNA 冻结** | QNA | 本链可筹备实验骨架，不得把发车日写成 DoD |
| `T-O-381` | `owner-gated` | `foundational / live-matrix` | 10 个 `CleanStrategyKey` + `clean.map.registered_api` 三 operation 均 live-to-vector；公共上传必须落地；七意图纳入；不含 live 爬虫 / 第五 kind / cuts / 前端 | QNA Q1-B | 公开选图闭集必须覆盖该矩阵 |
| `T-O-382` | `owner-gated` | `foundational / late-bind` | 清洁工人在真实表示已知之后按可配置闭集规则绑定；进 evidence 与 digest；禁无证据暗升 | QNA Q2-B | 不是 `T-O-340` 静默换工人；绑定后 `T-O-383` |
| `T-O-383` | `owner-gated` | `foundational / fail-loud-after-bind` | 绑定后不再换清洁工人；内容失败不出向量；Task/intake replay 与 ConflictError；空正文非成功；上传服从同一套幂等 | QNA Q3-A | 路径能出向量 ≠ 每个坏文件必须出 |
| `T-O-384` | `owner-gated` | `foundational / declarative-late-bind` | 同一 immutable revision 预声明全部 live clean 边；仅登记 guard/control 选边；`s05_binding_digest` 选边后封闭；retry 不热切图 | QNA Q4-A | 张数已由 `T-O-387` 闭合；禁表外 `dispatch_clean` |
| `T-O-385` | `owner-gated` | `foundational / upload-identity` | 上传只创造 S13 handle+digest（窄 reopen 无公网 object API）；不创造 Item；随后另一次 ingest；重复字节 replay 同一 handle | QNA Q5-A | 对象存在 ≠ 业务成功；purpose 字面本文件不锁 |
| `T-O-386` | `owner-gated` | `foundational / clean-contract` | 四通道同一份 admitted clean body 供 S06/g0；promptA 仅 `llm_required`；API/确定性仍是 clean；不为通道另写 structurize kernel | QNA Q6-A | 窄执行解释 `T-O-210`，不是废除 handbook |
| `T-O-387` | `owner-gated` | `foundational / graph-cardinality` | 选图键 = 四类 source_kind；三张 single-root + scatter 独立；mode/media 不再选图 | QNA Q7-A | 非法跨 kind 边不画；5 张选不中的图必须并进对应 kind revision |
| `T-O-388` | `owner-gated` | `foundational / reacquire-envelope` | `acquisition_mode` 是起点；绑定前可走有限、已声明、无环、正向再获取；decode 只观察；print_pdf 必须诚实；digest 覆盖实际 acquire 路径 | QNA Q8-A | 依赖 kind 图；禁暗升与 try-all-acquire |
| `T-O-389` | `owner-gated` | `foundational / semantic-ledger` | g0 original 只等于 clean body；五维+tags 作为 S04 revision semantics 四通道强制；禁止写入 g0；stub 不得冒充五维 | QNA Q9-A | 派生算法不锁；缺五维不得 acceptance-complete |

上游被 QNA 显式和解、本链必须遵守但不在本文件重冻：`T-O-42`、`T-O-62`、`T-O-208`/`210`/`352`、`T-O-340`、`S03-T007/T011/T012/T013/T017/T038/T053`、`S05-T002`、D08-T007、S13 完成定义第 7 条（已被 `T-O-385` 窄 reopen）。

### 2.2 暂定前提（Provisional · 待 proposed 证实/证伪）

| Truth-ID | 暂定前提（一句话） | 依据强度 | 待核方向（喂 reference-anchor / 事实核查） |
|----------|--------------------|----------|--------------------------------|
| `T-P-NH-1` | 本链 first-cut 切成 **五个相位** `NH1`–`NH5`，关键路径 NH1→NH3→NH4→NH5，NH2 与 NH3 可在 NH1 之后并行 | `叙事` | 核查 kind 图未落地时上传面能否独立开工；核查清洁工人是否必须等表示诚实 |
| `T-P-NH-2` | 拟派生 **五份** action-plan，与相位 1:1（`AP-NH1`…`AP-NH5`）；不按 pdf/web/doc/api 各写一份 AP | `叙事` | 核查 `http_resource` 一张图是否会让「按通道拆 AP」必然重复改同一 revision |
| `T-P-NH-3` | 业务核查单元是 **七个内聚簇**（附录 A），相位是簇的施工顺序而不是簇的同义词 | `叙事` | 后续事实核查按簇发，不按相位发 |
| `T-P-NH-4` | PDF「真文本层」需要替换 `local-pdf-literal-text.v1`；**用哪一个库本态不选** | `低 / HEAD 已证假实现` | `src/runtime/intake/types.py:144-171`；许可证/隔离待 execution QNA |
| `T-P-NH-5` | browser acquire 需要真实渲染端口注入组合根；**二进制与驱动本态不选** | `低 / HEAD 未注入` | `api/app.py:330-345` 组合根只注入 `http_fetcher`/`claude_cli`，无 browser/clean_llm；`acquisition_ingest.py:535-536` 假 `browser_profile` |
| `T-P-NH-6` | OCR / Vision / promptA 运输复用已有推理面，不新开第四调度池；**模型与运行时本态不选** | `叙事 / 继承 NS2 三池` | `strategies.py` `llm_required`；S11 现有端口 |
| `T-P-NH-7` | FilterMeta 四通道强制后，值来自「调用方 typed 元数据 ∪ 闭集派生」；算法本态不锁 | `QNA 明文不锁` | `acceptance_snapshot.py:576-614` stub；`registry.py:229-239` 已登记五维 |
| `T-P-NH-8` | 上传 purpose 须进入 S13 闭集，**字符串本态不锁** | `QNA 明文不锁` | `S13-artifact-storage.md` purpose 闭集 |
| `T-P-NH-9` | 晚绑定守卫是 **扩展登记谓词**（`eq` only），不是自由表达式；**谓词字面本态不锁** | `T-O-384` + HEAD 闭集 | `models.py:245-258`；`runtime_materialize.py:110-113` 缺键 fail-closed |
| `T-P-NH-10` | promptA 三套默认 id 必须对齐才能让 LLM 策略 live；**对齐方案本态不锁** | `HEAD 已知分叉` | `strategies.py:57-65` vs 文档/snapshot 默认 id |
| `T-P-NH-11` | `.experiment` 族可在 NH5 备骨架；发车日仍 OPEN（`T-O-380`） | `QNA` | 不得把 0815-R7 inline 4/4 算四通道接通 |
| `T-P-NH-12` | charset / canonical digest 合同版本若要动，属于执行；本态只记下它会碰到 revision 指纹 | `GLM eval` | decode `utf8-lf-nfc.v1`；改合同 = 新 digest 版本，不是暗改 |
| `T-P-NH-13` | `s05_binding_digest` 从 Task 创建推迟到清洁边选定，是晚绑定的实现后果，不是新的产品法 | `QNA 和解 #4` | `src/runtime/task/task_create.py:176-180` vs `S03-T017/T053` |
| `T-P-NH-14` | NH3 内部可以按 kind 图分工作流（http vs local vs api），但它们仍是 **同一 AP** 的工作项，不是三份 AP | `叙事 / 服从 T-O-387` | 核查 scatter_child 是否应单列工作项 |

---

## 3. 辨证审核（整合裁定原始 eval / owner 提案）★ 承重段 `[核心]`

> 站①承重梁。裁定动词：`纳入 / refine / 不纳入`。无 Δ-vs-plan 表。

| 来源项（eval / owner 提案） | 整合裁定 | 落到哪个 phase | 受约束真相（Truth-ID） | 备注 |
|------|----------|----------------|---------------------|------|
| 业主目标 1：完整建设 pdf/web/doc/api | `纳入` | NH3 主体 + NH4 贯通 | `T-O-376`/`381` | 「完整」= live-to-vector 闭集，不是 7 profile |
| 业主目标 2：状态机与通道真实接线 | `纳入` | NH1 关键路径 | `T-O-384`/`387`/`388` | 接线 = kind 图上看得见工人，不是调用方点名图 |
| 业主目标 3：边缘、路由、错误 | `纳入` | NH1 守卫 + NH3 表示 + NH5 失败法 | `T-O-382`/`383`/`388` | 边缘走已声明边；绑定后 fail-loud |
| 业主目标 4：unit/e2e + 实验通路 | `refine` | NH5；发车日 **不**进相位 DoD | `T-O-376`/`380` | 测试属于 completeness；发车日仍 OPEN |
| 业主 2026-08-29：不存在诚实未部署 | `纳入` | 全链 | `T-O-376` | 作废 grok/GLM 的 503-as-DoD |
| 业主：真实文件→真实向量；上传/CRUD/幂等/竞态 | `纳入` | NH2 上传；NH4 七意图；NH5 CAS | `T-O-381`/`383`/`385` | 上传 ≠ Item |
| Grok F1 Web 通道 | `refine` | NH3 | `T-O-381`/`388` | 纳入 deterministic/llm_rewrite/browser；**删除**「无注入则 503 即完整」；暗升仍禁，**声明式再获取纳入** |
| Grok F2 PDF 通道 | `纳入` | NH3 | `T-O-378`/`381`/`388` | 真文本层 + understanding/OCR + 诚实 print_pdf |
| Grok F3 Doc 通道 | `refine` | NH3 | `T-O-376`/`381` | 「缺引擎稳定拒绝」改为必须 live，不得 503 收口 |
| Grok F4 API fixture 合同 | `纳入` | NH3 / NH4 | `T-O-381`/`386` | live fetch **不纳入**（仍 caller-frozen records） |
| Grok F5「扩展 profile 键选图」 | `不纳入`（方案）/ `refine`（问题） | NH1 | `T-O-387` | 问题仍在（选不中的图）；方案改为 kind 家族，不再扩 12 profile |
| Grok F6 边缘错误闭集 | `纳入` | NH3 / NH5 | `T-O-378`/`383` | 无层与 OCR 未部署必须分码 |
| Grok F7 测试分层 | `refine` | NH5 | `T-O-376` | 默认进程 **无 monkeypatch** 的成功路径，不是「默认 503 + 另测注入」 |
| Grok F8 实验骨架 | `纳入`（骨架） | NH5 | `T-O-380` | 发车令不纳入 |
| Grok 取舍 3「禁止 static→browser 自动升级」 | `refine` | NH1 / NH3 | `T-O-388` | **暗升**仍禁止；**已声明正向边**的再获取是已冻产品法 |
| GLM「合同一个半通道 live」 | `纳入`（现状判断） | — | `T-O-378` | 作为缺口分母，不是方案 |
| GLM decode 后显式 route 决策点 | `纳入`（产品法已冻） | NH1 | `T-O-382`/`384` | 落点是七表 guard，不是表外策略包 |
| GLM charset 盲区 | `refine` | 执行 OPEN（`T-P-NH-12`） | — | 不升格 foundational；改合同必须新版本 |
| GLM / Grok：live 税局爬虫、cookie、第五 kind | `不纳入` | — | `T-O-377`/`381` | 业主 C 已否 |
| 重开 cuts/g0 / 按通道分 structurize kernel | `不纳入` | — | `T-O-376`/`386` | publication 只接通 |
| 表外 `dispatch_clean` / decode 后换 revision | `不纳入` | — | `T-O-384` | Q4-B/C 已否 |
| 前端 | `不纳入` | — | `T-O-381` | |

**整合后的一句话裁定**：eval 里「按通道写四个清洗器 + 扩 profile」这条路，被 foundational 真相改写成「先有 kind 图与晚绑定信封，再让四个通道的工人作为图上已声明的边 live」。Grok 的 F1–F8 作为 **能力闭集清单** 仍有用，作为 **选图方案** 已过期。

---

## 4. 范围与非范围（In/Out-Scope · 提案态）`[核心]`

> **范围模态 = 提案/条件式**（非冻结边界）。服从 `T-O-376` / `T-O-381`。

**In-Scope**

- **[S1] 10 个 `CleanStrategyKey` + `clean.map.registered_api` 三 operation live-to-vector** — 每条用真实文件 / 真实 URL / 冻结 records 走到可检索向量（`T-O-376`/`381`）
- **[S2] 声明式 kind 家族图与晚绑定信封** — 三张 single-root + scatter 独立；预声明边；登记 guard；digest 选边后封闭；绑定前有限再获取；decode 观察（`T-O-384`/`387`/`388`）
- **[S3] 公共对象上传** — 受鉴权 S13 handle；随后 ingest；幂等 replay（`T-O-385`）
- **[S4] 同一 admitted clean / g0；promptA 仅 LLM 策略；不为通道另写 S06 kernel**（`T-O-386`）
- **[S5] 四通道 FilterMeta 五维 + tags 进 S04 revision semantics，不进 g0**（`T-O-389`）
- **[S6] Task 七意图 + 已有 Team/Task/gate/retrieval 公共面对四通道真实对象走通**（`T-O-381`）
- **[S7] 绑定后 fail-loud、CAS/replay/ConflictError、空正文非成功，覆盖新路径与上传**（`T-O-383`）
- **[S8] unit + 无 monkeypatch 默认进程的 e2e 覆盖闭集**（`T-O-376`）；实验骨架可筹备（`T-O-380`）

**Out-of-Scope / 延后**

- **[O1] live 供应商爬虫 / 隧道 / cookie / 任意请求头** — `T-O-377`/`381`；重评：另开连接器战役
- **[O2] 第五 source kind / `action_branch` taxonomy / 调用方点名 `workflow_key`** — `T-O-377`/`379`；重评：never（除非推翻 QNA）
- **[O3] cuts/g0 算法重开、按通道分 structurize kernel** — `T-O-376`/`386`；重评：生成面另役
- **[O4] 前端** — `T-O-381`；重评：独立 FE 战役
- **[O5] 实验发车日** — `T-O-380`；重评：owner 令，不由本文给出
- **[O6] PDF 库 / 浏览器二进制 / OCR 引擎 / purpose 字面 / 谓词枚举 / HTTP 形状 / charset 版本** — QNA §10.2；重评：execution QNA 或 proposed 的 `T-O` execution 门
- **[O7] 把 scatter 折进 mega 单图** — `T-O-387` + `S03-T013`；重评：never
- **[O8] 存量 0815 harness 债、Q 通道超时** — NS9 deferred；重评：生成面波次，不阻塞 NH 闭集证明

---

## 5. 跨阶段贯穿主题（threaded themes · 初判）`[可选]`

- **技术路线红线**：三轴不回流 `action_branch`；晚绑定只走已声明无环边；表示必须诚实；g0 与 FilterMeta 分账；publication 只接通不重写。
- **治理冻结面**：本文件 **不**冻执行。已冻的只有 QNA `T-O`。下一扇门是 executional 细节（库、谓词字面、purpose、digest 推迟的物理写法）。
- **migration 初判**：不是平行系统。HEAD 12 张 profile 图、字面量 PDF、假 `browser_profile`、创建时 `s05_binding_digest`、无上传、FilterMeta stub，都是要在本链内被 **替换为真路径** 的现状，而不是要双轨保留的兼容层。编号待 proposed pin。
- **切分红线（初判）**：**不要按 pdf/web/doc/api 拆相位或拆 AP。** `http_resource` 一张图同时承载 web 策略与 `web.browser_print_pdf`（进 pdf 通道）；`local_object` 一张图同时承载 pdf/doc/image。按通道拆 AP 会让两份计划改同一张 immutable revision。通道是 **闭集验收格子**，不是 **内聚施工边界**。内聚边界是附录 A 的七簇。

---

## 6. DAG（关键路径 + 并行窗 · 初判）`[核心]`

> 初判，待事实核查与 proposed pin。箭头表示「产品法依赖」，不是已经排好的日历。

```text
                    ┌─▶ NH2 上传身份 ──────────────────────────┐
NH1 图与晚绑定信封 ─┤                                          ├─▶ NH4 语义分账 + publication 贯通 ─▶ NH5 失败法与闭集证明
                    └─▶ NH3 表示诚实 + 清洁工人 live ──────────┘
                              ▲
                              └── NH3 的 pdf/doc 真文件 e2e 依赖 NH2 公共上传；
                                  NH3 的 unit/fixture 路径不必等 NH2。

关键路径：NH1 → NH3 → NH4 → NH5
并行窗：NH1 之后，NH2 ∥ NH3（表示/工人）
scatter 不另开相位：跟在 NH1 的 registered_api 图义务里，工人在 NH3，语义在 NH4。
```

**为什么是这个顺序（辨证，非冻结）**

1. **NH1 必须最先。** 今日选不中的 5 张图、单 clean 步骤、创建时冻死 digest，会让后面任何「注入 OCR」都打不进可配置路由（`T-O-382`/`384`/`387`）。没有 kind 图，Q8 的再获取也没有画布。
2. **NH2 不需要等清洁工人。** 上传只创造 handle（`T-O-385`）。它需要的是：S13 Port 可暴露、幂等语义与 `T-O-383` 一致。它 **不**需要 OCR。pdf/doc 的「真实文件」e2e 需要它。
3. **NH3 必须在 NH1 之后。** 工人必须是图上已声明的边。表示诚实（decode 观察、`print_pdf`、真文本层）是守卫的 typed 事实来源（`T-O-388`）。把「表示」和「工人」放同一相位，是因为 print-pdf 是 **获取表示 + PDF 清洁** 的同一条产品路径，拆开会让 AP 对不齐 `T-O-381` 的一格。
4. **NH4 必须在 NH3 能产出 admitted clean 之后。** g0 等于该 body（`T-O-386`）；五维不能塞进还不存在的 clean（`T-O-389`）。publication 尾已存在，本相位是 **接通** 不是重写。
5. **NH5 最后。** 证明闭集、无 monkeypatch e2e、新路径 CAS。若提前写 e2e，会被迫 monkeypatch（与 `T-O-378` 对打）。

**拟派生 AP 职能（初判，1:1 相位）**

| 拟 AP | 职能（一句话） | 主簇 | 不负责 |
|-------|----------------|------|--------|
| `AP-NH1` | 把选图从 12 profile 收成 kind 家族，并让晚绑定/再获取住在七表里 | 图与晚绑定 | 不选 PDF 库、不注入浏览器 |
| `AP-NH2` | 把公共上传做成 S13 handle 面 | 公共上传 | 不写 IntakeItem、不定 HTTP 字面 |
| `AP-NH3` | 让表示诚实，并让 10+3 工人真的产出 admitted clean | 表示与再获取 + 清洁工人 | 不改 cuts、不按通道另写 S06 |
| `AP-NH4` | 四通道五维分账，并接到现有 B/C/向量/检索与七意图 | 语义分账 + publication | 不重开生成面 |
| `AP-NH5` | 把失败法盖到新路径上，并用无 monkeypatch 测试证明闭集 | 失败法与证明 | 不下令实验发车 |

若事实核查证明 `http_resource` 与 `local_object` 的工人变更可以无损分仓，proposed 可以把 `AP-NH3` 拆成两个 **同相位** 工作流，而不是新开 NH6。本态 **不**做该拆分。

---

## 7. 逐 phase 工作台账 —— first-cut（初判，待 pin）`[核心]`

> 台账模态 = first-cut：给候选工作项命名 + 粗估，**defer** 详细测试文件名、库、`step_key`。规模/风险是讨论值。涉及模块是 HEAD 现址，待 pin。

### 7.1 NH1 · 图与晚绑定信封

| 编号 | 工作项 | 涉及模块（初判，待 pin） | 规模 | 风险 | 受约束真相 |
|------|--------|-------------------------|------|------|--------------------|
| `NH1-01` | 公开选图改为四类 `source_kind`（scatter 仍独立） | `workflow_registry.py`；`config_snapshots.py:492-516`；`lsrag_definition.py:929-940` | `M` | `high` | `T-O-387`/`379` |
| `NH1-02` | 每张 kind 图预声明该 kind 全部 live acquire/decode/clean 边；5 张选不中的图并入 | `lsrag_definition.py:881-1054`；`BUILTIN_SOURCE_PROFILE_WORKFLOWS` | `L` | `high` | `T-O-384`/`381`/`387` |
| `NH1-03` | 登记守卫谓词扩展点（表示类事实）；operator 仍 `eq`；缺键 fail-closed | `models.py:245-258`；`runtime_materialize.py:86-117` | `M` | `med` | `T-O-384`；`S03-T012` |
| `NH1-04` | decode 改为观察器：无层/空壳是 typed 事实，停止盗用 OCR 不可用码 | `types.py:144-171`；decode process 合同 | `M` | `high` | `T-O-378`/`388` |
| `NH1-05` | `s05_binding_digest` 在清洁边选定后一次封闭，覆盖实际 acquire 路径；retry 不热切 | `task_create.py:176-180`；runtime materialize | `M` | `high` | `T-O-384`/`388`；`S03-T017/T053` |
| `NH1-06` | 正向再获取边的图位置（不同 `step_key`、无环、每边至多一次） | `lsrag_definition.py` routes；`models.py:389-432` | `M` | `med` | `T-O-388`；`S03-T011` |

### 7.2 NH2 · 公共上传身份

| 编号 | 工作项 | 涉及模块（初判，待 pin） | 规模 | 风险 | 受约束真相 |
|------|--------|-------------------------|------|------|--------------------|
| `NH2-01` | 受鉴权公共上传：只返回 handle+digest+size | `api/public/routes.py`（今日无 objects）；`ObjectStorePort.promote` | `M` | `med` | `T-O-385`/`381` |
| `NH2-02` | 同 team + sha256+size replay 同一 handle；冲突 typed | S13 catalog unique | `S` | `med` | `T-O-383`/`385` |
| `NH2-03` | purpose 进入闭集（**字面 OPEN**）+ 无 ingest 走 orphan/GC | S13 purpose / GC | `S` | `low` | `T-O-385` |
| `NH2-04` | 证明上传不创造 Source/Item/Revision；随后 `local_object` ingest 才有身份 | S04 acceptance | `S` | `med` | `T-O-385`；S04 |

### 7.3 NH3 · 表示诚实 + 清洁工人 live

| 编号 | 工作项 | 涉及模块（初判，待 pin） | 规模 | 风险 | 受约束真相 |
|------|--------|-------------------------|------|------|--------------------|
| `NH3-01` | 真 PDF 文本层（替换字面量扫描）；无层不空成功、不盗用 OCR 码 | `types.py:144-171`；`intake/pdf` | `L` | `high` | `T-O-378`/`381` |
| `NH3-02` | 组合根注入缺失的获取/清洁端口（browser / clean_llm / OCR-Vision 运输） | `api/app.py:330-345` | `M` | `high` | `T-O-376`/`381` |
| `NH3-03` | browser acquire 写出诚实 `representation_kind`；删除假 `injected-browser-renderer.v1` | `acquisition_ingest.py:535-536` | `M` | `high` | `T-O-378`/`388` |
| `NH3-04` | print_pdf 作为已声明获取表示产出 PDF bytes，再晚绑 `web.browser_print_pdf` | `clean_preflight.py:46-62`；D08-T009 | `M` | `med` | `T-O-381`/`388` |
| `NH3-05` | 10 策略 + API 三 operation 产出同一份 admitted clean（非空、digest、evidence） | `intake/{web,pdf,doc,api}`；`strategies.py` | `L` | `high` | `T-O-381`/`386` |
| `NH3-06` | promptA 仅挂 `llm_required` 策略；确定性/API map 用策略 digest 进 binding | `strategies.py:47-65` | `S` | `med` | `T-O-386` |
| `NH3-07` | HTTP 字节嗅探 vs 声明 media：PDF 压过 HTML 洗；图像不得当 web deterministic | `config_snapshots.py:504-506`；`clean_preflight.py` | `S` | `med` | `T-O-379`/`387` |
| `NH3-08` | API 空集/重复/坏 member 类型化结局，禁止 silent skip；仍 caller-frozen records | `intake/api`；scatter | `M` | `med` | `T-O-381`/`383` |

### 7.4 NH4 · 语义分账 + publication 贯通

| 编号 | 工作项 | 涉及模块（初判，待 pin） | 规模 | 风险 | 受约束真相 |
|------|--------|-------------------------|------|------|--------------------|
| `NH4-01` | 四通道 acceptance 写五维 + tags；废除 `{"source_kind"}` stub 冒充 | `acceptance_snapshot.py:576-614`；`registry.py:229-239` | `M` | `med` | `T-O-389` |
| `NH4-02` | 保证 g0 original = admitted clean body；FilterMeta 不进 clean_text / g0 summary | S06/S07 现链；`layered_content.py:17-28,121` | `M` | `med` | `T-O-386`/`389`/`352` |
| `NH4-03` | 每条接通路径送到现有 structurize→construct→vectorize→publication→retrieval | 现 LS-RAG 尾；`api/public/routes.py` retrieval | `M` | `med` | `T-O-376`/`381` |
| `NH4-04` | 七意图对四通道真实对象达到各自产品终态（rebuild/metadata/deactivate/…） | Task intents；S04 lifecycle | `M` | `med` | `T-O-381` |

### 7.5 NH5 · 失败法与闭集证明

| 编号 | 工作项 | 涉及模块（初判，待 pin） | 规模 | 风险 | 受约束真相 |
|------|--------|-------------------------|------|------|--------------------|
| `NH5-01` | 新通道 + 上传覆盖 Task 指纹 replay、intake 同键同 digest replay、ConflictError | `task_create.py`；NS9-FX2 | `M` | `med` | `T-O-383` |
| `NH5-02` | 绑定后内容失败 / 空正文不出向量；不得遍历工人或遍历 acquire | clean 失败路径 | `S` | `med` | `T-O-383`/`388` |
| `NH5-03` | 闭集每条 unit + **默认进程无 monkeypatch** 的 e2e 到向量或生命周期终态 | `tests/e2e/test_source_capability_paths.py` 现状是反例 | `L` | `high` | `T-O-376`/`378`/`381` |
| `NH5-04` | 实验通路骨架（格子、预检、不可变 run）；**发车日空着** | `.experiment/` 形态参考 0815 | `M` | `low` | `T-O-380` |

---

## 8. Owner decision gates —— 开放 gates `[核心]`

> 已冻结 foundational gate **不**重列。下列全部 `OPEN`，供后续 executional 冻结，不是本文件裁决。

| 编号 | 决策点 | 影响 | 当前建议 / 倾向 | 状态 |
|------|--------|------|------------------|------|
| `G-NH-1` | PDF 真文本层用什么本地库、如何隔离恶意输入 | NH3-01 可施工性、许可证、进程风险 | 倾向「有库、失败 typed、进 pyproject」；**不选具体库** | `OPEN` |
| `G-NH-2` | browser 渲染端口的实现与二进制 | NH3-02/03；SPA / print_pdf | 倾向本地注入、不搬 CF Browser Rendering；**不选驱动** | `OPEN` |
| `G-NH-3` | OCR / Vision 是否复用同一 LLM 端口、模型是谁 | NH3-05 扫描件/图片格 | 倾向不新开第四池（`T-P-NH-6`）；**不绑模型名** | `OPEN` |
| `G-NH-4` | 守卫谓词的登记名与 `expected_value` 字面 | NH1-03 与图编译 | 倾向闭集扩展 + `eq`；例（`text_layer_present`）**不是提案冻结** | `OPEN` |
| `G-NH-5` | 再获取边的具体 `step_key` / CONTROL 是否单独一步 | NH1-06 图形状 | 倾向不同 step、无环；**不锁名字** | `OPEN` |
| `G-NH-6` | 上传 HTTP 路径、multipart、purpose 字符串 | NH2 公共面 | 倾向 CAS unique 已够幂等分母；**不锁路径** | `OPEN` |
| `G-NH-7` | FilterMeta 四通道值如何派生 | NH4-01 调用方合同 | 倾向「缺值不得 acceptance」已冻，算法后锁 | `OPEN` |
| `G-NH-8` | promptA 目录 id 三套如何对齐 | NH3-06 LLM 策略一接就可能 hash mismatch | 倾向单一 canonical id；**不锁正文版本** | `OPEN` |
| `G-NH-9` | charset 合同是否在本战役升版本 | 中文 web 乱码 vs revision 指纹稳定 | 倾向若改则新 version，禁止暗改 `utf8-lf-nfc.v1` 语义 | `OPEN` |
| `G-NH-10` | L3 `profile_id` 允许名单如何改写 | 动态配置的团队层 | 倾向规则住在 compiled revision；仍禁 `workflow_key` | `OPEN` |
| `G-NH-11` | `.experiment` 发车日 | NH5-04 是否变成 live 分数 | **不倾向本文件给出日期**（`T-O-380`） | `OPEN` |
| `G-NH-12` | 相位/AP 是否保持 5 份 1:1 | 下游 action-plan 数量 | 本态倾向保持；事实核查后可在 proposed 调整 | `OPEN` |
| `G-NH-13` | PDF 页在一个 Item 内如何拼接 | 不重开 scatter | 倾向仍一个 Item 一份 clean body；拼接算法后锁 | `OPEN` |

---

## 9. 测试计划（概要）`[可选]`

> 概要，不锁测试文件名。服从 `T-O-376`：测试属于 completeness，不是附加优惠。

- **A 短途**：NH1 图编译（无环、kind 选图、非法边不存在、digest 选边后封闭）；NH2 上传幂等；decode 无层分码。
- **B spike**：单条路径（例如 local PDF 有层 / 无层→OCR）从真实文件打到检索，用来验证关键路径，不是闭集证明。
- **D mega**：`T-O-381` 矩阵每格 unit + 默认进程无 monkeypatch e2e 到向量或生命周期终态。0815-R7 inline 4/4 **不得**列入本矩阵。实验发车（`T-O-380`）不是本概要的退出条件。

反例（规划时就要避开）：`tests/e2e/test_source_capability_paths.py` 对 browser **monkeypatch**、对 OCR 断言失败关闭——这是 `T-O-378` 点名的假接线，不能当 NH DoD。

---

## 10. 风险登记 `[核心]`

| 风险 | 触发 | 影响 | 缓解（初判，非冻结） |
|------|------|------|----------------------|
| 按通道拆 AP 改同一张 kind 图 | 习惯「pdf 一组、web 一组」 | 两份计划热切同一 revision，打破 `S03-T007` | 本态把施工边界定在簇/相位，通道只当验收格子 |
| NH3 在 NH1 前注入端口 | 急于「先把 OCR 跑起来」 | 工人在、选不中，回到 5 张死图 | DAG 把 NH1 放关键路径头 |
| 再获取做成 while | 把「有限」读成「直到非空」 | 复活 Q3-B，与 `T-O-383`/`S03-T011` 冲突 | 边必须静态画出；每边一次 |
| digest 仍在 Task 创建写死清洁工人 | 少改 `task_create.py` | 晚绑定无法成为事实 | 遵守和解 #4：创建冻图，选边后封闭 s05 digest |
| 上传即 Item | 图省事 | 失败 OCR 留下 Intake 身份 | `T-O-385`：两步 |
| FilterMeta 塞进 clean_text | 让模型「看见」元数据 | 破坏 g0 digest 与 `T-O-389` | 双账本；acceptance 缺五维失败 |
| monkeypatch e2e 冒充接通 | 浏览器难装 | 假绿，重演 `T-O-378` | NH5 DoD 写死默认进程无补丁 |
| PDF 库 / 浏览器引入攻击面或体积否决 | 选型阶段 | 卡住 NH3 | 失败 typed + 隔离；选型 OPEN，不在本文赌 |
| 范围滑向「能洗全网」 | SPA 登录、反爬 | 无边 | O1 硬砍 |
| 把 0815 发车日写成 NH 完成 | 想要分数 | 违反 `T-O-380` | 骨架可做，日期空着 |

---

## 11. 后继解锁 + 下游链意图声明 `[核心]`

- **解锁的下游价值**：S06 开始能吃非 inline 的真 clean；四通道真实对象可检索；上传后 rebuild 能复用 handle；0815 族可从 documentation inline 升级为源适配 dogfood（**另令发车**）。
- **★ 下游链意图（省略/停链须在此预告）**：
  - `[x]` **满三态**：→ [[planning-proposed]] → [[planning-final]] → 派生 ≥2 action-plan；
  - `[ ]` **省略 proposed**：initial → final；
  - `[ ]` **停链转 charter**：initial → re-planning → charter。

  **理由**：本态只 CITE foundational，执行门（`G-NH-1`…）全 OPEN；附录 A 的七簇还要做事实核查。省略 proposed 会把 first-cut DAG 误当成冻结方案。拟派生 AP 数 ≥2（本态倾向 5，待 proposed pin）。

- **建议的下一跳（不冻结）**：先对附录 A 七簇做事实核查（HEAD + 遗产 + 规格是否支持本态内聚切分），再开 executional QNA 锁 `G-NH-*` 中挡施工的项，再写 `planning-proposed`。

---

## 12. 交叉引用与修订历史 `[可选]`

- **交叉引用**：上游 [`pre-initial-planning-qna.md`](pre-initial-planning-qna.md)；eval [`initial-thoughts-by-grok.md`](initial-thoughts-by-grok.md)、[`initial-thoughts-by-GLM53f.md`](initial-thoughts-by-GLM53f.md)；下游尚未创建的 `planning-proposed`
- **修订历史**：

| 版本 | 日期 | 作者 | 主要变更 |
|------|------|------|----------|
| v0.1 | 2026-08-29 | Grok | 初稿：CITE `T-O-376..389`；七簇详论；NH1–NH5 first-cut DAG 与拟 AP 职能；冻结零决策 |

---

## 附录 A · 业务簇详论（供后续事实核查）

> 本附录是站①的 **讨论对象**，不是冻结边界。事实核查应逐簇回答：「内聚是否成立？HEAD 现场是否如所引？遗产对照是否只借语义？与已冻 `T-O` 有无实际冲突？」  
> **簇 ≠ 相位 ≠ AP。** 簇是产品法内聚；相位是施工顺序；AP 是拟派生执行册。

### A.0 为什么不按四通道分簇

业主口中的「通道」是验收格子：`pdf/web/doc/api`（`T-O-381`）。代码里它们交叉：

- `web.browser_print_pdf` 的 **channel 字段是 `pdf`**，acquire 却是 `http_browser`（`strategies.py:67-76`）。
- `http_resource` 一张 kind 图必须同时看得见 static/browser/print 与 web 策略（`T-O-387` + `T-O-388`）。
- `local_object` 一张图同时看得见 pdf/doc/image。
- g0、FilterMeta、publication、七意图、上传，都不是某一通道私有。

若按通道分簇，晚绑定、digest 封闭、再获取、上传身份会被复制四次，事实核查也会四次问同一张 S03 图。故本态按 **产品法底物** 分七簇；通道作为 NH3/NH5 的 **验收矩阵行**。

---

### 簇 1 · 图与晚绑定信封

- **一句话**：Task 创建只按 `source_kind` 拿到一张 immutable 程序；这张程序已经画出该 kind 全部合法 acquire/decode/clean 边；表示已知之后，登记 guard 选一条清洁边，然后封闭 `s05_binding_digest`。
- **冻结真相**：`T-O-379`、`T-O-382`、`T-O-384`、`T-O-387`、`T-O-340`（显式决策 ≠ 静默换）；上游 `S03-T007/T011/T012/T017/T038/T053`。
- **HEAD 待核现场**：
  - 每张图一个 acquire、一个 decode、一个 clean：`lsrag_definition.py:307-314, 913-924`
  - 公开 7 键、另 5 张选不中：`929-940` vs `1003-1054`
  - 选图 = kind×mode×media：`config_snapshots.py:492-516`
  - 调用方不能点名 `workflow_key`：`workflow_registry.py:84-88`
  - 守卫看不见表示，缺键 fail-closed：`models.py:245-258`；`runtime_materialize.py:110-113`
  - 创建即写 `s05_binding_digest`：`task_create.py:176-180`
  - 图必须无环、禁止自边：`models.py:389-432`；`S03-T011`
  - admission 后 CONTROL `human_review` 已是「决策点 → 已画出的下游」：`lsrag_definition.py:151-153, 366-374`
- **遗产**：`action_registry.ts:91-148` 用一条 branch **事前**选定抓取器与是否 AI。借「分叉存在」，不借 branch 名当 `workflow_key`（`T-O-377`）。
- **内聚理由**：选图、预声明边、守卫、digest 封闭是同一张声明式程序的四个面。切开会让 NH3 在错误的图上注入工人。
- **辩证**：
  - 一张 mega 图（Q7-B，已否）会把非法边交给运行时守卫，且一张图变更碰到所有通道。
  - 维持 12 profile（Q7-C，已否）让 static/browser 两张图不相通，Q8-A 无法画正向再获取。
  - 表外 `dispatch_clean`（Q4-B，已否）把 `action_branch` 换文件名。
- **开放执行**：`G-NH-4`、`G-NH-5`、`G-NH-10`、`T-P-NH-9`、`T-P-NH-13`。
- **建议事实核查问**：
  1. `_source_profile_workflow` 是否确实只能替换三个 process_key、不能表达多 clean 边？
  2. 现有 admission BRANCH 是否足以作为晚绑定的同构证据，还是 CONTROL 步骤另有约束？
  3. 把 5 张选不中的图「并入」kind revision，会不会碰到 compiled digest / bootstrap 的隐藏假设？
  4. `s05_binding_digest` 今日是否被下游当成「创建时已含清洁工人」？推迟封闭要改哪些读方？

---

### 簇 2 · 表示与再获取

- **一句话**：绑定清洁工人之前，系统必须 **看见** 真实表示（文本层水位、rendered/print_pdf/transferred、空壳、嗅探 media）；必要时走已声明的正向再获取；decode 只观察，不代替 OCR 失败。
- **冻结真相**：`T-O-378`、`T-O-388`、`T-O-382`、`T-O-383`（绑定后不再换）；`S03-T011` 无环。
- **HEAD 待核现场**：
  - acquire 只写 `rendered|transferred`，从不写 `print_pdf`：`acquisition_ingest.py:535`
  - 无条件写 `browser_profile: injected-browser-renderer.v1`：同处 `535-536`
  - PDF 字面量扫描；无层抛 `CLEAN_OCR_CAPABILITY_UNAVAILABLE`；还写死 `text_layer: present`：`types.py:144-171`
  - preflight 期望 `print_pdf` 才能把 `clean.extract.pdf_llm` 解成 `web.browser_print_pdf`：`clean_preflight.py:46-62`
  - HTTP 无 image profile：`config_snapshots.py:504-506`
- **遗产**：htmlCrawl vs browserFetch vs browserPDF 事前选（`action_registry.ts:94-137`）。空 HTML 在 universal 可 SUCCESS——MKB 已用 `CLEAN_EMPTY` 拒绝（`intake/web/__init__.py:28-29`），不要借空成功。
- **内聚理由**：print-pdf、SPA 空壳、无层 PDF 都是「表示已知」问题。没有诚实表示，簇 1 的守卫没有 typed 输入，簇 3 的 OCR/print 路径物理不可达。
- **辩证**：Grok 笔记曾写「禁止 static 失败后自动 browser」。QNA 把它拆成：**暗升禁止**（无证据换表示）vs **已声明正向边允许**（业主接受的 Q2-B 例示）。本簇必须同时保住这两句，不能只留一句。
- **与簇 1 的边界**：簇 1 画布与封闭 digest；簇 2 生产守卫所读的事实，并把再获取边跑起来。事实核查若发现「观察器」必须改 Process 合同，应标在本簇，不要算成选图问题。
- **开放执行**：`G-NH-1`（真文本层才能观察「有层」）、`G-NH-2`、`G-NH-5`。
- **建议事实核查问**：
  1. 除 `types.py` 外，还有谁把「无字面量」当成 OCR 未部署？
  2. 图像 decode 空字符串（`acquisition_ingest.py:620-629`）是否已是「观察」先例，可被 PDF 无层模仿？
  3. 再获取若需要第二次 decode，现绑定表能否表达两条 decode 边而不成环？
  4. cookie banner / 打印参数是否仍能保持「不是 source kind」（D08）？

---

### 簇 3 · 清洁工人与 admitted clean

- **一句话**：闭集里每个清洁工人都在场，产出 **同一份** 非空 admitted clean body；promptA 只强制 LLM 策略；API map 与确定性仍是 clean，不是跳过 A。
- **冻结真相**：`T-O-381`、`T-O-386`、`T-O-378`、`T-O-383`（空正文非成功）；窄解释 `T-O-210`。
- **HEAD 待核现场**：
  - 10 键登记：`strategies.py:15-25, 46-151`
  - 组合根无 `browser_fetcher` / `clean_llm`：`api/app.py:330-345` 的 `IntakePipeline(...)` 关键字参数闭集
  - `llm_required` 才有 `prompt_key`：`strategies.py:47-55` vs `57-65`
  - `CLEAN_EMPTY`：`intake/web/__init__.py:28-29`；pdf/doc 同类
  - `dispatch_clean` 以 capability×strategy×media 决策：`intake/__init__.py`
- **遗产**：universal 才 AI，dedicated 只 ETL。本簇对齐该分账，而不是强迫 chinatax 再打一遍模型（Q6-B 已否）。
- **内聚理由**：工人是否 live、clean 合同是否同一、promptA 义务，是同一「第一环」问题。按通道切开，会把 `T-O-386` 的同一性拆丢。
- **与簇 2 的边界**：簇 2 给表示；簇 3 在 **已绑定** 的那一个工人里洗。绑定后再换工人属于 `T-O-383` 禁止，不在本簇「补救」。
- **开放执行**：`G-NH-3`、`G-NH-8`、`T-P-NH-6`、`T-P-NH-10`。
- **建议事实核查问**：
  1. OCR 与 Vision 是否已经共享同一 LLM 端口，只是 process_key 不同？
  2. API scatter child 是否已经从 member `clean_text` 进 LS-RAG，本簇只需保证空/坏 member 不假成功？
  3. promptA 三套默认 id 的具体分叉点在哪些文件？
  4. `max_input_bytes` 20MiB 与 `acquisition_max_response_bytes` 是否已经对齐证据面？

---

### 簇 4 · 公共上传

- **一句话**：调用方把真实 PDF/docx/图片变成 S13 handle；对象存在不是业务成功；Item 只由随后的 ingest/acceptance 产生。
- **冻结真相**：`T-O-381`、`T-O-385`、`T-O-383`。
- **HEAD 待核现场**：
  - 公共路由无 `/objects` 或 upload：`api/public/routes.py`
  - `local_object` 只要已有 `mkbobj:v1:…`：`src/contracts/api/models.py:116-121`
  - `ObjectStorePort.promote` 仅内部：`src/storage/ports.py`
  - S13 完成定义第 7 条「无公网 object API」：`S13-artifact-storage.md:67-77`
  - Task 创建先做身份幂等、新 Task 才 promote：`src/runtime/task/task_create.py:70-72`
- **遗产**：admin presign R2 → confirm → 再入队。借「字节先于业务身份」，不借 R2/file 行当 Item。
- **内聚理由**：身份法律与清洁工人无关。把上传塞进 pdf 簇，会让 web/API 路径的幂等法分裂。
- **辩证**：上传即 Item（Q5-B）污染 lifecycle；字节只活在 ingest Task 内（Q5-C）兑不了「文件上传全部落地」且受请求体上限。窄 reopen 已冻。
- **开放执行**：`G-NH-6`、`T-P-NH-8`。
- **建议事实核查问**：
  1. CAS unique `(team, sha256, size)` 是否已经足够作为 replay 分母（S13-E05）？
  2. 现 purpose 闭集扩一项的登记路径是什么？谁有权加？
  3. 无 ingest 孤儿的 GC grace 是否已有、是否误删仍被 ingest 指向的对象？
  4. 鉴权边界是否已有 Team 作用域，不必为上传发明新身份？

---

### 簇 5 · 语义分账

- **一句话**：clean body 是知识原文（g0 original）；realm/type/channel/source_name/is_active/tags 是 S04 revision 上的过滤面；二者不得互相写入。
- **冻结真相**：`T-O-389`、`T-O-386`、`T-O-62`、`T-O-352`；扩展 D08-T007。
- **HEAD 待核现场**：
  - FilterMeta 模型与 `semantic_tuples`：`src/contracts/intake/semantics.py:12-63`
  - `DEFAULT_SEMANTICS` 已为全部 intake 登记五维：`registry.py:229-239`
  - acceptance 仅当 `filter_meta` 为 mapping 时展开五维，否则 stub `{"source_kind": ...}`：`acceptance_snapshot.py:591-610`
  - layered `context_meta` 键含 realm/type/channel/source_name：`layered_content.py:17-28, 121`
  - API 三 provider 已调 `semantic_tuples`：`intake/api/providers/*.py`
- **遗产**：dedicated member 对象带 `*FilterMeta`，不把过滤维写进正文。借分账，不借 skip。
- **内聚理由**：这是检索身份，不是清洗算法。放进簇 3 会诱使「把标签写进 clean_text 好过模型」。
- **开放执行**：`G-NH-7`、`T-P-NH-7`。
- **建议事实核查问**：
  1. web/pdf 今日是否完全不写 `realm` 行，还是写了空 blob 就算过？
  2. S06 是否已经从 revision semantics 读 context，还是只从结构模型输出猜？
  3. `is_active` 对非 API 通道有没有已冻规则，还是本战役必须新给闭集派生？
  4. g0 summary 通道有没有地方会复制 FilterMeta？

---

### 簇 6 · publication 贯通与生命周期

- **一句话**：NH **不重写** structurize/construct/cuts/向量算法；但每条接通路径必须把 admitted clean 送进现有尾，并让七意图在真实对象上达到产品终态。
- **冻结真相**：`T-O-376`、`T-O-381`、`T-O-386`（不为通道另写 kernel）。
- **HEAD 待核现场**：
  - 单 root 贯穿 ingress→publication：`S03-T038`；图尾在 `lsrag_definition.py` structurize 之后
  - 七意图：`src/contracts/api/models.py:278-286`
  - retrieval 已在公共面：`api/public/routes.py:452` `POST .../retrieval:search`
  - R7 inline 4/4 不是四通道接通：`T-O-376`
- **内聚理由**：这是「下游已经存在、上游必须送达」的战役义务。若并进簇 3，会把生成面改动混进清洗工人。
- **辩证**：业主要真实向量。这不是新设计向量，是 **接通**。规划若在本簇出现新的切法/kernel，就是范围事故。
- **开放执行**：无 foundational 缺口；执行上要确认「可检索」的 Layer A 查询面是否已够验收。
- **建议事实核查问**：
  1. 现 publication 是否已按 accepted revision 消费，而不是 latest？
  2. rebuild / metadata 路径是否会重新 clean（S05 说 HITL/rebuild 不重新 clean）？
  3. scatter child 的向量与 parent 的关系是否已满足 `T-O-381` API 格？
  4. 七意图里哪些今日只对 inline 测过？

---

### 簇 7 · 失败法与证明闭集

- **一句话**：新路径服从已有 CAS/replay/ConflictError；绑定后失败就是失败；用无 monkeypatch 的测试证明 `T-O-381` 格子，而不是用 503 或补丁绿。
- **冻结真相**：`T-O-376`、`T-O-378`、`T-O-383`、`T-O-380`（发车日不进 DoD）。
- **HEAD 待核现场**：
  - Task 指纹双检：`task_create.py:70-104` 一带
  - e2e monkeypatch browser、OCR 失败关闭：`tests/e2e/test_source_capability_paths.py`
  - 空成功是遗产反例，MKB 已有 `CLEAN_EMPTY`
- **内聚理由**：证明与失败法是战役的退出面。提前分散到各通道 AP，会导致「每条路自己发明成功语义」。
- **开放执行**：`G-NH-11`、`T-P-NH-11`；测试文件名不锁。
- **建议事实核查问**：
  1. NS9-FX2 intake replay 指针约束是否已覆盖 `local_object` handle 复用？
  2. 哪些 e2e 今天依赖注入夹具，默认 `create_app()` 根本走不到？
  3. 0815 runner 纪律哪些可以借（turso.connect、不可变 run），哪些格子不能借（inline documentation）？

---

### A.8 簇 × 相位 × 拟 AP（初判对照）

| 簇 | 主相位 | 拟 AP | 验收时通道格子如何出现 |
|----|--------|-------|------------------------|
| 1 图与晚绑定 | NH1 | `AP-NH1` | 不按通道验收；验收「kind 选图 + 边看得见」 |
| 2 表示与再获取 | NH3（图位置在 NH1-06） | `AP-NH3`（NH1 画出边） | web 空壳、pdf 无层、print_pdf 作为格子 |
| 3 清洁工人 | NH3 | `AP-NH3` | 10+3 全表 |
| 4 公共上传 | NH2 | `AP-NH2` | pdf/doc 真文件的前置条件 |
| 5 语义分账 | NH4 | `AP-NH4` | 四通道都有五维 |
| 6 publication / 生命周期 | NH4 | `AP-NH4` | 每条接通路径可检索；七意图终态 |
| 7 失败法与证明 | NH5 | `AP-NH5` | 闭集 e2e；发车日不作为退出 |

---

## 附录 B · 站① 自检（对照模板速用表）

| 段 | 站① initial 填法 | 本文 |
|----|------------------|------|
| §2 真相台账 | foundational `T-O` + `T-P` | `T-O-376..389` CITE；`T-P-NH-1..14` 暂定 |
| §3 辨证审核 | 整合 eval/owner，标 `T-O` | Grok F1–F8 / GLM / 业主四目标已裁定 |
| §7 工作台账 | first-cut，待 pin | `NH1-01`…`NH5-04` |
| §8 gates | 仍 OPEN | `G-NH-1`…`G-NH-13` |
| §11 | 解锁 + 下游链意图 | 满三态 |
| 自宣告 role | 冻结零决策 | 文首 + 本文状态 `draft` |
| 业务簇 | 模板未单列；业主要求详论 | 附录 A，供事实核查 |

**明确未做（避免误读为已冻）**：未选 PDF 库、未选浏览器、未写 `step_key`、未写上传 URL、未写守卫枚举、未写实验 `run_id`、未声称 DAG 已排期、未派生 action-plan 文件。
