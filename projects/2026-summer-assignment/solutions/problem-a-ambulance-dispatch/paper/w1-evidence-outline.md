# W1 主张—证据大纲（完整三问）

## 论文定位与统一口径

- 交付：中文 Word 暑期作业论文；借用用户提供的 2026 数学建模国赛 Word 模板版式，不声明参赛。
- 原题：`../../../problem-statements/problem-a-ambulance-dispatch-statement.docx`，SHA-256 为 `5F5079815AB8AD6592FEE7A4B0B8B01A5DF8865983A2871C324B6AB772C39F2D`。
- 权威模型合同：`analysis/modeling-report.md`；术语合同：`analysis/terminology.md`。
- 唯一证据核验命令：`python src/reproduce_all.py --project-root . --mode verify --scope all`；绑定文件：`results/复现清单.json`。
- 统一响应时间：等待 + 3 min 准备 + 45 km/h 行驶；45 min 是接受派车后的完整车辆占用周期。
- 区域中心仅为聚合需求代表点；3 km 是任务一名义规划服务半径，0.75 km 是包含 3 min 准备后的严格 4 min 中心代理诊断半径。
- 最终Word完整回答三问；任务三有限节点只作为连续响应面的数值设计，不把插值写成精确连续解，也不跨事故时长汇总总体效果。

## 摘要拟用主张

| 主张 | 数值 | 结果证据 | 模型/代码证据 | 拟入文图表 |
|---|---|---|---|---|
| 六站全部启用且满配 | 配车 `(3,2,2,2,1,2)` | `results/task-1/summary.json`；`site_solution.csv` | 报告 3.2--3.4；`solve_q1()` | 表2；图3 |
| 任务一最优运输分配 | 总距离 131.819720 km·次/日，均距 0.941569 km | `results/task-1/summary.json`、`assignment.csv` | 报告 3.4--3.6；`solve_q1()` | 表3；图2 |
| 任务一覆盖率需分口径 | 3 km 可执行覆盖 86.429%，严格 0.75 km 中心代理 60.714%，潜在 3 km 覆盖 97.143% | `results/task-1/summary.json` | 报告 2.3、3.7 | 图4 |
| 日常主策略为 B | 平均响应 5.3432 min，A 为 5.6142 min；差值 -0.2711 min，95% CI `[-0.3116,-0.2305]` | `results/task-2/final_summary.csv`、`final_paired_response.csv` | 报告 4.6、4.9；`simulate()`、`_choose_b()` | 表4、表5；图8、图9 |
| 显式备用配置为 C | S3 固定 1 辆备用，`tau=7 min`；平均响应 5.5872 min | `results/task-2/selected_policy.json`、`final_summary.csv` | 报告 4.7；`_choose_c()` | 表4、表5；图7、图9 |
| 事故压力由区域与持续时间主导 | 在每个时长内先按种子平均10个事故区，$B_N$ 全市平均响应由 $H=0.5$ h 的 6.1706 min 上升到 $H=12$ h 的 31.6386 min；R1为最高压力区，R6/R2/R1分别代表低/中/高压力 | `results/task-3/citywide_duration_table.csv`、`response_surfaces.csv` | 报告 7.1--7.4；`build_citywide_duration_table()`、`build_response_surfaces()` | 表7；图10--图12 |
| 事故感知预测只产生局部小幅改善 | $B_E-B_N$ 的全市平均差在各节点仅为 $-0.0981$ 至 $0.0264$ min且95%区间均跨0；按10个事故情景中的全部事故区呼叫加权后，$H=8,10,11$ h分别改善 0.1519、0.0941、0.1965 min，95%区间不跨0 | `results/task-3/scoped_paired_response_surfaces.csv` | `build_scoped_paired_surfaces()`；共同随机数、复制级t区间 | 表8；图13 |

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

- 表：表2=`results/task-1/site_solution.csv`列出站点配置与负荷；表3=`assignment.csv`列出非零运输分配；`summary.json`提供汇总校验。
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

- 表：表4=`results/task-2/final_summary.csv`与`final_paired_response.csv`列出A/B/C样本外评价；表5=`selected_policy.json`列出日常策略B和固定备用策略C的最终执行规则。
- 图：图5=`raw_q2_nhpp_intensity.png`（合成强度）、图6=`process_q2_b_grid.png`（B参数筛选）、图7=`process_q2_c_screen.png`（C配置筛选）、图8=`result_q2_multi_metric.png`（B相对A的多指标方向）、图9=`result_q2_paired_difference.png`（共同随机数下成对差）。绝对均值及95%区间放入表4，故`result_q2_mean_response.png`保留为候选图但不进入最终正文。
- 代码：`generate_calls()`、`simulate()`、`cumulative_response_loss()`、`_choose_a()`、`_choose_b()`、`_choose_c()`；复现核对：`verify_q2()`。
- 验证：30 个最终复制，每复制预热 30 天、统计 30 天和 4200 次呼叫；策略共享同一呼叫流；单车单日不超过 12 次。

## 第三问：连续事故时长下的应急响应

### 必须回答的结论

