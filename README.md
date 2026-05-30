# smind-family

`smind-family` 正在按 `docs/action-plan/P0.md ~ P7.md` 进行 Python 模块化单体重构。

## 目录边界

- `apps/`: 运行入口（API / worker / CLI）
- `packages/`: 业务与基础能力包
- `tests/`: 测试
- `tools/`: 工具与脚本
- `data/`: 本地数据目录（db / objects / logs / tmp）
- `legacy-family/`: **只读迁移参考**，不承接新功能开发

## P0 基础命令

```bash
bash tools/scripts/bootstrap.sh
bash tools/scripts/smoke.sh
```

## 运行入口

```bash
python -m smind_api.main
python -m smind_worker.main --once
python -m smind_cli.main --help
```

