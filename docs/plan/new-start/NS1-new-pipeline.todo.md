# NS1 执行 Todo / DAG

> 依据：`docs/plan/new-start/NS1-new-pipeline.md`、`docs/eval/new-start/pre-NS1-qna.md`
> 日志模板：`.adocs/code-execution-log.md`
> 收口模板：`.adocs/closure.md`
> 执行纪律：严格串行；前一 Phase 未完成、未测试、未回填日志、未分簇提交时，后一 Phase 保持 blocked。

## DAG 总线

```text
NS1-ENTRY
  └─> NS1-P1
        └─> NS1-P2
              └─> NS1-P3
                    └─> NS1-P4
                          └─> NS1-P5
                                └─> NS1-CLOSURE
```

并行仅允许发生在同一 Phase 内、且不跨越 block；每个 Phase 的退出条件必须全部满足：

1. STEP-1/STEP-2 上下文已重新读取并记录。
2. 本 Phase 的全部工作项、测试、审查修复已完成。
3. 工作日志已按 `.adocs/code-execution-log.md` 追加到 action-plan 底部。
4. 本 Phase 已完成分簇 commit，且 commit 后测试重新运行。

## NS1-ENTRY — 已完成

- [x] 读取 NS1 action-plan 全文及其引用锚区。
- [x] 读取冻结真相层 `docs/eval/new-start/pre-NS1-qna.md`（`T-O-337..351`）。
- [x] 读取 `.adocs/code-execution-log.md` 与 `.adocs/closure.md` 模板。
- [x] 确认禁止项：live migration、worker 发布、Pages 发布。

## NS1-P1 — 契约资产与 catalog

**Block：NS1-P1 可执行；NS1-P2 blocked until P1 exit gate。**

- [x] `P1-01 / NS1-T01`：冻结 `layered_content.v1` schema 与 generic/legal/realestate 金样、非法样例。
- [x] `P1-02 / NS1-T02`：迁入四角色 prompt 正文并校验正文约束/hash。
- [x] `P1-03 / NS1-T03`：仅晋升 `mkb_prompt_hash_pointers` 既有表，补 role/status/granularity_set migration。
- [x] `P1-04 / NS1-T04`：bootstrap 四 role default 与 json 闭集。
- [x] `P1-05 / NS1-T05/T06`：内部 token + internal network catalog CRUD；更新为新 immutable version；禁止 body/path traversal。
- [x] `P1-06 / NS1-T07/T46`：统一 `resolve_prompt(prompt_id)` 与 hash fail-closed/soak。
- [x] STEP-1：重新读取 P1 使用的 plan 锚 A-9/A-10/A-12/A-20..A-27、S14/D04 相关真相。
- [x] STEP-2：重新读取 QNA `T-O-337..351`，确认不改入口为 `prompt_id`、四 role、json 行闭集。
- [x] STEP-3：开发、unit/domain 测试、审查和修复。
- [x] STEP-4：按 code-execution-log 模板追加 P1 工作日志。
- [x] STEP-6：分簇提交 P1（schema/prompts；migration/registry；CRUD/tests）。
- [x] P1 EXIT：所有 P1 tests green，commit 后重跑，P2 解锁。

## NS1-P2 — Kernel 验收

**Block：仅在 NS1-P1 EXIT 后解除；已完成。**

- [x] `P2-01 / NS1-T10/T11`：实现 `adopt_layered_json`，NFC/LF、schema、闭集、g0 回填、精确子串首次命中、失败码、projection。
- [x] `P2-02 / NS1-T12`：`_structurize` 只接受/采用候选 JSON；生产不再调用 compiler 假树；metadata refresh 同步修复。
- [x] `P2-03 / NS1-T13`：construct 按 `block_id` 使用 C 整包 summary；原文不可变。
- [x] STEP-1：重新读取 P2 锚 A-1/A-2/A-3/A-13/A-14、S06/S07 真相及 P1 输出。
- [x] STEP-2：重新读取 QNA `T-O-343..347`，确认不静默补层、不退回假树、C 只吃验收 layered。
- [x] STEP-3：开发、unit/domain 测试、审查和修复。
- [x] STEP-4：按模板追加 P2 工作日志。
- [x] STEP-6：分簇提交 P2（kernel；generation wiring；tests/fixture）。
- [x] P2 EXIT：T10–T13 green，源码守卫 green，P3 解锁。

## NS1-P3 — CLI 工人与四跳

**Block：仅在 NS1-P2 EXIT 后解除；已完成，NS1-P4 解锁。**

