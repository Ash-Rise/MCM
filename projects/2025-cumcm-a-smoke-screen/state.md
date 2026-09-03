# Current State

## Objective

独立完成 2025 CUMCM A：可信数值结果 → 正式冻结 → 只消费 frozen results 的 figures → paper.md → 经完整度与视觉检查的 paper.docx。

## Current Frontier

问题 1～5 的 best-found 已 accepted 并统一冻结；下一步进入只消费 `results/frozen/` 的 figures。本轮未产生新 DP。

## Accepted

- DP-03/B1：问题 5 只按逐弹指派对象计入正式目标 $L_1+L_2+L_3$；B2 只作选后补充物理评价。
- Q1：完整圆柱遮蔽 1.391642669 s。
- Q2：完整圆柱遮蔽 4.588055444 s，作为有多起点、速度边界和高分辨率复核支撑的 best-found；不作全局最优声明。
- Q3：扩大航迹盆地后三弹均有正贡献，并集 6.689702644 s。
- Q4：三机各一弹，并集 11.397460410 s；独立分解、多起点和局部扰动审计均未发现更优解。
- Q5：14 弹共享航迹联合方案，B1 的 M1/M2/M3 分别为 20.960407101、7.672175015、2.427043957 s，总计 31.059626073 s。B2 选后复算同值。

## Frozen Results

- `results/frozen/q1.json`～`q5.json` 是后续数值主张的唯一输入。
- `results/frozen/result1.xlsx`～`result3.xlsx` 与冻结 JSON 一致，并与工作版字节相同。
- 全部优化结果都只声称为当前证据下的 best-found，不声称全局最优。

## Next Actions

1. figures 只读取 frozen results，不调用求解器。
2. 完成第一版后做 figure retrospective，区分图表设计与渲染样式问题。
3. 随后完成 paper.md 与 DOCX 冻结。

## Boundaries

- 未查看公开题解、优秀论文、赛题讲评或外部已计算结果。
- `decisions.md` 只有 Accepted DP-03；历史 DP/pilot 细节不再进入执行前沿。
- 原件获取说明仍见题面 Markdown；若以后取得的组委会原件与当前镜像高影响内容不一致，停止下游工作并重新核对。
