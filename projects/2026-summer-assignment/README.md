# 2026 Summer Assignment

本目录保存 A、B、C 三道题的权威题面与三套已完成解答。原始 DOCX 控制题目事实；Markdown 版本只作为机器读取接口，任何差异均以 DOCX 为准。

## 题面

- A：[急救站选址与调度题面](problem-statements/problem-a-ambulance-dispatch-statement.docx)
- B：[冷链配送题面 DOCX](problem-statements/problem-b-statement.docx) · [机器读取版](problem-statements/problem-b-statement.md)
- C：[光伏诊断题面 DOCX](problem-statements/problem-c-statement.docx) · [机器读取版](problem-statements/problem-c-statement.md) · [配套数据 DOCX](problem-statements/problem-c-supporting-data.docx) · [配套数据机器读取版](problem-statements/problem-c-supporting-data.md)

## 解答与正式复现入口

| 题目 | 终态解答 | 正式模型/结果入口 | 当前论文 |
|---|---|---|---|
| A | [problem-a-ambulance-dispatch](solutions/problem-a-ambulance-dispatch/README.md) | `src/reproduce_all.py`，支持只读验证、聚合重建和完整重跑 | [paper.md](solutions/problem-a-ambulance-dispatch/paper/paper.md) · [paper.docx](solutions/problem-a-ambulance-dispatch/paper/paper.docx) |
| B | [problem-b-cold-chain-routing](solutions/problem-b-cold-chain-routing/) | `src/solve_problem_b.py`，完整枚举并生成三个正式结构化结果 | [paper.md](solutions/problem-b-cold-chain-routing/paper/paper.md) · [paper.docx](solutions/problem-b-cold-chain-routing/paper/paper.docx) |
| C | [problem-c-pv-diagnostics](solutions/problem-c-pv-diagnostics/) | `src/reproduce_all.py` 生成正式结果；`src/generate_evidence.py` 只消费结果生成证据与图 | [paper.md](solutions/problem-c-pv-diagnostics/paper/paper.md) · [paper.docx](solutions/problem-c-pv-diagnostics/paper/paper.docx) |

从各解答目录运行：

```powershell
# A：验证全部冻结结果和图表证据
python src/reproduce_all.py --project-root . --mode verify --scope all

# B：正式求解；随后可独立生成图表和 DOCX
python src/solve_problem_b.py
python src/plot_problem_b.py
python src/build_paper.py

# C：正式结果；随后从冻结结果生成 evidence/figures
python src/reproduce_all.py
python src/generate_evidence.py
```

三题均已完成 terminal artifact closure：`decisions.md` 保存仍有效的重要决策，`results/` 保存正式数值或其明确证据视图，`paper/` 保存当前论文；阶段 scaffolding、临时摘要和 QA 文件不属于当前接口。
