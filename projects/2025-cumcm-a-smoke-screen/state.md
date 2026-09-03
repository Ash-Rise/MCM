# Current State

## Objective

独立完成 2025 CUMCM A：可信数值结果 → 正式冻结 → 只消费 frozen results 的 figures → paper.md → 经完整度与视觉检查的 paper.docx。

## Current Frontier

问题 1～5 的 best-found 已 accepted 并统一冻结；Q5 严格无效动作清理、冻结表格机械校验及第一版 figures 已完成。正式论文源 `paper/paper.md` 已完成，并针对 Q3 共享航迹耦合、Q4 独立组合条件和 Q5 联合优化意义作了聚焦修订，通过关键数值、约束、图路径和内容边界自审；已删除冻结后不再允许使用的 working → accepted/frozen 反向覆盖脚本。本轮按用户要求未生成 DOCX。

## Accepted

- DP-03/B1：问题 5 只按逐弹指派对象计入正式目标 $L_1+L_2+L_3$；B2 只作选后补充物理评价。
- Q1：完整圆柱遮蔽 1.391642669 s。
- Q2：完整圆柱遮蔽 4.588055444 s，作为有多起点、速度边界和高分辨率复核支撑的 best-found；不作全局最优声明。
- Q3：扩大航迹盆地后三弹均有正贡献，并集 6.689702644 s。
- Q4：三机各一弹，并集 11.397460410 s；独立分解、多起点和局部扰动审计均未发现更优解。
- Q5：删除 3 枚对 B1、B2 均严格零贡献的动作后，保留 11 弹共享航迹联合方案；B1 的 M1/M2/M3 分别为 20.960407101、7.672175015、2.427043957 s，总计 31.059626073 s。B2 选后复算同值。

## Frozen Results

- `results/frozen/q1.json`～`q5.json` 是后续数值主张的唯一输入。
- `results/frozen/result1.xlsx`～`result3.xlsx` 由对应 frozen JSON 直接生成，并已逐字段核对行数、指派、有效时长及运动/资源约束。
- 全部优化结果都只声称为当前证据下的 best-found，不声称全局最优。
- `figures/` 的三张第一版正式图只读取 frozen JSON，未调用求解器或改写正式结果。

## Next Actions

1. 如进入排版阶段，以当前 `paper/paper.md` 为正文权威，按当届官方规则生成并视觉复核 `paper.docx`。

## Boundaries

- 未查看公开题解、优秀论文、赛题讲评或外部已计算结果。
- `decisions.md` 只有 Accepted DP-03；历史 DP/pilot 细节不再进入执行前沿。
- 原件获取说明仍见题面 Markdown；若以后取得的组委会原件与当前镜像高影响内容不一致，停止下游工作并重新核对。
