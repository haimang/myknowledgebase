# MKB-0815-R5 · 系统写 g0 + 模型只报锚点

> **文档性质**：`eval / execution-ledger`（可执行台账 + 施工说明；不是 closure，不是发车令）
> **日期**：`2026-08-17`
> **作者**：`Grok`
> **上游 RCA**：`docs/eval/new-start/after-MKB-0815-R3-analysis.md`；R4 记分 `after-MKB-0815-R4-first-wave.md`
> **下游**：R5 代码 + 预检 + 业主点头后的 `-r5` live
> **文档状态**：`drafted / WAIT_OWNER_TO_EXECUTE`
> **不改写**：R1 封条；R2/R3 RCA；kernel 拒绝谓词

本文件把上一轮口头解法收成 **一张台账、一个 DAG、一份按函数写的施工说明**。未写到的文件默认不动。Live 仍要业主另令。

---

## 0. 解法一句话

原文已经在系统手里。不要再让模型默写全书。

1. **g0 由管道写入**：无论模型交了残缺全文、空全文、还是没交 g0，组装器都放进恰好一块 `body = clean`。
2. **g1 由模型报锚、管道来剪**：模型只交每章在原文里能对上的 **起句 / 止句**，禁止交整章 body。管道在 `clean` 上切片，再交给 **现有** admit。
3. **裁判规则一字不改**：`g0 == clean`、g1 必须是 `clean` 连续子串、层集合必须等于冻结 profile。变的是试卷怎么组，不是怎么判。

内核 `normalize_layered_candidate` **已经**有一条窄隧道：g0 的 body 为空时填 `clean`（`adopt.py` 注释写明 *frozen g0 clean-text tunnel*）。N-A3/Q-A5 红是因为模型交了 **非空但残缺** 的 g0，隧道不触发，随后被「g0 不是全文」打死。本方案把隧道补完：**运行时永远用 clean 覆盖 g0**，不放宽「覆盖之后仍必须相等」那条拒绝。

---

## 1. 问题如何映射到工作项

| 现场失败 | 根因（已证） | 本方案哪一相解 |
|---|---|---|
| N-A3 / Q-A5 `STRUCTURE_ANCHOR_MISSING`（g0 非全文，但已有 g1） | 模型抄残了全书 | **P1 系统写 g0** |
| N-A2 `GRANULARITY_SET_MISMATCH`（`set=0`，1 块） | 模型交完 g0 就停，57KB 不肯切章 | **P2 锚点切章**；若仍无切，**P6 残差登记**，不开 v5 |
| N-A6 `empty_result` | 信封空，不是切章 | **不绑进 P1/P2 验收**；P6 残差 |
| Q-A3 17 / N-A5 21 | 已发布资产 | **全程 tripwire**，禁止同键重跑、禁止删库 |

禁止再用「加厚步骤 6」当本方案的主路径。v3/v4 已证：禁 g=2 / 恰好集字面改变不了 57KB 工人行为。

---

## 2. 不变量（违反即停工）

- 不改 `validate_layered_content` / `adopt.py` 的 **拒绝谓词**（`STRUCTURE_ANCHOR_MISSING` / `GRANULARITY_SET_MISMATCH` / g0 必须恰好一块 的判定式）。
- 不改 stub，不静默 salvage，不换生产默认 binding。
- 不改 C，不改 R1 封条，不回写 R2/R3/R4 已发生 Task。
- 叶服务 `lsrag_*` 仍无 I/O；组装器停在 Mixin / runtime，**不**渗进叶包。
- 证据仍是一等行；禁止把原文 / prompt / stdout 写入 extra 或 stage report。
- 禁止 `rm` `mkb.turso.db`。Q-A3 必须保持 17 向量，N-A5 必须保持 21 向量。
- 文档提示词仍禁止大写 `MKB`、`semantic_block`。

「系统写 g0」**不是**放松 kernel：admit 仍检查 `g0.body == clean`。只是交 g0 的人换成管道。

