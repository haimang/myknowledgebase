# S14–S16 战役 · 全真相层审计报告

> **项目**：`myknowledgebase`（MKB）  
> **日期**：`2026-08-12`  
> **作者**：`MKB owner + Grok workflow domain-truth-s14-s16`  
> **文档性质**：`qna-truth / campaign audit`（**证据与编排记录**；**非**执行 SSOT）  
> **执行 SSOT**：仅 `docs/baseline/domain-truth/**`  
> **索引版本**：`spec-index.md` 附录 B · **v0.61**  
> **词表版本**：`spec-glossary.md` · **v2.8**

---

## 1. 战役结论（一句话）

S01–S16 与 D01–D05 的 domain-truth 均已 **accepted**（或 D02/D05 frozen）；S14–S16 v1.1 以 `T-O-263..336` 闭合治理/观测/安全三角；索引保持 **`active index`**——因 `17` System Topology 与 `18` Acceptance/Truth Freeze 仍 **pending**，**禁止**宣称 `review-ready index` 或 `frozen truth index`。

---

## 2. 形式化文件密度确认

| Spec | 路径 | 版本 | 状态 | 行数（约） | T-O 范围 | E 包 |
|------|------|------|------|-----------|----------|------|
| S14 | `domain-truth/S14-config-prompt-model-registry.md` | `S14-v1.1` | accepted | ~1063 | `T-O-263..286` | E01–E11 |
| S15 | `domain-truth/S15-observability-reliability.md` | `S15-v1.1` | accepted | ~1091 | `T-O-287..311` | E01–E11 |
| S16 | `domain-truth/S16-security-trust-boundary.md` | `S16-v1.1` | accepted | ~1237 | `T-O-312..336` | E01–E12 |

三文件均为九段式 + 执行台账 + 验收矩阵 + 修订历史；**非 thin**。QNA `qna-truth/S14.md` / `S15.md` / `S16.md` 为 locked 证据层。

**全局 T-O 连续**：最高占用 **336**；S14 附录标注下一空号 **T-O-337**（本审计 **不** 新分配）。

---

## 3. 覆盖矩阵（F2/F3/F4）

| 主题 | 权威 | 状态 |
|------|------|------|
| 配置分层 L0–L4 / ConfigSnapshot | S14 | frozen |
| Prompt git+hash / promptA·B·C | D03+D05+S14 | frozen |
| Model catalog bootstrap 写 vs S11 resolve | S14+S11 | 双向矩阵钉死 |
| Override 白名单 + 审计 sink 分账 | S14→domain_events / security_audit | frozen |
| Provenance model+prompt+schema+params | S14 | frozen |
| 三表 retention / metric 闭集 / ALERT_* | S15 | frozen |
| ready/live / sec_token_loaded | S15+S16 | frozen |
| operator 只读 / dead-letter / repair 分账 | S15+S03+S12 | frozen |
| InternalToken / EndpointClass / 限流 | S16 | frozen |
| Egress SSRF / SecretSlot / SupplyFence | S16 | frozen |
| Redaction 权威 | S16-T056；S15 sync-from | frozen |
| G-10 silent swap | S11+S14+S16 | closed for v1 transport |
| G-12 agent authoring | S03+S14 | **deferred** |
| G-01 skill registration | S01 | **deferred** |

---

## 4. 对抗扫描（race / 盲点 / 覆盖）

### 4.1 已关闭的竞态与双写风险

| 风险 | 裁决 | 证据 |
|------|------|------|
| catalog/binding 双写 SSOT | bootstrap 写=S14；resolve=S11-E03 | S14-T004/T018；S11-E03 矩阵 |
| Process 中途热切 binding | L4 一次 materialize；retry 禁热切 | S14-T007/T015/T016 |
| override 审计「和/或」双 sink | 成功→domain_events；越权→security_audit | S14-T017 |
| metric 名各域私造 | 必须进 S15 目录才可 export | S15-T017；S14 映射表 |
| event_type 私造 | D04 闭集 + S15 Writer；未登记失败 | D04 扩展纪律 |
| log 当业务 SSOT | 全域禁止；失败须关系/CAS/Outcome | OD + S15/S14/S16 |
| team_uuid 当授权 | 永不；token valid/invalid 单轴 | OD-04；S16-T003 |
| silent model swap | G-10 + SupplyFence + registry 禁 fallback | T-O-199/267/335 |
| `/health` 恒 ok 混 ready | live 禁依赖；ready 聚合 503 | S15-T019；S16 EndpointClass |

