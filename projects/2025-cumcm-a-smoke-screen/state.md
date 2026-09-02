# Current State

## Objective

独立完成 2025 CUMCM A：可信数值结果 → 正式冻结 → 只消费 frozen results 的 figures → paper.md → 经完整度与视觉检查的 paper.docx。

## Current Frontier

问题 1、2 已 accepted；问题 3～5 已有可信 working lower bounds 和工作版结果模板。下一步加强问题 3～5 的替代候选/扰动证据，决定是否接受并统一冻结数值结果。本轮未产生新 DP。

## Accepted

- DP-03/B1：问题 5 只按逐弹指派对象计入正式目标 $L_1+L_2+L_3$；B2 只作选后补充物理评价。
- Q1：完整圆柱遮蔽 1.391642669 s。
- Q2：完整圆柱遮蔽 4.588055444 s，作为有多起点、速度边界和高分辨率复核支撑的 best-found；不作全局最优声明。

## Working Results

- Q3：FY1 三弹，正式并集 6.360438477 s；四个高分辨率候选中当前值最高，第三弹在当前最优共享航迹上无正贡献。
- Q4：FY1～FY3 各一弹，三个区间互不重叠，并集 11.397460410 s。
- Q5：12 弹固定航迹扩展下界；B1 的 M1/M2/M3 分别为 18.485918080、7.672175015、2.427043957 s，总计 28.585137052 s。B2 选后复算同值，未参与排序。
- `results/working/result1.xlsx`、`result2.xlsx`、`result3.xlsx` 已从对应 working JSON 转录并重载校验；均未冻结。

## Next Actions

1. 对 Q3～Q5 做最小但足以改变接受判断的扰动与替代候选检查，重点审计 Q5 固定航迹贪心的遗漏空间。
2. 接受后统一生成 frozen results；冻结前不得把 working XLSX 当正式结果。
3. figures 只读取 frozen results，并在第一版后做 figure retrospective；随后完成论文与 DOCX 冻结。

## Boundaries

- 未查看公开题解、优秀论文、赛题讲评或外部已计算结果。
- `decisions.md` 只有 Accepted DP-03；历史 DP/pilot 细节不再进入执行前沿。
- 原件获取说明仍见题面 Markdown；若以后取得的组委会原件与当前镜像高影响内容不一致，停止下游工作并重新核对。
