# Current State

## Objective

独立完成 2025 CUMCM A：可信数值结果 → 正式冻结 → 只消费 frozen results 的 figures → paper.md → 经人工视觉验收的最终 paper.docx。

## Current Frontier

问题 1～5 的 best-found、冻结结果和正式 figures 均未改变。上一版 DOCX 的人工视觉验收失败，其 frozen 状态已撤销。当前 `paper/paper.md` 仅补强摘要并重组 Q3～Q5 宽表字段；新生成的 `paper/paper.docx` 是待人工验收的 candidate，不是 frozen artifact。candidate 共 17 页、9 张表、3 幅图和 255 个原生公式对象，全文统一纵向 A4；摘要首页、二三级标题左对齐、正文行距、宽表、图表和分页已完成机械检查与逐页 rendered review。自动检查通过不代表人工视觉验收通过。

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
- `paper/paper.md` 是正文内容 authority；`paper/paper.docx` 当前仅为 candidate，尚无已认可的最终版式文件。
- 转换清单 `paper/paper.conversion.json` 记录正文源、模板和后处理产物哈希。

## Next Actions

1. 由用户对 PR 中的 candidate DOCX 做最终肉眼验收；在明确接受前不得 merge、freeze 或宣布 DOCX 阶段完成。

## Boundaries

- 未查看公开题解、优秀论文、赛题讲评或外部已计算结果。
- `decisions.md` 只有 Accepted DP-03；历史 DP/pilot 细节不再进入执行前沿。
- 原件获取说明仍见题面 Markdown；若以后取得的组委会原件与当前镜像高影响内容不一致，停止下游工作并重新核对。
