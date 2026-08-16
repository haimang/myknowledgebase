# pre MKB-0815-R3 · 发车前预检冻结

> **对象**：`MKB-0815-R3`（After-NS3 族第三枪；方法/对象/预检家）
> **日期**：`2026-08-16`
> **作者**：`Grok`
> **文档性质**：`eval / preflight-freeze`（不是 closure，不是发车令）
> **文档状态**：`subjects-sealed / WAIT_OWNER`
> **上游权威**：
> - `docs/eval/new-start/pre-NS4-qna.md` `T-O-365` / `T-O-375`
> - `docs/closure/new-start/NS4-generation-evidence-plane-closure.md`
> - `.experiment/0815/runs/MKB-0815-R3/RUN.md`
> **下游**：业主是否点头执行冻结 collect；R3 分析必须产品表 + 观测表（数一等行）

---

## 0. 一句话

R3 **可以进入业主发车闸**，前提是本文件引用的预检 `passed=true`。本文件 **不**授权 ingest。

live 仍走冻结命令（`T-O-375`）：

```bash
.venv/bin/python .experiment/0815/runs/MKB-0815-R2/collect.py \
  --cells N-A5,N-A3,N-A6,N-A2,Q-A5 \
  --suffix -r3 --no-extras --rerun
```

R3 不新建 serving 库。Q-A3 留在 R2 `runtime/mkb.turso.db`（17 向量）。禁止 `rm` 该库或归档 `mkb.db`。

---

## 1. 冻结身份

| 项 | 值 |
|---|---|
| run | `MKB-0815-R3` |
| parent | `MKB-0815-R2` |
| 方法 | `.experiment/0815/runs/MKB-0815-R3/RUN.md` |
| 封存时刻 | `2026-08-16T06:23:48Z` |
| 封存 HEAD | `d3a41955cbdd6a9fea70b24a2c816561f08cb793`（预检前；代码闸通过后以 `preflight.json.git_head` 为准） |
| SUBJECTS.md5 文件 MD5 | `442752284761368a4b0fee1554c7e909` |
| METHOD.md5 | `014ea5646ac229b89cd7a6e3173ef51e`（`RUN.md`） |
| PROTOCOL.md5 文件 MD5 | `a582f479db73c3e81122db87fd52641d` |
| 结论 | **未封**（live 未跑） |
| R1 封条 | 保持 `conditional-ready`，不改写 |

对象 18 份：R1/R2 同文 6 篇 + 提示词/schema，含 g1 **v3**。g1 v3 与仓内 `data/prompts/json/promptB.documentation.g1.v3.md` 字节一致（MD5 `97a605c0b7bdbe1c7f6949baf015d65c`）。

---

## 2. 格子与通过标准（冻结）

**开**：`N-A5, N-A3, N-A6, N-A2, Q-A5` + `-r3`。  
**不开**：Q-A3 同键、A1、A4、A5g2。不改 C，不换 binding。

产品轴 `R3_READY`：

```text
Q-A3 serving intact
+ at least one of {N-A5, Q-A5} publish
+ zero GRANULARITY_SET_MISMATCH on this -r3 g1 set
+ retrieval re-score has no Layer A 422
+ no kernel patch
+ Q cells not lane_contaminated
+ NS4 closure already recorded
```

观测轴按格：失败必须有 **stage report 或 failed invocation 行**；否则 `obs-insufficient`；不连坐；不认 extra。

---

## 3. 预检发现并已处理的阻塞

现场 Turso 拷贝在预检时仍停在 `012`：`mkb_generation_stage_reports` 不存在。直接套原 013 会因历史 extra `stage_key=transcribe_markdown` 撞上 CHECK。

处理（预检范围，不是 live ingest）：

1. 证据面 `stage_key` 对齐 `T-O-369` 闭集：`transcribe_markdown` → `markdown`；
2. 013 回填只接受闭集值，并把历史别名映射为 `markdown`；
3. 备份后对 `mkb.turso.db` 执行 `r3_prepare.py`（`migrate` + catalog v3）。

结果：013 已应用；8 条历史 invocation 映射为 `markdown×6 / structurize×1 / construct×1`；向量仍 17/17；Q-A3 task succeeded；零 `-r3` 键。

---

## 4. 预检闸

权威机器记录：`.experiment/0815/runs/MKB-0815-R3/results/preflight.json`  
`checked_at`：`2026-08-16T06:25:36Z` · `passed`：`true` · `git_head`：`d3a41955cbdd6a9fea70b24a2c816561f08cb793`

19/19 闸全过：R1 封条与对象、R2/R3 对象、NS4 closure、g1 v3 合同、catalog g1=v3/C=v2、`transcribe_markdown→markdown`、CLI schema、markdown flavor、冻结命令、Turso 013 + 17/17 向量、零 `-r3` ingest、问句 `expected_dimension`、仓内测试结构、vLLM 模型、Layer A 1024 embed、Qwen `PING_OK`、Claude NI `PING_OK`。

仓内测试结构：

| 文件 | 锁什么 |
|---|---|
| `tests/domain/test_r3_preflight_kit.py` | R3 方法/协议/封条文件在 |
| `tests/domain/test_r3_launch_lock.py` | 冻结命令、Turso/CW、零 `-r3` jsonl |
| `tests/unit/test_r3_prompt_freeze.py` | g1 v3 闭集、C 仍 v2、markdown 证据键 |
| `tests/integration/test_r3_turso_evidence_ready.py` | 013 + 17 向量 + g1 v3 + 无 `-r3` ingest |

---

## 5. 业主发车核对单

- [x] NS4 closure 已写，R3 不在 NS4 相位
- [x] 对象与方法已封 MD5
- [x] g1 v3 active，C v2 未改
- [x] Turso + CW；Q-A3 17 向量 intact
- [x] 013 + stage_reports 表已在 live 拷贝
- [x] 零 `-r3` ingest
- [x] `preflight.py` 全绿（`2026-08-16T06:25:36Z` · 19/19）
- [ ] **业主点头** 后才跑冻结 collect
