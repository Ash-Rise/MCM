# Problem A: Ambulance Dispatch

暑期作业 A 题的终态解答，覆盖急救站服务分配、日常调度策略、事故情景和临时外援分析。2026 国赛模板只用于版式参考，本项目不声明为 2026 国赛参赛论文。

## 当前交付

- 正文内容权威：[paper/paper.md](paper/paper.md)
- 用户批准的 Word 版式基线：[paper/paper.docx](paper/paper.docx)
- Accepted Decisions：[decisions.md](decisions.md)
- 正式实现：[src/](src/)
- 冻结结果与复制级证据：[results/](results/)
- 正式图表：[figures/](figures/)
- 回归与模型合同测试：[tests/](tests/)

Git Tag [`v2.5`](https://github.com/Ash-Rise/MCM/releases/tag/v2.5) 对应用户批准的 A 题论文 V2.5 发布版。`main` 上的固定文件名表示当前仓库接口；历史版本由 Git Tag、Release 和提交历史保存。

## 结果与展示边界

- `results/task-1/`：任务一确定性正式结果。
- `results/task-2/`：调参、选中策略、复制级评价及聚合结果。
- `results/task-3/`：事故情景、复制级结果、响应面和临时外援结果。
- `src/generate_figures.py` 只读取上述冻结结果生成图表，不重新求解或覆盖正式结果。

批准的 `paper.docx` 保留 V2.5 的人工锁定表格与分页，尚未迁移到共享 YAML formatter。以后只有在论文需要实质修订时才迁移；跨项目方法和机器排版参数分别以[建模与论文方法手册](../../../../shared/templates/personal-modeling-playbook.md)和[共享 paper profile](../../../../shared/templates/personal-paper-profile.yaml)为准。

## Reproduction

Run commands from this directory:

```powershell
# Read-only validation of all frozen evidence.
python src/reproduce_all.py --project-root . --mode verify --scope all

# Rebuild aggregate tables and response surfaces from versioned replication data,
# regenerate figures, and then validate all three tasks.
python src/reproduce_all.py --project-root . --mode rebuild --scope all

# Optional full rerun, including the expensive stochastic experiments.
python src/reproduce_all.py --project-root . --mode full --scope all
```

`verify` 不运行长仿真，只重新计算确定性检查并核验冻结表、配对情景、硬约束和所需图表。`rebuild` 从版本化复制级结果重建聚合表与响应面并重新生成图；`full` 才会重新运行昂贵的随机实验。复制级 CSV 是正式科学证据，不是可随意删除的缓存。
