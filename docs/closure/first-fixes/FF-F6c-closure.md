# [FF-F6c / 认证与配置] Closure

> 阶段: `first-fixes/FF-F6c — 认证与配置`
> 范围: `prompt_versions/provider_configs 读路径 + 团队 API key 认证 + 统一 PBKDF2（F6-07/09/11）`
> Close-type: `closed-with-explicit-deferrals`
> 状态: `closed`
> 日期: `2026-06-01` · 作者: `Opus 4.8`
> 关联 charter: `docs/design/first-fixes/initial-planning-by-opus.md（§6.6 F6-07/09/11 / §2.C [Q5][Q6]）`
> 关联 design: `N/A（消费冻结 [Q5][Q6][Q7]）`
> 关联 action-plan: `docs/action-plan/first-fixes/FF-F6c-auth-config.md（§11 已回填）`
> 关联 evidence: `inline §2 + AP §11.3`
> 关联 review: `docs/eval/first-code-review-plan/part-cr-5.md（R1 api_keys / R3 密码哈希）+ part-cr-2.md（R3 配置表零访问）`

---

## 0. 一句话 verdict

> F6c 收口：`prompt_versions`/`provider_configs` 从零访问接成读取访问层（`config_repo`，team 级优先回退全局）；团队 API key 认证全链路（generate `sm_` 明文 + sha256 hash 存储 + validate 中间件 + team 归属唯一取 api_keys.team_id + `POST /team/api-keys` owner-only）；auth 统一 PBKDF2 单路径（删 `_hash_legacy_password` 与 legacy rehash 死代码）；先红后绿 17 用例（含伪造/revoked/expired/非 owner/明文不入库攻击向量），全量 175→**192 passed**（exit 0）；close-type=closed-with-explicit-deferrals。

> **本阶段最关键的 known gap（对下游影响）**：
> 1. config_repo 已交付**可读载体**，但 F6a/F6b 消费侧（按配置选 provider/prompt）**未接线**——下游接线为 follow-up。
> 2. api_key **scope 级授权**本轮 OOS（只做认证 who，不做授权 what）；F6a htmlCrawl SSRF 仍未处置。

---

## 1. 工作项收口表

| Item | 状态 | 证据（commit + test + run-time） |
|------|------|----------------------------------------|
| P1-01/02 prompt_versions/provider_configs 读路径 | ✅ | `697dcb0 + test_config_repo(4) + 2026-06-01 04:10 UTC` |
| P2-01/02 api_keys 读写 + key 生成/hash（明文不入库） | ✅ | `697dcb0 + test_api_key(库内仅 hash) + 2026-06-01 04:10 UTC` |
| P2-03/04 validate_api_key 中间件 + team 归属 | ✅ | `697dcb0 + test_api_key_auth(valid/forged/revoked) + 2026-06-01 04:10 UTC` |
| P2-05 create_api_key 端点（owner-only） | ✅ | `697dcb0 + test_api_key_auth::test_non_owner_cannot_create_key + 2026-06-01 04:10 UTC` |
| P3-01/02 统一 PBKDF2（删 legacy 死代码） | ✅ | `697dcb0 + test_auth_pbkdf2(4) + 2026-06-01 04:10 UTC` |

---

## 2. Evidence / Validation 矩阵

| 验证项 | 命令 / 证据 | 结果 | 覆盖范围 |
|--------|-------------|------|----------|
| 配置载体读路径 | `pytest tests/unit/test_config_repo.py` | `4 passed`；active/多版本最新/team 回退全局/settings 解析 | config_repo |
| api_key 生成/hash/明文不入库 | `pytest tests/unit/test_api_key.py` | `5 passed`；sm_ 前缀/hash 不可逆/**库内仅 hash 无明文**/validate 往返/伪造-revoked-expired 拒 | AuthService api_key |
| api_key 认证端到端 + 攻击向量 | `pytest tests/integration/p2_control_plane/test_api_key_auth.py` | `4 passed`；owner 创建+X-Api-Key/ApiKey 鉴权/伪造-缺失 401/revoked 401/非 owner 403 | deps + 端点 + auth |
| 统一 PBKDF2 | `pytest tests/unit/test_auth_pbkdf2.py` | `4 passed`；无 _hash_legacy_password 符号/非 PBKDF2 拒/PBKDF2 注册登录/错密码拒 | auth verify/login |
| 全量回归 | `python3 -m pytest tests/` | `192 passed`（exit 0；175+17）；Bearer session 路径无回归 | 全仓 |