---

## 3. 成功定义

### 3.1 代码相（P1–P3）未绿不得进 live

见 §5 台账验收列。

### 3.2 Live 相 `R5_READY`（仅业主点头后的 `-r5` 枪）

```text
R5_READY
  = Q-A3 serving intact (17)
  + N-A5 serving intact (21)
  + N-A3 不再因「g0 非全文」失败
    （允许因缺 g1 / 锚点对不上而红，但码不得再是
     "The g0 body is not the complete clean artifact"）
  + Q-A5 同上
  + N-A2：若模型交出 ≥1 条可解析切刀，则不得再因「只有一块 g0」红
    （set 不得再是 {0}；缺切刀则记 CUTS_EMPTY，见 §6.3，不记成「v5 提示词失败」）
  + 每格失败仍有 stage report（admit 拒绝另有 failed invocation）
  + retrieval 无 Layer A 422
  + no kernel patch / Q 格不串 NI
```

N-A6 空信封 **单独记分**，不否决 P1/P2。57KB 若切刀仍为空，token 仍 `conditional-ready`，并按 §8 把 A2 标成体量 defer，**禁止**再开提示词版本。

---

## 4. 相位与 DAG

```text
P0  冻本文件（本文）
  -> P1  运行时组装：永远写入系统 g0
  -> P2  切刀信封 + 切片器 + 新提示词（模型不再交 g1 body）
  -> P3  单测 / 金样 / 守卫
P1+P2+P3
  -> P4  R5 preflight（serving 17+21、catalog、零 -r5）
  -> WAIT_OWNER_LIVE
      -> P5  collect --cells N-A3,N-A6,N-A2,Q-A5 --suffix=-r5 --no-extras --rerun
      -> P6  记分 + 残差台账（N-A6 / 可选 A2 defer）
```

任一相未绿不得进下一相。P5 前零 ingest。

---

## 5. 执行工作台账

| ID | 相 | 工作项 | 输入证据 | 精确输出 | 验收 |
|---|---|---|---|---|---|
| `R5-00` | P0 | 冻结本解法 | 口头方案 + R3/R4 记分 | 本文落盘 | 本文 |
| `R5-01` | P1 | 系统 g0 组装器 | N-A3/Q-A5 消息逐字「g0 非全文」；`adopt.py:37-68` 空隧道 | 见 §6.1 | 残缺 g0 + 合法 g1 → admit **不再**报 g0 非全文 |
| `R5-02` | P1 | `_structurize` 先组装再 admit | 现 `generation_construct.py` admit 前 | 只改 Mixin 调用点 | CLI/live 两条都走组装器 |
| `R5-03` | P2 | 切刀合同 `mkb.b-json-cuts.v1` | 「模型不得拥有坐标」（`adopt.py:125`） | 纯校验，无 I/O | 非法切刀 fail-closed；禁止 span/offset 字段 |
| `R5-04` | P2 | 切片器：切刀 → `layered_content.v1` | clean + cuts | 只产出 kernel 已认识的包 | 每刀唯一命中；歧义/逆序/空刀 typed 失败 |
| `R5-05` | P2 | 提示词 g1.cuts.v1 | v4 已证加厚无效 | **新文件**，不改 v4 字节 | 无 `"granularity"` 正例；禁止抄全书；无 `MKB` |
| `R5-06` | P2 | catalog / resolve | UNIQUE prompt_id | g1 默认切到 cuts 版 **或** 新 prompt_id（见 §6.5） | bootstrap retire+insert；N-A5/Q-A3 快照不回写 |
| `R5-07` | P3 | 单测闭集 | §7 | 新 `tests/unit/test_r5_assemble.py` 等 | 见 §7 |
| `R5-08` | P3 | architecture 守卫 | 叶无 I/O | 组装器不得进 `src/services/lsrag_*` | 现有叶守卫仍绿 |
| `R5-09` | P4 | R5 preflight | 17+21 tripwire | `MKB-0815-R5/preflight.py` | exit 0；零 `-r5` |
| `R5-10` | P5 | live 四格 `-r5` | 业主令 | 新 Task，不覆盖旧键 | 见 §3.2 |
| `R5-11` | P6 | 记分 / 残差 | jsonl + Turso 一等行 | eval；不封 R1 | N-A6、可选 A2 defer 入账 |

