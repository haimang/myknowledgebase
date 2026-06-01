# first-fixes 执行进度 — 会话重启交接 (2026-05-31)

> 因执行会话 shell/IO 显示层持续不稳定（命令实际执行成功但输出间歇性延迟/串读/显示陈旧），
> owner 决定重启会话后继续。本文件是重启后的唯一恢复锚点。

## 已完成并提交 (main 分支, 工作树干净, 全量 `python3 -m pytest tests/` 退出码 0 = **115 passed**, F1-F4)

| 阶段 | 状态 | 提交 | closure |
|------|------|------|---------|
| F1 时间与事务基座 | ✅ 收口 | `f46b86e` (+docs) | `docs/closure/first-fixes/FF-F1-closure.md` |
| F2 连接与装配 | ✅ 收口 | `df4de14` + `6f34150` | `FF-F2-closure.md` |
| F3 内核恢复+执行器契约 | ✅ 收口 | `2ff96cb` + `858964a` + `e9a1c70`(test_t05 适配契约+SHA更正) | `FF-F3-closure.md` |
| F4 适配层安全与数据完整性 | ✅ 收口 | `1a568d3`(代码+50测试) + docs | `FF-F4-closure.md` |
| F5 向量真实性与检索 | ✅ 收口 | `7a70408`(代码+22测试) + docs | `FF-F5-closure.md` |

> 重启时以 `git log --oneline` 实际 HEAD 为准（交接提交后 HEAD 在 `e9a1c70` 之后的 handoff 提交上）。
> 验证命令：`cd /workspace/repo/smind-family && python3 -m pytest tests/ -q` 应 **65 passed**（`--co` 实测 65 个用例、无 skip/xfail）。早前文档/提交信息中的"66 passed"为虚高记账，已据实更正为 65。

- F1/F2/F3 的 action-plan §11 执行日志均已回填。
- 三阶段 todo (#1-#6) 已标 completed。

## 环境关键事实（重启后无需再排查）
- **用系统 `python3`（非 venv）**。已装：fastapi 0.136.3 / pydantic 2 / pydantic_settings / starlette / httpx。
- **离线缺失（无外网、不可装）**：numpy / uvicorn / bs4 / lxml / requests / sentence_transformers / sqlite_vec。
  → F5 embedder 必须用纯 Python/stdlib 自造确定性 1536 维"本地小模型"（非 SHA 伪向量）；F6 htmlCrawl 必须用 `html.parser`（stdlib）而非 bs4。
- workspace 包已 editable 安装（import 解析到 `packages/*/src`、`apps/*/src`）。
- 跑测试：`cd /workspace/repo/smind-family && python3 -m pytest tests/ -q`。
- **FF-F1 closure 里"fastapi 缺失致 p2-p7 不可运行"的推测不成立**（F2 已证 fastapi 可用、65 passed）；F7 需统一回链更正 F1 记录（已在 FF-F2 closure §4 记为 handoff）。

## 执行纪律（owner 已确认）
- **不要用收尾子代理**（在本环境会陷入 tool-use 循环）。主轨直接做，**每次少量、串行**的工具调用。
- IO 不稳：命令输出重定向到 `/tmp/x.txt` 再 `cat`/Read；重要结论（commit SHA、测试计数、干净树）用独立小命令多次确认。
- 严守 owner 流程：每阶段 STEP1 重拉上下文(action-plan + owner-gated-qna + 对应 part-cr) → STEP3 完整开发 → STEP4 先红后绿测试↔修复 → STEP5 回填 AP §11 + 写 closure(模板 docs/templates/closure.md 子阶段档 §0-5) + 提交。
- commit 尾行：`Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`。

## 剩余工作 (todo #11-#19)
- **F4 适配层安全** ✅ 已收口 (`1a568d3`): _resolve_safe 双层路径封堵 / rowid 单调不复用+复用 / 软删统一 / purge 删对象(uploads+static_files+artifacts) / 原子写+受控异常。50 新测先红后绿, 全量 115 passed。详见 `FF-F4-closure.md`。
  - F4 给 F5 留的前序: rowid 单调来源 = vector_records 含软删 MAX+1 (前提 delete 不硬删 vr 行)；search 仍缺 namespace/model 过滤(R10→F5-03)；embedding_dimension 写死 1536、cosine 截断 min(len)(R7→F5)。
- **F5 向量真实性** ✅ 已收口 (`7a70408`): LocalEmbedder 词袋 feature-hashing(1536维,共词余弦更高) 替 SHA; embed_text 委托之、写/查同实例; embed_text_fake 降级; vec0 degraded fail-loud + VectorIndex 接口(BruteForceVectorIndex); search 增 namespace/model 过滤 + distance_metric 读配置。详见 `FF-F5-closure.md`。
  - F5 给下游留: F6b rag:vectorize 直接用 `default_embedder()`(name=`local-bow-hash-v1`); 真实神经 embedding/vec0/外部 API 均技术债 handoff; **F7-05 须把 P4/P5 vector/retrieval 假绿 ✅ 重定级为 degraded**。
- **F6a 清洗器** (#11-12): AP=FF-F6a。action registry+dispatch; universal cleaner htmlCrawl 真实(stdlib html.parser 去标签留正文); chinatax provider 真实 ETL(可 mock 网络); 多 provider/PDF/浏览器/scatter 显式 degraded([Q3])。
- **F6b RAG 执行器** (#13-14): AP=FF-F6b。structurize 真实结构化(非朴素 split); construct chunk+summary 双通道; 独立 rag:vectorize step。注意 F3 已把 rag 执行器改成 ExecutorResult 契约——在此契约上增强, 勿回退终态归属。
- **F6c 认证配置** (#15-16): AP=FF-F6c。团队 API key 认证(中间件+create_api_key+team归属, api_keys 表已存在); 删 legacy 密码兼容声明统一 PBKDF2([Q6]); prompt_versions/provider_configs 接线。
- **F7 测试整合** (#17-18): AP=FF-F7。测试原语(冻结时钟/并发/恶意路径/向量真实性 fixtures); 去夹具掩盖; capstone A-J(tests/e2e); 断言强度门禁; closure 重定级(含更正 F1 fastapi 记录)。
- **#19 跨 F1-F7 全面审查+测试**, 对照 owner QnA 裁决, 向 owner 报告。

## 已知技术债/handoff(已在各 closure §4 记账)
- 跨库 vec 写不在 core 事务内(仅 core 侧原子) → F4 协调。
- restart force/kickstart 延后([Q4] 本轮仅 recovery, 已显式拒绝非 recovery mode)。
- F6 真实执行器建在 F3 的 `workflow_core/executors.py` ExecutorResult 契约上。