### 4.2 残差盲点（**不**阻塞 S14–S16 accepted；归 17/18 或已知 v1 残差）

| ID | 残差 | 承接 |
|----|------|------|
| GAP-01 | `17` System Topology 未写（进程/GPU/挂载/端口） | specs/17 |
| GAP-02 | `18` Acceptance/Truth Freeze 矩阵与签署未写 | specs/18 |
| GAP-03 | 跨域错误码总表（CONFIG_*/OBS_*/SEC_*/RETRIEVE_*/…）未汇编 | 18 |
| GAP-04 | event_type 全闭集与 payload allowlist 总对账 | D04+S15+18 |
| GAP-05 | 多副本 rate-limit 无共享计数器（S16 已知残差） | 17 部署说明 / 未来 reopen |
| GAP-06 | Vector/Turso/CUDA spike 与商业 benchmark 证据 | 附录 A 仍 pending |
| GAP-07 | legal-hold / 公网多租户加固 OOS | S15/S16 TM |
| GAP-08 | G-01 / G-12 deferred | 未来 adapter reopen |
| GAP-09 | G-09 foundation closed；精细容量曲线可与 S15 共治 | spike / 18 |

### 4.3 对 S01–S13 的校准动作

| 文件 | 动作 | 原因 |
|------|------|------|
| `S11-inference-runtime.md` | 头注 **S14-S16 战役校准** | 写/resolve 矩阵与 G-10/S16 边界显式 |
| `S14-…registry.md` | §8.5 Formal 状态 **v1.1** | 与 Truth 版本一致 |
| `S15-…reliability.md` | 附录 next T-O → **337** | 避免与 S16 占用冲突的陈旧提示 |
| S01–S10/S12/S13/D* 正文 | **未重写** | 扫描未发现因 S14–S16 导致的语义冲突；既有邻域分账已覆盖 |

---

## 5. Gate 登记状态（战役后）

| 状态 | Gate |
|------|------|
| **closed**（含 foundation / for v1 transport） | G-02..G-11，G-13..G-35 |
| **deferred** | G-01（skill 注册），G-12（agent authoring） |
| **open** | **无** |

---

## 6. 索引 / 词表回填摘要

| 工件 | 变更 |
|------|------|
| `spec-index.md` | §0 状态说明；§1.1 行 14–16 已 accepted；§1.2 glossary **v2.8**；§3.14–3.16 完整冻结回填；G-10 加固注记；§7 补 S08–S16 勿重做；附录 A checklist；附录 B **v0.59–v0.61**；§9 交叉引用 |
| `spec-glossary.md` | **v2.8**：扩 §7.7–7.9 术语；§8 alignment 补 S08–S11 与审计报告 |
| 本文件 | 战役审计 SSOT 证据 |

**索引状态词汇**：保持 **`active index`**。  
达到 `review-ready` 的前置：`17`+`18` accepted + 跨系统对账完成 + owner 审阅路径就绪。

---

## 7. 本战役触碰文件清单

1. `docs/baseline/spec-index.md`
2. `docs/baseline/spec-glossary.md`
3. `docs/baseline/domain-truth/S11-inference-runtime.md`（头注校准）
4. `docs/baseline/domain-truth/S14-config-prompt-model-registry.md`（§8.5 状态字）
5. `docs/baseline/domain-truth/S15-observability-reliability.md`（附录 T-O 提示）
6. `docs/baseline/qna-truth/_s14-s16-campaign-audit.md`（本报告）

**只读确认、未改写**：`S01`–`S10`、`S12`、`S13`、`S16` 正文、`D01`–`D05`、`qna-truth/S14|S15|S16.md`（已 locked）。

---

## 8. 建议下一步（非本审计范围）

1. 编写 `specs/17-system-topology.md`（进程模型、端口、GPU、object_root、token 注入面）。  
2. 编写 `specs/18-acceptance-truth-freeze.md`（HARD 矩阵、gate 终表、跨 ID/错误/事件对账）。  
3. 将 index 升 `review-ready` → owner 签署 → 全量 `frozen`。  
4. 实现阶段严格只引用 domain-truth；禁止把本 audit 当执行 SSOT。

---

**文件结束 · S14–S16 campaign audit · 2026-08-12**