---

## 6. 施工说明（按函数、字段、禁令）

未点名的文件默认不动。

### 6.1 `R5-01` — 系统 g0 组装器

**新文件（推荐）**：`src/runtime/intake/generation_assemble.py`  
纯函数，无 persistence / 无 CLI。不要放进 `src/services/lsrag_structurize/`。

```python
def overlay_system_g0(
    *,
    clean_text: str,
    candidate: Mapping[str, object],
    profile: tuple[int, ...],
) -> dict[str, object]:
    """Drop every model g0 block; insert exactly one system g0 (body=clean)."""
```

规则：

1. `clean = normalize_layered_text(clean_text)`（与 kernel 同一 NFC / 换行配方，从 `contracts.lsrag.layered_content` 引用，禁止另写一套空白规则）。
2. 从 candidate 取出 `layered_content` 列表；**丢掉**所有 `granularity==0` 的块（残缺全文一律丢弃，不尝试修补）。
3. 在列表 **最前** 插入：

```python
{
  "block_id": 0,
  "granularity": 0,
  "original_content": {"title": None, "body": clean},
  "llm_summary": {"title": None, "body": None},
}
```

4. 其余块（g1/g2）`block_id` **重排**为从 1 起递增（避免与系统 g0 撞 id）。**不得**改它们的 body。
5. 保留 `context_meta`；`date` / `knowledge_tree` 若不是对象就丢掉（不要为了救模型去改 schema 校验）。
6. **不**在本函数里做层集合判定。交给随后的 admit。因此：
   - 残缺 g0 + 合法 g1 → 覆盖后 set 仍 `{0,1}` → 过 g0 检查；
   - 只有残缺 g0 → 覆盖后仍只有 `{0}` → 仍 `GRANULARITY_SET_MISMATCH`（N-A2 现状，正确）。

禁止：

- 把模型 g0 与 clean 做 fuzzy merge / diff 补丁。
- 在组装器里吞掉 `STRUCTURE_*`。
- 把 clean 全文写入 diagnostic / extra。

单测（必须）：

| 例 | 输入 | 期望 |
|---|---|---|
| A | g0 body=`clean[:-10]` + 两块合法 g1 | admit **成功**（或至少不再是 g0-非全文） |
| B | 仅一块残缺 g0 | 仍 `GRANULARITY_SET_MISMATCH`，histogram `set=[0]` |
| C | 无 g0、两块合法 g1 | 插入系统 g0 后 admit 成功 |
| D | 残缺 g0 含密钥字符串 `SECRET` | 组装后 candidate / extra / report **不得**再出现 `SECRET`（已被丢掉） |

例 A 是对本相的定义性验收：它就是 N-A3 的缩小版。

### 6.2 `R5-02` — 接线位置

**只改** `src/runtime/intake/generation_construct.py` 的 `_structurize`：在得到 `layered_candidate`（CLI 或 live 或 state）之后、`LsragStructurizeService().admit(...)` 之前：

```python
layered_candidate = overlay_system_g0(
    clean_text=clean,
    candidate=layered_candidate,
    profile=profile,
)
```

CLI 失败（非 object）**不要**走组装器，保持现有 transport_failed + `cli_structured_kind` 路径。

`_live_structured_generate` 与 CLI 两条都要经过同一点，禁止只给 NI 接线。

禁止在 `lsrag_structurize.admit` 里偷偷覆盖 g0（叶包保持「只判不造」）。现有空-g0 隧道可留作防御，但 R5 **不得依赖**模型把 g0 留空。

