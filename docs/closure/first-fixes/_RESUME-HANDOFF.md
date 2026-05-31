# first-fixes 执行进度 — 会话重启交接 (2026-05-31)

> 因执行会话 shell/IO 显示层持续不稳定（命令实际执行成功但输出间歇性延迟/串读/显示陈旧），
> owner 决定重启会话后继续。本文件是重启后的唯一恢复锚点。

## 已完成并提交 (HEAD = 858964a, main 分支, 工作树干净, 全量 `python3 -m pytest tests/` 退出码 0 = 65 passed)

| 阶段 | 状态 | 提交 | closure |
|------|------|------|---------|
| F1 时间与事务基座 | ✅ 收口 | `f46b86e` (+docs) | `docs/closure/first-fixes/FF-F1-closure.md` |
| F2 连接与装配 | ✅ 收口 | `df4de14` + `6f34150` | `FF-F2-closure.md` |
| F3 内核恢复+执行器契约 | ✅ 收口 | `2d289e9` + `858964a` | `FF-F3-closure.md` |

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

## 剩余工作 (todo #7-#19)
- **F4 适配层安全** (#7-8, in_progress, 尚未改任何代码): AP=`docs/action-plan/first-fixes/FF-F4-adapter-safety.md`。
  - F4-01 `filesystem_store.py` object_key 边界校验(_resolve_safe: 拒绝绝对路径/`..`段, resolve 后 is_relative_to(root)); put/get/exists/新增delete 统一走它。
  - F4-02 `ingestion/service.py` file_initiate filename basename 收口(static_initiate 复用)。
  - F4-03 `vector_sqlite_vec/store.py` rowid 单调不复用 + upsert 同 chunk_id 复用现有 rowid(消孤儿) + 软删后不重号删审计。注意:F3 已让 rag 用确定性 chunk_id=f"{run}:{idx}", 与此兼容。
  - F4-04 软/硬删统一(当前 vr 软删 deleted_at 但 chunk_embedding_index 硬删 DELETE)。
  - F4-05 `filesystem_store.delete` + `purge.py process_purge_requests` 接 object_store 删 uploads/static_files object_key。注意:purge.py 已被 F1/F3 改过(BEGIN IMMEDIATE 包裹 + 注释跨库 vec)。
  - F4-06 put_text 原子写(temp+os.replace)、get_text 受控异常。
  - F4-07 先红后绿: tests/unit/test_filesystem_store_paths.py + test_vector_store_rowid.py + tests/integration purge 删对象。攻击向量必含 `../escaped.txt /abs a/../../x`，pre-fix 必红。
- **F5 向量真实性** (#9-10): AP=FF-F5。Embedder adapter+本地确定性 1536 维 embedding(纯 Python, 词袋 hash 投影但**语义相关**: 同义/共词文本余弦更高, 非 SHA 噪声) 替换 `rag_vectorizer/embedder.py` 的 SHA 伪向量; VectorIndex 接口 + degraded fail-loud(`_fallback_vec_sql` 已是退化路径, 加 logger.warning); search 加 namespace_id/embedding_model 过滤([Q1][Q2])。
- **F6a 清洗器** (#11-12): AP=FF-F6a。action registry+dispatch; universal cleaner htmlCrawl 真实(stdlib html.parser 去标签留正文); chinatax provider 真实 ETL(可 mock 网络); 多 provider/PDF/浏览器/scatter 显式 degraded([Q3])。
- **F6b RAG 执行器** (#13-14): AP=FF-F6b。structurize 真实结构化(非朴素 split); construct chunk+summary 双通道; 独立 rag:vectorize step。注意 F3 已把 rag 执行器改成 ExecutorResult 契约——在此契约上增强, 勿回退终态归属。
- **F6c 认证配置** (#15-16): AP=FF-F6c。团队 API key 认证(中间件+create_api_key+team归属, api_keys 表已存在); 删 legacy 密码兼容声明统一 PBKDF2([Q6]); prompt_versions/provider_configs 接线。
- **F7 测试整合** (#17-18): AP=FF-F7。测试原语(冻结时钟/并发/恶意路径/向量真实性 fixtures); 去夹具掩盖; capstone A-J(tests/e2e); 断言强度门禁; closure 重定级(含更正 F1 fastapi 记录)。
- **#19 跨 F1-F7 全面审查+测试**, 对照 owner QnA 裁决, 向 owner 报告。

## 已知技术债/handoff(已在各 closure §4 记账)
- 跨库 vec 写不在 core 事务内(仅 core 侧原子) → F4 协调。
- restart force/kickstart 延后([Q4] 本轮仅 recovery, 已显式拒绝非 recovery mode)。
- F6 真实执行器建在 F3 的 `workflow_core/executors.py` ExecutorResult 契约上。
