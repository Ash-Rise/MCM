# W1 主张—证据大纲（任务一、任务二阶段稿）

## 论文定位与统一口径

- 交付：中文 Word 暑期作业论文；借用用户提供的 2026 数学建模国赛 Word 模板版式，不声明参赛。
- 原题：`../../../problem-statements/problem-a-ambulance-dispatch-statement.docx`，SHA-256 为 `5F5079815AB8AD6592FEE7A4B0B8B01A5DF8865983A2871C324B6AB772C39F2D`。
- 权威模型合同：`analysis/modeling-report.md`；术语合同：`analysis/terminology.md`。
- 本阶段唯一证据核验命令：`python src/reproduce_all.py --project-root . --mode verify --scope q1-q2`；绑定文件：`results/复现清单.json`。该入口不读取、聚合或验证旧任务三产物。
- 统一响应时间：等待 + 3 min 准备 + 45 km/h 行驶；45 min 是接受派车后的完整车辆占用周期。
- 区域中心仅为聚合需求代表点；3 km 是任务一名义规划服务半径，0.75 km 是包含 3 min 准备后的严格 4 min 中心代理诊断半径。
- 本阶段Word完整回答任务一和任务二；任务三只保留连续时长合同与“待计算”说明，不写旧六节点数值、旧图或效果结论。

## 摘要拟用主张

| 主张 | 数值 | 结果证据 | 模型/代码证据 | 拟入文图表 |
|---|---|---|---|---|
| 六站全部启用且满配 | 配车 `(3,2,2,2,1,2)` | `results/task-1/summary.json`；`site_solution.csv` | 报告 3.2--3.4；`solve_q1()` | 表3；图3 |
| 任务一最优运输分配 | 总距离 131.819720 km·次/日，均距 0.941569 km | `results/task-1/summary.json`、`assignment.csv` | 报告 3.4--3.6；`solve_q1()` | 表4；图2 |
| 任务一覆盖率需分口径 | 3 km 可执行覆盖 86.429%，严格 0.75 km 中心代理 60.714%，潜在 3 km 覆盖 97.143% | `results/task-1/summary.json` | 报告 2.3、3.7 | 图4 |
| 日常主策略为 B | 平均响应 5.3432 min，A 为 5.6142 min；差值 -0.2711 min，95% CI `[-0.3116,-0.2305]` | `results/task-2/final_summary.csv`、`final_paired_response.csv` | 报告 4.6、4.9；`simulate()`、`_choose_b()` | 表6；图8、图9 |
| 显式备用配置为 C | S3 固定 1 辆备用，`tau=7 min`；平均响应 5.5872 min | `results/task-2/selected_policy.json`、`final_summary.csv` | 报告 4.7；`_choose_c()` | 表6；图7、图9 |

## 第一问：容量约束站点—车辆—服务分配

### 必须回答的结论

1. 日需求 140 次/日必须完全覆盖；每车 12 次/日，因此至少需要 `ceil(140/12)=12` 辆车。
2. 六站停车容量之和恰为 12，故所有站点均启用并满配，配车具有唯一性；这不是经验评分结果。
3. 固定配车后，问题约化为容量约束运输型线性规划；第一层最小化加权出车距离，第二层在距离最优面上最大化 3 km 规划覆盖。
4. 区域 7、8、9 的需求需分流；S2 留有 4 次/日余量，其余站点达到容量上限。
5. 最近医院距离不进入派车距离；加入任务一目标只形成由需求守恒固定的常数项，正文仅作为理想行驶链条补充指标解释。

### 公式落点

- 距离：`d_ij=sqrt((x_i-X_j)^2+(y_i-Y_j)^2)`。
- 第一层目标：`min sum_i sum_j d_ij x_ij`。
- 约束：需求守恒、`sum_i x_ij <= 12 v_j`、`y_j <= v_j <= vbar_j y_j`、`sum_j v_j <= 12`。
- 必要性：`140 <= 12 sum_j v_j` 与 `sum_j vbar_j=12`。
- 第二层目标：固定 `D<=D*+epsilon` 后最大化 `sum_i sum_j 1(d_ij<=3)x_ij`。
- 静态下界：`3+60 dbar/45=4.255426 min`，明确不得作为任务二答案。

### 证据位置

- 表：`results/task-1/site_solution.csv`、`assignment.csv`、`summary.json`。
- 图：图1=`raw_q1_spatial.png`（输入空间）、图2=`process_q1_assignment_heatmap.png`（运输分配）、图3=`result_q1_site_capacity.png`（容量必要性）、图4=`result_q1_coverage.png`（覆盖口径）。
- 代码：`src/ambulance_model.py::read_problem`、`solve_q1`；复现核对：`src/reproduce_all.py::verify_q1`。
- 验证：需求残差 0，容量超限 0，MILP 与约化 LP 目标差 0。

## 第二问：条件 NHPP 与连续多日离散事件仿真

### 必须回答的结论

1. 原题没有逐时历史记录，双高斯仅是透明合成的日内强度形状；每天总呼叫严格固定为 140，条件 NHPP 只随机化到达时刻，区域标签概率为 `q_i/140`。
2. 车辆、队列和未完成任务跨午夜继承；00:00 只重置日接单计数；最后统计日停止新增呼叫后排空既有任务。
3. A 为全局合法车辆中就近派车；B 在当前绕行限制内，最小化当前额外响应、未来 45 min 累计响应损失和日负荷惩罚；C 是单独的固定备用方案，不与 B 混为一个策略。
4. B 的筛选参数为 `(beta,delta)=(4,2)`，日常主方案平均响应 5.3432 min；相对 A 的平均响应、P95、等待、延迟成本和积压均改善。
5. C 的配置为 `r=(0,0,1,0,0,0)`、`tau=7 min`；它用于满足“备用车辆配置”要求，不宣称全局最优，也不替代总体更优的 B。
6. 延迟惩罚按 `200 max(T_resp-4,0)` 元/次；B 平均每次为 358.44 元，日均 50181.83 元。