### 6.3 `R5-03` — 切刀合同

**新文件**：`src/contracts/observability` **不要**用；切刀是 B 的物料，不是观测。  
推荐：`src/contracts/lsrag/cuts.py`（纯校验，无 I/O）。

```text
schema_version = "mkb.b-json-cuts.v1"
```

允许顶层键（闭集）：

```text
schema_version, cuts
可选 context_meta（对象；未知键丢掉或整段省略，二选一写死在实现里，禁止半接受）
```

`cuts` 必须是 **非空** 数组，否则 `CUTS_EMPTY`（新产品码，422）。空切刀 **不要**伪装成 `GRANULARITY_SET_MISMATCH`：那会和「交了 g0 没切」搅在一起。N-A2 若改切刀后仍交空列表，记 `CUTS_EMPTY`。

每一刀允许键（闭集）：

```text
title      字符串或 null
start      非空字符串，必须是 clean 的精确子串
end        非空字符串，必须是 clean 的精确子串
```

**禁止**键：`span`、`start_byte`、`end_byte`、`offset`、`index`、`body`、`original`、`clean`。模型不得拥有坐标。

校验失败码（新产品码，全部 422，走现有 `MkbError` + stage report）：

| 码 | 何时 |
|---|---|
| `CUTS_SCHEMA_INVALID` | 类型/未知键/缺字段 |
| `CUTS_EMPTY` | `cuts` 缺或空 |
| `CUTS_ANCHOR_MISSING` | `start` 或 `end` 不是 `clean` 子串 |
| `CUTS_ANCHOR_AMBIGUOUS` | `start` 在 `end` 之前的窗口里出现 ≥2 次，或 `end` 在选定起点之后出现 ≥2 次 |
| `CUTS_ORDER_INVALID` | 唯一命中后 `start` 位置 ≥ `end` 位置 |

禁止把 `start`/`end` 全文写入 extra。report 只记 `cut_count`、`failed_index`（int 或 null）。

### 6.4 `R5-04` — 切片器

同模块 `generation_assemble.py`：

```python
def assemble_from_cuts(
    *,
    clean_text: str,
    cuts_pack: Mapping[str, object],
    profile: tuple[int, ...],
) -> dict[str, object]:
    """Validate cuts, slice clean, overlay system g0, return layered_content.v1."""
```

算法（必须按此，禁止「就近段落」启发式）：

1. `clean = normalize_layered_text(clean_text)`。
2. `validate_cuts(cuts_pack)`。
3. 对第 `i` 刀：
   - `s = clean.find(start)`；找不到 → `CUTS_ANCHOR_MISSING`。
   - 若 `clean.find(start, s+1)` 仍 ≥0 **且** 在第一个 `end` 之前还有第二次 `start` → `CUTS_ANCHOR_AMBIGUOUS`。
   - 从 `s` 起找 `end`：`e = clean.find(end, s)`；找不到 → `CUTS_ORDER_INVALID` 或 `CUTS_ANCHOR_MISSING`（找不到 end 用 MISSING；找到但 `e < s` 不可能；`e == s` 且 end 不是 start 的后缀时允许零宽？**禁止零宽**，`e + len(end) <= s` → `CUTS_ORDER_INVALID`）。
   - 若 `clean.find(end, e+1)` 在本刀无定义；**只要求** 从 `s` 起 `end` 第一次出现。第二次出现不 Ambiguous（止句重复很常见）。**只对 start 在 [s, e) 内重复判歧义。**
   - `body = clean[s : e + len(end)]`。
4. 组装 `layered_content.v1`：系统 g0 + 各刀 g1（`block_id=i+1`，`original_content.title=title`，`body=切片`，summary 全 null）。
5. 调用方再 `admit`。切片合法则 g1 必为子串，g0 必等于 clean。

单测：

