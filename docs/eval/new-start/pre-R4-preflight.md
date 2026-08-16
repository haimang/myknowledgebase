# pre MKB-0815-R4 · 发车前预检冻结

> **对象**：`MKB-0815-R4`（R3 RCA 后的闭集/证据面修复枪）
> **日期**：`2026-08-17`
> **作者**：`Grok`
> **文档性质**：`eval / preflight-freeze`（不是发车令）
> **文档状态**：`subjects-sealed / WAIT_OWNER`
> **上游**：`docs/eval/new-start/after-MKB-0815-R3-analysis.md` §9–§22
> **方法**：`.experiment/0815/runs/MKB-0815-R4/RUN.md`

## 0. 一句话

R4 **可以进入业主发车闸**。本文件 **不**授权 ingest。live 命令：

```bash
.venv/bin/python .experiment/0815/runs/MKB-0815-R2/collect.py \
  --cells N-A3,N-A6,N-A2,Q-A5 \
  --suffix=-r4 --no-extras --rerun
```

Q-A3 17 与 N-A5 21 必须保持。禁止 `rm` 库。`--suffix` 必须带等号。

## 1. 已落地的修复（R4-01..05）

| ID | 落点 |
|---|---|
| R4-01 | `_structurize` admit 拒绝时 stash failed invocation + report |
| R4-02 | process 成功 `UPDATE` 清 `error_code`/`error_message` |
| R4-03 | stage report `latency_ms` 用 monotonic |
| R4-04 | receipt `api_inference` → `adapter_kind=local_vllm` |
| R4-05 | `promptB.documentation.g1.v4.md`；catalog v4；v3 retired |

未做：R4-06 live、R4-07 金标、R4-08 封条。

## 2. 预检

权威记录：`.experiment/0815/runs/MKB-0815-R4/results/preflight.json`  
14/14 PASS。Turso：g1=v4，Q-A3=17，N-A5=21，零 `-r4` 键。通道烟测绿。

## 3. 业主发车核对单

- [x] R3 RCA 已写；R4 修复已测
- [x] 对象/方法已封
- [x] 两份 serving intact
- [x] `preflight.py` 全绿
- [ ] **业主点头** 后才跑冻结 collect