1. 事故区遍历 10 个区域，持续时间是连续变量 $H\in[0.5,12]$ h；事故区总强度为正常的 5 倍，起点取持续时间相关的最不利窗口 $t^*(H)$。
2. `B_N` 沿用日常强度；`B_E` 只在已识别事故区间内将事故区未来强度乘 5 写入 B 的 45 min 前瞻损失。车辆、FCFS、45 min 占用、`(beta,delta)` 和日 12 次上限均不变。
3. 事故结束后立即恢复 `B_N`；事故期到达但尚未派出的呼叫继续计算完整响应，事故结束后的新呼叫不进入任务三评价。
4. 有限时长节点只作为自适应数值设计。初始节点为 `0.5,1,2,4,8,12` h；两轮按曲率与95%置信带宽补入 `5,6,10,11` h，最终使用10个节点构造逐复制PCHIP响应面。
5. 每个节点包含10个事故区、10个种子和两个成对策略，共2000行复制结果；全部成对策略共享同一呼叫流，日12次上限和事故窗口边界字段均通过验证。
6. 在每个时长内先对同一种子的10个事故区取平均，再构造成对差。$B_N$ 的全市平均响应随压力总体上升：$H=0.5$ h为6.1706 min，$H=12$ h为31.6386 min；非单调局部波动来自持续时间相关的最不利起点与随机拥堵，不能解释为压力减弱。
7. $B_E$ 对全市均值的改变很小：10个节点的差值范围为 $[-0.0981,0.0264]$ min，逐时长95%置信区间均跨0。因此不能宣称总体显著改善。
8. 分域结果按每个种子中10个事故情景的全部相关呼叫加权。事故区呼叫在 $H=8,10,11$ h 时分别改善0.1519、0.0941、0.1965 min，对应95%区间分别为 `[0.0173,0.2866]`、`[0.0021,0.1860]`、`[0.0407,0.3523]` min；其余节点证据不足。非事故区大多数区间跨0，仅 $H=1$ h出现0.0362 min的小幅恶化，95%区间为 `[0.0016,0.0708]` min。
9. R1是最高压力区，R6、R2、R1分别用作低、中、高压力代表。区域与事故持续时间造成的容量压力远大于仅修改预测层带来的收益；$B_E$ 的价值是事故感知与局部保护，而不是替代增配车辆或外援。
10. 题面没有事故持续时间分布，因此不跨时长等权合成一个“总体应急效果”；PCHIP曲线和置信带是有限仿真点的数值近似，不写成精确连续解。

### 公式落点

- 事故增量强度：`lambda_extra_k(t)=4 q_k f(t mod 24)`，使总强度为正常 5 倍。
- 压力窗：`t^*(H)=argmax_s int_s^(s+H) f(t mod 24)dt`。
- 连续曲线：`Tbar_k(H), P95_k(H), C4_k(H), Qmax_k(H)`，附复制级置信带。
- 逐复制插值：对每个种子和情景的节点值构造 `PCHIP(H)`，再在每个 $H$ 上跨复制计算均值与t型95%置信带；策略差先在共同随机数下计算 $B_E-B_N$。
- 分域成对效应：在固定 $H$、种子和策略内先汇总10个事故情景中的全部事故区呼叫或非事故区呼叫，按呼叫数加权得到分域均值，再计算共同随机数下的 $B_E-B_N$。零呼叫情景以零权重进入且10区完整性被强制校验；若一个种子在某节点的全10区合计仍为零，则该种子不能形成完整PCHIP曲线，故非事故区有效复制数为9。

### 证据位置

- 模型合同：`analysis/modeling-report.md` 7.1--7.4、`analysis/terminology.md` 第8节。
- 表：表6=`results/task-3/adaptive_design.csv`列出自适应补点设计；表7=`citywide_duration_table.csv`按时长列出 $B_N/B_E$ 全市平均响应与成对差；表8=`scoped_paired_response_surfaces.csv`列出事故区/非事故区成对差及95%区间。
- 图：图10=`raw_q3_incident_load.png`（连续预期新增呼叫曲线与采样点），图11=`process_q3_duration_zone.png`（全10区响应面与置信带宽诊断），图12=`result_q3_response_curve.png`（R6/R2/R1低中高压力曲线），图13=`result_q3_paired_effect.png`（逐时长分域成对效应）。
- 代码：`run_emergency_experiments.py` 的 `worst_start_hour()`、`_run_scenarios()`、`build_response_surfaces()`、`build_scoped_paired_surfaces()`；复现核对：`verify_q3()`。
- 禁用证据：旧的 `aggregate_absolute_metrics.csv`、`aggregate_paired_effects.csv`、`paper_metrics.csv` 已移除，验证器会拒绝它们重新出现。

## 最终表号冻结

| 表号 | 表名 | 权威数据源 |
|---:|---|---|
| 表1 | 主要符号说明 | `analysis/terminology.md` |
| 表2 | 站点配置与服务负荷 | `results/task-1/site_solution.csv` |
| 表3 | 非零运输分配方案 | `results/task-1/assignment.csv` |
| 表4 | A/B/C样本外仿真评价 | `results/task-2/final_summary.csv`、`final_paired_response.csv` |
| 表5 | 日常与备用车辆执行规则 | `results/task-2/selected_policy.json` |
| 表6 | 任务三自适应持续时间节点 | `results/task-3/adaptive_design.csv` |
| 表7 | 全市逐时长平均响应与成对效应 | `results/task-3/citywide_duration_table.csv` |
| 表8 | 事故区与非事故区成对效应 | `results/task-3/scoped_paired_response_surfaces.csv` |

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
6. 任务三：连续事故时长、最不利窗口、自适应响应面、分域成对评价（4图、3表）。
7. 模型检验、优缺点与适用边界。
8. 参考文献与全题复现说明。

最终稿固定使用任务一4幅、任务二5幅、任务三4幅正式图，8个左右可编辑表和20个以上原生OMML公式；三问均有原始、过程和结果证据，图号—文件名—章节映射见各问证据位置，所有编号连续且均在正文引用。