| 例 | 期望 |
|---|---|
| 正例：与 v4 正例同一 `clean`，四段起止句 | 组装后 admit 成功，g1 body 与手工切片一致 |
| start 不在 clean | `CUTS_ANCHOR_MISSING` |
| start 出现两次且都在第一次 end 前 | `CUTS_ANCHOR_AMBIGUOUS` |
| end 在 start 之前 | `CUTS_ORDER_INVALID` |
| `cuts=[]` | `CUTS_EMPTY` |
| 切刀 JSON 含 `start_byte` | `CUTS_SCHEMA_INVALID` |

### 6.5 `R5-05` / `R5-06` — 提示词与 catalog

**新建** `data/prompts/json/promptB.documentation.g1.cuts.v1.md`。  
**禁止**改 v3/v4 字节（N-A5 钉 v3 hash）。

提示词要点（保持短，不堆说教）：

- 你 **不要** 输出 `layered_content`，不要输出 g0，不要抄 `clean` 全文。
- 只输出一个对象：`{"schema_version":"mkb.b-json-cuts.v1","cuts":[...]}`。
- 每一刀 `start`/`end` 必须是 `clean` 里逐字出现的短句（建议 ≤ 80 字），用来框一章。
- 必须覆盖一级结构；禁止空 `cuts`；禁止坐标。
- 正例 / 反例 / 步骤 1–n；禁止大写 `MKB`。

Catalog 二选一，**本台账指定 A**（少一个 prompt_id，少一条路由）：

- **A（指定）**：`promptB.documentation.g1` 新版本 `cuts.v1` 或 `v5`，路径指向 cuts 文件。`resolve_prompt` 无版本 → 数值最新。N-A5 旧快照仍钉 v3。  
  版本号用 `v5` 而不是 `cuts.v1`，以符合现有 `_PROMPT_VERSION = ^v[0-9]+`。
- B（否决除非业主改口）：新 `prompt_id`，要改 flavor→id 表。

`DEFAULT_CATALOG_PROMPTS` 把 g1 指到 `v5` + cuts 文件。现库 `register_prompt` retire+insert，与 v3/v4 相同，禁止只 bootstrap。

`_structurize` 在 CLI/live **解码之后** 分岔：

```text
if pack.get("schema_version") == "mkb.b-json-cuts.v1"
    or "cuts" in pack:
        candidate = assemble_from_cuts(...)
else:
        candidate = overlay_system_g0(candidate=pack, ...)
admit(candidate)
```

兼容：若某车道仍吐旧 `layered_content`（过渡期），P1 覆盖 g0 仍生效。R5 live **只**发 cuts 提示词；旧形状仅作防御，不是双合同。

解码：CLI 已要求顶层 object。cuts 包走同一 `structured` 路径。schema 校验用 cuts JSON schema（可挂 `--json-schema`），**不要**再挂 `layered_content.v1` 去逼模型交 g0。

### 6.6 `_cli_layered_candidate` / live schema

今天 NI structurize 带 `lsrag.layered_content` schema。R5 必须改成 cuts schema，否则模型被 schema 逼着交 g0/g1 body。

**允许改**：`generation_construct.py` 里给 json role 选 schema 的分支；新 `data/schemas/mkb.b-json-cuts.v1.json`。  
**禁止**改 `lsrag.layered_content.v1.json` 本体。

### 6.7 观测

沿用 R4 已接线：admit/cuts 失败 → stage report + failed invocation。  
cuts 失败：`error_code` 用 `CUTS_*`；histogram 可空；`cut_count` 可进 report 的已有计数字段或 `layer_counts` **不要**滥用。推荐 report：`block_count=len(cuts)`，`granularity_set` 空或省略，`disposition=rejected`。

禁止把 start/end 写入 report。

### 6.8 明确不改

| 路径 | 原因 |
|---|---|
| `adopt.py` 里 `normalized_body != clean` 那一行 | 裁判保留；组装后必相等 |
| `adopt.py` set ≠ profile | N-A2 无切刀时仍应红 |
| `layered_content.py` 字段闭集 | 组装输出必须仍满足它 |
| C / summarizer v2 | `T-O-375` 纪律延续 |
| stub / salvage 白名单 | 禁止假绿、禁止换工人 |
| 同键 N-A5 / Q-A3 | 丢掉索引 |