---

## 3. Hard-gate 判定

| Gate | 判据 | 实测 | 判定 |
|------|------|------|------|
| 有效 key 创建并通过校验、解析正确 team | owner 创建 + key 鉴权通过 | T05/T06 绿 | ✅ PASS |
| 攻击向量全拒 | 伪造/无效/revoked/expired/非 owner + 明文不入库 | T04/T07/T08 绿 | ✅ PASS |
| 配置载体可读 + auth 单路径 PBKDF2 | 读路径返回 active + 非 PBKDF2 拒 | T01/T02/T09 绿 | ✅ PASS |

---

## 4. Deferred / Carry-over ledger

| 项 | 类型 | 当前状态 | 承接位置 / 触发条件 | 责任方 |
|----|------|----------|---------------------|--------|
| config_repo 下游消费接线（F6a/F6b 按配置选 provider/prompt） | C（handoff） | 载体可读已交付；消费侧仍用内置 registry 默认 | F6a/F6b 需运行期改配置时 | F6a/F6b/下一轮 |
| api_key scope 级授权（O1） | A（OOS） | scopes_json 仅落库，不做端点级强制 | 产品提出按 scope 限权 | 下一轮 |
| prompt/provider 写入/激活端点（O3） | B（主动 defer） | 仅读载体 | 运行期改配置时 | 下一轮 |
| 其余缺失 legacy RPC（reset_password 等, O2） | A（OOS） | 未做 | final §3.2 [O4] | 下一轮 |
| workflow_step_links（O4） | A（归 FF-F3） | F3 已接线 | — | F3 |
| htmlCrawl SSRF 防护（F6a handoff） | C（handoff） | 仍未处置 | 下一轮安全 | 安全/下一轮 |
| 端到端 api_key 投递 ingestion mega | C（handoff） | 单端点鉴权已验 | `FF-F7` capstone 多 team 隔离步 | F7 |

---

## 5. 诚实收口声明

| 收口纪律 | 兑现声明 |
|----------|----------|
| 每个 ✅ 归类 5 态 | ✅ — §1 全部 **verified**（commit + test + run-time 四元组齐全，含攻击向量先红后绿） |
| ✅ 证据为四元组，无裸 file:line | ✅ |
| scope diff 守卫（仅改 in-scope 文件，无越界） | ✅ — 改 config(+repo 新)/auth/team/deps/team 路由，均在 §3 工作总表 + §7.1 锚表内 |
| deferred 已三分类（A/B/C）且每项有承接位置 | ✅ — §4 七项均标 A/B/C + 承接位置 |
| owner-test 项未经复测标 ⏸ | N/A — 无 owner-test 项（攻击向量本地可复现） |

> **诚实附注**：
> 1. **明文 key 不入库经测试断言**：`test_create_api_key_stores_only_hash_not_plaintext` 实测 `SELECT * FROM api_keys` 全列无明文、仅 sha256 hash（⛔1 真实兑现，非声明）。
> 2. **config_repo 已交付但下游未接线**：本 AP 交付可读配置载体（F6-09 前置满足）；F6a/F6b 当前仍用内置 registry/规则默认，按配置驱动选择的消费侧接线如实标为 §4 handoff，不冒领"配置已驱动去桩"。
> 3. **Bearer 优先、api_key 并存**：既有 session 鉴权零改动（⛔6），api_key 为新增并存分支；全量 192 含 p2/p3/p5 既有 Bearer 路径无回归。
> 4. **统一 PBKDF2 先红后绿真实**：删除前 legacy sha256 hash 经 `_verify_password` 回退被接受（红基线）；删除后 `test_non_pbkdf2_hash_rejected` 断言一律 False（绿）。
> 5. 全量 192 passed 含 F1-F6b 既有 175 用例无回归。
