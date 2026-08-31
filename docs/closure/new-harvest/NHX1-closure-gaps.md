# NHX1 Closure Gaps（事实更正版）

> 日期：2026-08-31
> 当前判断：**NHX1 代码已写入并有本地回归结果，但还没有达到 closure-ready。**
> 本文只讨论内部验收缺口；不把 owner 签字、公开发布或 image 发布偷换成代码验收条件。

## 1. 当前已知事实

已完成的只是以下工程事实：

- P1–P9 的代码和本地测试命令已执行过；最近一次全仓结果为 `1010 passed`。
- `ruff`、现有架构扫描、migration 测试和若干 E2E 回归通过。
- 已有 `coverage.v1.json`、`manifest.v1.json`、race/crash 测试和分阶段日志。

这些结果说明“当前工作树在本地回归中没有失败”，不等于“NHX1 已完成独立审查、0815 级综合实验、组件技术栈确认和完整 closure 证据”。

## 2. 真正的内部 Closure 阻碍

| # | 缺口 | 当前事实 | Closure 前必须补什么 |
|---|---|---|---|
| 1 | 独立二次代码审查 | `docs/code-review/new-harvest/NHX1-third-pass-review.md` 是本轮执行者自己的审查，不是独立 reviewer 的二次审查 | 由不同审查者按 VF、migration、workflow、object/evidence、runtime、API、security 逐项审查，形成 findings；每个 finding 都要进入“测试 RED → 修复 → 重跑”循环 |
| 2 | 0815 级 E2E 综合实验 | 当前有许多 pytest E2E，但没有 `MKB-NHX1` 专属的 preflight、固定实验单元、运行结果、持久化 DB、retrieval/serving 证据包 | 建立类似 `.experiment/0815` 的 NHX1 runner/preflight/results/inspect 结构；实验必须覆盖四 source kind、声明策略、workflow、publication、retrieval、失败归因和资产不漂移 |
| 3 | 组件 Tech Stack 未冻结 | 目前只有抽象 `SupplyIdentity`/capability slot；实际 PDF parser、browser、OCR、model、CLI 的组件版本、binary digest、SBOM/CVE、适用边界没有形成 NHX1 manifest | 为每个实际组件登记名称、版本、来源、binary/model digest、adapter、输入输出、资源/网络边界、测试映射；PDF parser/browser 选型必须先确认，不能把当前 Firefox 发现逻辑当成已批准技术栈 |
| 4 | Claude/Agy CLI 组合未验证 | 代码中存在 `claude -p` 的 subprocess adapter 和 stub；没有完成生产级 `claude -p` 路径的 NHX1 E2E 证明，也没有 `agy -p` 的明确接入、边界和结果证据 | 明确 A/B/C 各阶段到底使用 Claude CLI、Agy CLI、local-vLLM 还是组合；固定 argv、stdin、prompt、schema、timeout、错误/重试和 provenance，并用真实 runner 验证 |
| 5 | Declarative workflow 与默认策略入库关系未完成证明 | `WorkflowDefinition` 确实存在于 `src/workflows/`，`WorkflowRegistryService.bootstrap()` 也会写 workflow registry/revision/steps/routes；但默认 clean strategy group 主要仍是代码 registry，NHX1 没有独立的“策略组已入库且与 workflow selection 对齐”的实验级证据 | 对每个声明式 workflow 证明：代码声明、持久化 revision/steps/routes、default strategy/capability、实际 selected route 和最终 retrieval 坐标一致；明确哪些是 code-owned registry、哪些必须 durable projection，不能只证明“表存在” |
| 6 | Test-ID / VF 证据闭集仍需独立复核 | 分组 pytest 和全仓结果存在，但不代表每个 VF、每个 `NHX1-T01..T30` 都由独立可复跑命令和真实结果支撑 | 独立 reviewer 复核 VF→work item→Test-ID→evidence 四向映射；逐 Test-ID 保存命令、exit、stdout digest、UTC、minimum layer，不能用分组 PASS 代替 |

## 3. 为什么之前的两个口径不能作为收口标准

之前提到的两个口径是：

1. “内部测试通过”；
2. “真实 live/production gate 通过”。

它们都不够：

- 内部测试通过只能说明已执行的断言通过，不能替代独立审查、测试↔修复循环、0815 级综合实验或 Tech Stack manifest。
- live/production gate 即使通过，也不能证明代码没有漏账、workflow 声明和默认策略没有漂移，或审查结论不是执行者自证。
- 因此，当前正确状态应是：**本地回归通过，但 Closure Evidence 不完整。**

## 4. `T22-O` 的位置

冻结 Q39 / `T-O-419` 曾把真实 model/binary/S16 owner attestation 写成 NHX1 final gate；这解释了旧 closure 为什么记录了 `T22-O`。

但本轮 owner 最新澄清是：`live 准备就绪` 指内部测试完成，owner 不参与内部验收。两者目前存在文档口径冲突：

- `T22-O` 不能被拿来掩盖上面 1–6 项内部缺口；
- 也不能在不修订冻结 Truth 的情况下，静默把 `T22-O` 删除。

所以当前应先完成 1–6 项内部验收；随后由项目 owner 决定是否追加、移除或重新定义 `T-O-419`，并按 append-only 规则记录变更。

## 5. 参考：为什么旧 NH1–NH9 当时可以结束

旧 NH 的 closure 主要是各 AP 的局部工程交付，很多生产、实验和审查内容明确留在 deferred/OOS：

- [AP-NH1 closure](/mnt/usb/workspace/myknowledgebase/docs/closure/new-harvest/AP-NH1-foundation-contracts-and-proof-baseline.md) 使用 `closed-with-explicit-deferrals`。
- [AP-NH6 closure](/mnt/usb/workspace/myknowledgebase/docs/closure/new-harvest/AP-NH6-local-runtime-supply-and-security.md) 将 `10+3 live-to-query` 和 S16 signature 留作后续条件。
- [AP-NH9 closure](/mnt/usb/workspace/myknowledgebase/docs/closure/new-harvest/AP-NH9-closed-set-assurance.md) 明确 “S16 is not signed here”。

这不能证明 NHX1 已满足同样条件；它只说明旧 NH 的完成谓词更窄，且允许显式 deferred。NHX1 如果要宣称更强的 closure，就必须先补齐本文件第 2 节的内部证据。

## 6. 正确的后续顺序

1. 先完成独立二次审查并登记 findings。
2. 对每个 finding 执行 RED → fix → rerun，直到 review findings 关闭。
3. 冻结并提交 NHX1 Tech Stack manifest，先决定 PDF/browser/CLI/model 真实组件。
4. 构建 NHX1 专属 0815 级 preflight + E2E runner，生成 DB/serving/retrieval/失败证据。
5. 重新核对声明式 workflow、默认策略组、capability 和 durable registry 的对应关系。
6. 重新执行逐 Test-ID evidence executor 和全仓测试。
7. 只有上述内部条件完成后，才讨论最终 closure 类型；任何 `T22-O` 口径另行按 Truth revision 处理。

## 7. 更正声明

此前版本把“固定发布物/production owner gate”写成主要甚至唯一 closure 阻碍，遗漏了本文件第 2 节的真实内部缺口。这是事实判断错误；当前版本以独立审查、综合实验、Tech Stack、CLI 组合和 workflow 入库证明为优先收口条件。