- [x] `P3-01 / NS1-T20`：实现可注入 `ClaudeCliPort`/RecordingStub，argv、schema、error/usage/session 合同。
- [x] `P3-02 / NS1-T21`：仅 llm clean strategy 经 CLI；deterministic/API 不调用 CLI。
- [x] `P3-03 / NS1-T22`：新增可选 `lsrag.transcribe_markdown`，只产 Markdown。
- [x] `P3-04 / NS1-T23`：B.json 使用 schema + adopt，按 markdown/clean 切换物料。
- [x] `P3-05 / NS1-T24`：C 整包一次，消费验收 layered，不改 original。
- [x] STEP-1：重新读取 P3 锚 A-5/A-6/A-16/A-18、S11/legacy transport reference 及 P2 输出。
- [x] STEP-2：重新读取 QNA `T-O-338/T-O-340/T-O-347/T-O-350` 与 claude transport 证据。
- [x] STEP-3：开发、unit/spike 测试、审查和修复；CI 禁网络/禁 live vendor。
- [x] STEP-4：按模板追加 P3 工作日志。
- [x] STEP-6：分簇提交 P3（CLI；handlers/wiring；tests）。
- [x] P3 EXIT：T20–T24 green，P4 解锁。

## NS1-P4 — API 与 Workflow

**Block：NS1-P3 EXIT 已满足；当前 in_progress（先完成 STEP-1/STEP-2，再进入实现）。**

- [ ] `P4-01 / NS1-T30/T31`：`IntakeIngestPayload` strict `*_prompt_id`，json required，拒绝 prompt_ref/path/角色错配。
- [ ] `P4-02 / NS1-T32`：主图及 scatter child 加可选 markdown 跳；无 id 不创建 transcribe process。
- [ ] `P4-03 / NS1-T33`：结构失败为 failed，不因 B 失败开 human gate；显式 review 仍可用。
- [ ] `P4-04 / NS1-T34`：materialize 冻结四跳 `{prompt_id,version,hash,path}`，retry 不热切。
- [ ] STEP-1：重新读取 P4 锚 A-7/A-8/A-11/A-19/A-30/A-33、API/workflow/runtime 真相及 P3 输出。
- [ ] STEP-2：重新读取 QNA `T-O-341/T-O-348..351` 与 S03/S14 frozen binding 约束。
- [ ] STEP-3：开发、contract/e2e 测试、审查和修复。
- [ ] STEP-4：按模板追加 P4 工作日志。
- [ ] STEP-6：分簇提交 P4（payload/catalog resolution；workflow；tests）。
- [ ] P4 EXIT：T30–T34 green，P5 解锁。

## NS1-P5 — 分层测试与收口

**Block：仅在 NS1-P4 EXIT 后解除。**

- [ ] `P5-01 / NS1-T40`：domain architecture guards。
- [ ] `P5-02 / NS1-T41/T42`：stub CLI generic/no-md 与 legal/with-md 两条旅程。
- [ ] `P5-03 / NS1-T43`：child 失败隔离、sibling 完成、root fail-closed。
- [ ] `P5-04`：S14/D04 窄回填附录与 README payload 示例（不改 QNA）。
- [ ] `NS1-T44/T45/T46`：既有 generation/intake 回归与 hash soak。
- [ ] STEP-1：重新读取 P5 锚 A-28..A-33、测试台账、全部 P1–P4 产物。
- [ ] STEP-2：重新读取 QNA 全部冻结项及 §10 hard gates。
- [ ] STEP-3：全面开发、审查修复、unit/domain/intake/e2e/mega/soak 本地测试。
- [ ] STEP-4：按模板追加 P5 工作日志。
- [ ] STEP-6：分簇提交 P5（guards/e2e；truth/docs；final fixes）。
- [ ] P5 EXIT：硬闸全部 PASS；生成 closure。

## NS1-CLOSURE — 最终收口

- [ ] 只在 P1–P5 EXIT 后创建 `docs/closure/new-start/NS1-new-pipeline-closure.md`。
- [ ] closure 使用 `.adocs/closure.md` 结构，逐项给出五态与四元组证据。
- [ ] 回填 action-plan 状态 `executed` 与测试台账/日志，不改 QNA。
- [ ] 最终审查：`git diff --check`、`ruff`、`compileall`、全量 `pytest`、scope/forbidden scan。
- [ ] 明确声明：未执行 live migration、未发布 worker、未发布 Pages。