---

## 7. 强制本地测试

```text
tests/unit/test_r5_assemble.py          # overlay_system_g0 + assemble_from_cuts 表
tests/unit/test_r5_cuts_contract.py     # 未知键 / 空刀 / 坐标键
tests/unit/test_ns1_prompt_bodies.py    # 纳入 cuts 提示词；无 MKB；无 layered 正例
tests/unit/test_ns1_prompt_catalog.py   # g1 == v5
tests/domain/test_architecture.py       # 叶包仍无 I/O；assemble 不在 lsrag_* 
tests/unit/test_r4_evidence_fixes.py    # 回归：admit-fail invocation 仍在
```

禁止用「先跑一格 live」代替上表。

---

## 8. 残差（写进 P6，不绑 P1/P2 完工）

| 残差 | 处理 |
|---|---|
| N-A6 `empty_result` | 再空则本族不再为它改 B；记 transport residual |
| N-A2 切刀仍空 | 标 `corpus-defer / 57KB`；禁止 v6 提示词 |
| A1/A4/A5g2 | 仍默认不开 |
| 检索 `channel=None` | 另 AP，不进 R5 |

---

## 9. 范围控制

### 9.1 allowlist

`generation_assemble.py`；`_structurize` 调用点；`contracts/lsrag/cuts.py`；cuts JSON schema；g1 **v5** 新提示词 + catalog retire；R5 预检/RUN；单测；分析附录。

### 9.2 denylist

放宽 `adopt.py` / `layered_content.py` 拒绝式；改 stub；`rm` 库；同键重跑 N-A5/Q-A3；Mixin 拆除；YAML 工作流；把切刀 `start`/`end` 当 extra 证据；再写 v6「请务必切章」。

### 9.3 tripwire

diff 若改 `STRUCTURE_ANCHOR_MISSING` 的判定式 → 停。  
Q 格 `generate_pools` 含未声明 NI → 该格作废。  
Q-A3≠17 或 N-A5≠21 → `not-ready`。  
组装器出现在 `src/services/lsrag_*` → 停。

---

## 10. Live 预算（仅 P5，须业主令）

| 字段 | 上界 |
|---|---|
| 格子 | `N-A3,N-A6,N-A2,Q-A5` |
| 后缀 | `--suffix=-r5`（必须等号写法） |
| extras | `--no-extras` |
| 库 | 禁止删 |
| 停止 | serving 丢失、静默 salvage、jsonl 再 `collect-exception` 且库已终态 |

```bash
.venv/bin/python .experiment/0815/runs/MKB-0815-R2/collect.py \
  --cells N-A3,N-A6,N-A2,Q-A5 \
  --suffix=-r5 --no-extras --rerun
```

---

## 11. Commit 纪律（执行 P1–P3 时）

1. `feat(runtime): overlay system-owned g0 before structurize admit`
2. `feat(runtime): assemble layered JSON from quoted cuts`
3. `feat(prompts): documentation g1 v5 quoted-cuts envelope`
4. `test(r5): assemble/cuts/catalog guards`
5. `docs(eval): freeze R5 preflight`（P4）

禁止与 kernel 放宽混提。

---

## 12. Final verdict（本解法，不是 live 结论）

```text
problem              model copies full clean + cuts chapters in one shot
fix                  system writes g0; model quotes start/end; pipeline slices
kernel               reject predicates UNCHANGED
leaf I/O             UNCHANGED
serving              Q-A3 17 + N-A5 21 tripwire
prompt thickening    NOT the path (v3/v4 falsified)
live                 WAIT_OWNER after P1-P4 green
```

当前状态：

**`R5 LEDGER DRAFTED / NOT EXECUTED / NO NEW INGEST`**。