### 公式落点

- 条件 NHPP：`lambda_i(t)=q_i f(t mod 24)`，`int_0^24 f(t)dt=1`，并给定 `N_d=140`。
- 周期双高斯：周期核 `G`、未归一化 `g` 与归一化 `f`。
- 响应：`T_resp=T_wait+3+60d/45`。
- B：`Delta T_ea`、`C_a(t)` 的 45 min 积分、`B_a=(n_ad+1)/12`、`J_ea=Delta T_ea+C_a+beta B_a` 与 `Delta T_ea<=delta`。
- C：常规车预测响应 `T_hat_reg` 与释放条件 `T_hat_reg>tau`。
- 统计：复制级成对差 `Delta_m=M_B,m-M_A,m` 与 95% t 区间。

### 证据位置

- 表：`results/task-2/selected_policy.json`、`final_summary.csv`、`final_paired_response.csv`。
- 图：图5=`raw_q2_nhpp_intensity.png`（合成强度）、图6=`process_q2_b_grid.png`（B参数筛选）、图7=`process_q2_c_screen.png`（C配置筛选）、图8=`result_q2_multi_metric.png`（B相对A的多指标方向）、图9=`result_q2_paired_difference.png`（共同随机数下成对差）。绝对均值及95%区间放入表6，故`result_q2_mean_response.png`保留为候选图但不进入阶段稿。
- 代码：`generate_calls()`、`simulate()`、`cumulative_response_loss()`、`_choose_a()`、`_choose_b()`、`_choose_c()`；复现核对：`verify_q2()`。
- 验证：30 个最终复制，每复制预热 30 天、统计 30 天和 4200 次呼叫；策略共享同一呼叫流；单车单日不超过 12 次。

## 第三问：本阶段仅冻结模型合同

### 必须回答的结论

1. 事故区遍历 10 个区域，持续时间是连续变量 $H\in[0.5,12]$ h；事故区总强度为正常的 5 倍，起点取持续时间相关的最不利窗口 $t^*(H)$。
2. `B_N` 沿用日常强度；`B_E` 只在已识别事故区间内将事故区未来强度乘 5 写入 B 的 45 min 前瞻损失。车辆、FCFS、45 min 占用、`(beta,delta)` 和日 12 次上限均不变。
3. 事故结束后立即恢复 `B_N`；事故期到达但尚未派出的呼叫继续计算完整响应，事故结束后的新呼叫不进入任务三评价。
4. 有限时长节点只作为自适应数值设计，从六个初始节点出发，在高曲率或高不确定区间补点；正式报告连续响应面与复制级置信带。
5. 题面没有事故持续时间分布，不跨时长等权合成总体效果；任务三数值结果、最不利区域和改善幅度均待重算。

### 公式落点

- 事故增量强度：`lambda_extra_k(t)=4 q_k f(t mod 24)`，使总强度为正常 5 倍。
- 压力窗：`t^*(H)=argmax_s int_s^(s+H) f(t mod 24)dt`。
- 连续曲线：`Tbar_k(H), P95_k(H), C4_k(H), Qmax_k(H)`，附复制级置信带。

### 证据位置

- 模型合同：`analysis/modeling-report.md` 7.1--7.4、`analysis/terminology.md` 第8节。
- 阶段稿说明：不引用 `results/task-3/` 和旧任务三图；后续完成自适应响应面、M1/P1/P2/W1复验后再补写结果章节。

## 参考文献与章节落点

1. Matteson et al. (2011), DOI `10.1214/10-aoas442`：问题分析与任务二，支撑 EMS 呼叫使用时变计数到达率建模；不继承其数据和拟合方法。
2. Jánošíková et al. (2021), DOI `10.1186/s12942-021-00285-x`：任务一，支撑覆盖率与响应/距离指标分开报告。
3. Wu and Hwang (2009), DOI `10.1111/j.1553-2712.2009.00583.x`：任务二，支撑静态常驻配置下用离散事件仿真平衡车辆可用性与需求。
4. Yang et al. (2019), DOI `10.1016/j.jmse.2020.01.004`：任务二与模型评价，支撑在时空随机需求下进行仿真优化。

四条文献均由 OpenAlex 与 AnySearch 交叉匹配，并通过 Crossref DOI 元数据核对题名、作者、年份、期刊、卷期和页码；正文只陈述其方法适用性，不外推其数值结论。

## 拟定正文结构与图表数量

1. 摘要与关键词。
2. 问题重述、问题分析。
3. 模型假设与符号说明。
4. 任务一：MILP/运输 LP、必要性证明、结果和覆盖口径（4 图、2 表）。
5. 任务二：条件 NHPP、事件系统、A/B/C、参数与最终评价（5 图、2--3 表）。
6. 任务三后续工作：只列连续时长权威合同和待计算项，不列结果图表。
7. 前两问模型检验、优缺点与适用边界。
8. 参考文献与前两问复现说明。

阶段稿固定使用任务一4幅、任务二5幅正式图，6--8个可编辑表和15个以上原生OMML公式；任务一、任务二均有原始、过程和结果证据，图号—文件名—章节映射见各问证据位置，所有编号连续且均在正文引用。任务三图表待正式重算后补入最终稿。
