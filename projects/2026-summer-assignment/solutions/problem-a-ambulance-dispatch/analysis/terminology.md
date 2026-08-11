# A题任务一、任务二术语与符号表

> **状态说明（2026-08-11）**：任务一术语继续有效。任务二正在改为“每日固定140次条件NHPP + 相对4 min的延迟惩罚成本”，本表任务二条目须随修订实现更新后才能作为论文合同。

> 本表与《题目分析报告》同步。任务三尚未冻结，暂不收录未经确认的第三问符号。

## 1. 基本集合与空间参数

| 中文术语 | 英文术语 | 符号 | 定义 | 单位 | 首次出现 | 禁止混用或注意事项 |
|---|---|---:|---|---|---|---|
| 需求区集合 | demand-zone set | $I$ | $I=\{1,\ldots,10\}$ | — | 报告1.2 | 下标固定用 $i,r$ |
| 候选站集合 | candidate-site set | $J$ | $J=\{1,\ldots,6\}$ | — | 报告1.2 | 下标固定用 $j$ |
| 车辆集合 | ambulance set | $\mathcal A$ | 任务二中的12辆具体车辆 | — | 报告4.3 | 与站点配车数 $v_j$ 区分 |
| 区域日均需求 | mean daily zone demand | $q_i$ | 区域 $i$ 的日均呼叫量 | 次/日 | 报告1.2 | 是期望量，不是每天固定次数 |
| 全市日均需求 | mean total daily demand | $Q$ | $Q=\sum_iq_i=140$ | 次/日 | 报告1.2 | 与每日随机实现值 $N_d$ 区分 |
| 区域坐标 | zone centroid | $(x_i,y_i)$ | 区域中心代表坐标 | km | 报告2.1 | 不代表区域内每个居民位置 |
| 站点坐标 | station coordinate | $(X_j,Y_j)$ | 候选站点坐标 | km | 报告2.2 | 与医院位置无关 |
| 站点—区域距离 | site-to-zone distance | $d_{ij}$ | 区域中心与站点间欧氏距离 | km | 报告2.2 | 不得用“距最近医院距离”替代 |
| 平均行驶速度 | mean travel speed | $v$ | 题面给定45 | km/h | 报告1.2 | 与站点配车变量 $v_j$ 注意区分；正文优先写数值45 |
| 黄金响应时限 | golden response threshold | $T_4$ | 接警至到场的4 min时限 | min | 报告2.2 | 包含等待、准备、行驶 |
| 准备时间 | preparation time | $t_0$ | 车辆出发前准备，题面给定3 | min | 报告2.2 | 不能忽略或重复计入45 min占用 |
| 严格黄金覆盖半径 | strict four-minute radius | $R_4$ | 无等待时 $45(4-3)/60=0.75$ | km | 报告2.2 | 不是3 km |
| 等待后的有效半径 | residual coverage radius | $R_4(w)$ | 已等待 $w$ min后剩余可行驶距离 $0.75(1-w)$ | km | 报告2.2 | 只在 $0\le w\le1$ 时非负 |
| 最近医院距离 | nearest-hospital distance | $h_i$ | 原题表1给出的区域到最近医院距离 | km | 报告1.3 | 不进入站点到现场响应距离 |

## 2. 任务一变量、约束与结果

| 中文术语 | 英文术语 | 符号 | 定义 | 单位 | 首次出现 | 禁止混用或注意事项 |
|---|---|---:|---|---|---|---|
| 站点车辆上限 | station vehicle capacity | $\bar v_j$ | 各站最大配车数 $(3,2,2,2,1,2)$ | 辆 | 报告1.2 | 是停车/配置上限，不是实际配车 |
| 车辆配置变量 | ambulance-allocation variable | $v_j$ | 站点 $j$ 的实际配车数 | 辆 | 报告3.2 | 整数，且 $v_j\le\bar v_j$ |
| 站点启用变量 | station-opening variable | $y_j$ | 站点启用为1，否则为0 | 0/1 | 报告3.2 | 不等于建设优先级评分 |
| 服务分配流量 | service-allocation flow | $x_{ij}$ | 区域 $i$ 日均由站点 $j$ 承担的呼叫量 | 次/日 | 报告3.2 | 是连续长期流量，不是单次派车0-1变量 |
| 单车日接单上限 | daily dispatch cap | $c$ | 每车每日最多接受12次任务 | 次/(车·日) | 报告3.2 | 按接受派车日计数，不按呼叫到达日 |
| 站点日服务容量 | station daily service capacity | $cv_j$ | 站点 $j$ 的日服务上限 | 次/日 | 报告3.2 | 与45 min时间占用约束并存 |
| 总加权出车距离 | total demand-weighted distance | $D$ | $\sum_{ij}d_{ij}x_{ij}$ | km·次/日 | 报告3.2 | 平均值需除以140 |
| 最小总距离 | minimum total distance | $D^*$ | 第一层运输LP最优目标值 | km·次/日 | 报告3.5 | 第二层覆盖优化不得显著超过它 |
| 平均出车距离 | mean dispatch distance | $\bar d$ | $D/140$ | km | 报告3.2 | 与医院距离加权平均无关 |
| 静态响应下界 | static response lower bound | $\bar T_{\mathrm{static}}$ | $3+60\bar d/45$，不含排队 | min | 报告3.6 | 不能称为任务二优化后平均响应时间 |
| 严格覆盖指示量 | strict coverage indicator | $g_{ij}$ | $d_{ij}\le0.75$时为1 | 0/1 | 报告3.5 | 不是3 km覆盖指示量 |
| 严格静态覆盖量 | strict static covered demand | $C_4$ | $\sum_{ij}g_{ij}x_{ij}$ | 次/日 | 报告3.5 | 除以140才是覆盖率 |
| 词典序优化 | lexicographic optimization | — | 先最小距离，再在距离最优集中最大覆盖 | — | 报告3.5 | 不把不同单位目标随意加权 |
| 数值容差 | numerical tolerance | $\varepsilon$ | 第二阶段允许的求解器浮点误差 | km·次/日 | 报告3.5 | 不能成为实质性距离让步 |
| 站点负荷 | station workload | $\ell_j$ | $\ell_j=\sum_ix_{ij}$ | 次/日 | 报告3.6 | 必须不超过 $12v_j$ |
| 标准站年成本 | annual standard-station cost | $c_s$ | 题面给定120 | 万元/年 | 报告1.2 | 题面无总预算，当前不构造预算约束 |
| 建设优先级评分 | construction-priority score | — | 原题表2的站点评分 | 分 | 报告3.1 | 不进入当前主模型目标 |

## 3. 覆盖率与响应指标

| 中文术语 | 英文术语 | 符号 | 定义 | 单位 | 首次出现 | 禁止混用或注意事项 |
|---|---|---:|---|---|---|---|
| 严格4分钟静态覆盖率 | strict static four-minute coverage | $\rho_4^{\mathrm{static}}$ | 无等待且实际分配满足 $3+60d/45\le4$ 的需求比例 | % | 报告2.3 | 本题复算为60.714%，不含排队 |
| 实际分配3 km覆盖率 | assigned-flow 3-km coverage | $\rho_{3\mathrm{km}}^{\mathrm{assigned}}$ | 按分配矩阵判断 $d\le3$ 的需求比例 | % | 报告2.3 | 只给行驶4 min的对照口径 |
| 静态潜在3 km覆盖率 | potential 3-km spatial coverage | $\rho_{3\mathrm{km}}^{\mathrm{potential}}$ | 只判断附近是否存在3 km内站点 | % | 报告2.3 | 不考虑容量、分配、忙碌；97.143%属于此口径 |
| 呼叫等待时间 | call waiting time | $T_e^{\mathrm{wait}}$ | 从呼叫到达到车辆接受派车 | min | 报告2.2 | 与3 min准备时间分开 |
| 呼叫响应时间 | call response time | $T_e^{\mathrm{resp}}$ | 等待+准备+派出位置到现场行驶 | min | 报告2.2 | 不含现场处置和送医 |
| 严格4分钟服务率 | realized four-minute compliance | $\rho_4$ | 仿真中 $T_e^{\mathrm{resp}}\le4$ 的呼叫比例 | % | 报告4.9 | 与静态覆盖率区分 |
| P90响应时间 | 90th-percentile response time | P90 | 90%呼叫不超过的响应时间 | min | 报告4.9 | 不是平均值的90% |
| P95响应时间 | 95th-percentile response time | P95 | 95%呼叫不超过的响应时间 | min | 报告4.9 | 与95%置信区间区分 |
| 延迟惩罚成本 | delay penalty cost | — | 原题给定200元/(min·次) | 元 | 报告1.2 | 尚未用于前两问主目标，使用时须定义从何时起罚 |

## 4. 任务二到达过程

| 中文术语 | 英文术语 | 符号 | 定义 | 单位 | 首次出现 | 禁止混用或注意事项 |
|---|---|---:|---|---|---|---|
| 非齐次Poisson过程 | nonhomogeneous Poisson process | NHPP | 到达率随时间连续变化的Poisson过程 | — | 报告4.2 | 本题的日内曲线是合成情景，不是历史拟合 |
| 区域到达率 | zone call-arrival rate | $\lambda_i(t)$ | $q_if(t\bmod24)$ | 次/h | 报告4.2 | 积分一日等于 $q_i$ |
| 全市到达率 | total call-arrival rate | $\lambda_\Sigma(t)$ | $140f(t)$ | 次/h | 报告4.2 | 日积分为140 |
| 归一化日内强度 | normalized intraday intensity | $f(t)$ | 24 h周期且一日积分为1的强度形状 | $\mathrm h^{-1}$ | 报告4.2 | 不是概率密度以外的随意乘子 |
| 周期高斯核 | periodic Gaussian kernel | $G(t;\mu,\sigma)$ | 普通高斯在24 h周期上的延拓 | — | 报告4.2 | 用于保证0时与24时连续 |
| 双高斯未归一化强度 | unnormalized double-Gaussian intensity | $g(t)$ | 基线加上午峰与傍晚峰 | — | 报告4.2 | 归一化后才得到 $f(t)$ |
| 小时到达概率 | hourly arrival share | $p_h$ | $\int_h^{h+1}f(t)dt$ | — | 报告4.2 | 24项和为1；不是历史频率 |
| 日随机呼叫总数 | realized daily call count | $N_d$ | $N_d\sim\mathrm{Poisson}(140)$ | 次/日 | 报告4.2 | 不固定等于140 |
| 峰值幅度 | peak amplitude | $a_1,a_2$ | 上午峰和傍晚峰相对幅度 | — | 报告4.2 | 做±10%、±20%情景扰动并重新归一化 |
| 峰值位置 | peak center | $\mu_1,\mu_2$ | 基准为9 h和18 h | h | 报告4.2 | 是合成情景参数 |
| 峰宽 | peak width | $\sigma_1,\sigma_2$ | 基准为2 h和2.5 h | h | 报告4.2 | 是合成情景参数 |
| 稀疏化法 | thinning algorithm | — | 从上界齐次过程筛选NHPP到达时刻 | — | 报告4.2 | 属于实现算法，不是另一到达模型 |
| 共同随机数 | common random numbers | CRN | 不同策略使用相同呼叫轨迹进行成对比较 | — | 报告4.8 | 不同独立复制仍使用不同种子 |

## 5. 车辆、队列和跨日状态

| 中文术语 | 英文术语 | 符号 | 定义 | 单位 | 首次出现 | 禁止混用或注意事项 |
|---|---|---:|---|---|---|---|
| 固定常驻配车 | fixed home-station allocation | $u_j$ | $(3,2,2,2,1,2)$ | 辆 | 报告4.3 | 任务后回所属站，不动态改归属 |
| 车辆下一可用时刻 | next available time | $t_a^{\mathrm{free}}$ | 车辆完成当前任务并可再次派出的时刻 | min或h | 报告4.3 | 接受任务后加45 min |
| 完整任务占用时间 | full busy-cycle duration | $S$ | 题面给定45 min，从接受派车到回站可用 | min | 报告4.3 | 不再额外加准备、去返程和现场时间 |
| 日接单次数 | daily accepted dispatches | $n_{a,d}$ | 车辆 $a$ 在日历日 $d$ 接受的任务数 | 次 | 报告4.3 | 00:00重置；忙闲状态不重置 |
| 全市FCFS队列 | citywide FCFS queue | — | 全市未派呼叫按到达顺序等待 | — | 报告4.3 | 后到呼叫不得因更近而插队 |
| 呼叫到达日 | call-arrival day | $d_e^{\mathrm{arr}}$ | 呼叫指标归属的日期 | 日 | 报告4.4 | 与接受派车日区分 |
| 接受派车日 | dispatch-acceptance day | $d_e^{\mathrm{disp}}$ | 车辆日接单次数归属的日期 | 日 | 报告4.4 | 跨日排队时可与到达日不同 |
| 日末积压量 | end-of-day backlog | $Q_d^{\mathrm{end}}$ | 日末仍未派出的呼叫数 | 次 | 报告4.8 | 24:00不能清零 |
| 日末排空 | terminal drain | — | 最后统计日停止新到达后继续运行至旧呼叫完成 | — | 报告4.4 | 不等于每日清空系统 |
| 预热期 | warm-up period | $W$ | 为消除初始全空闲偏差而舍弃的天数 | 日 | 报告4.8 | 只舍弃统计，不重置状态 |
| 最近医院距离 | nearest-hospital distance | $h_i$ | 区域中心至最近医院的题给距离 | km | 报告4.9 | 不进入派车距离；用于理想行驶链条补充指标 |
| 理想行驶链条时间 | ideal travel-chain time | $T_e^{\mathrm{chain}}$ | 响应时间加按45 km/h直达最近医院的理想行驶时间 | min | 报告4.9 | 不含现场处置、交接和院内时间，不等于真实到院时间 |
| MSER-5预热判据 | MSER-5 warm-up rule | $M(d)$ | 将跨复制逐日均值按不重叠5日分批，以删失后均值的均方误差代理选择预热长度 | 日 | 报告4.8 | 三项诊断指标取最大删失点；最优点落在搜索上界则延长试运行 |

## 6. 三种派车策略

| 中文术语 | 英文术语 | 符号 | 定义 | 单位 | 首次出现 | 禁止混用或注意事项 |
|---|---|---:|---|---|---|---|
| 策略A | global nearest dispatch | A | 从全市合法空闲车辆中派最近车辆 | — | 报告4.5 | 无覆盖保护、无备用身份 |
| 合法候选车辆集 | eligible ambulance set | $\mathcal A_e(t)$ | 当前空闲且接受后不超过日12次的车辆 | — | 报告4.5 | 忙车和当日已满12次车辆不在集合中 |
| 策略B | look-ahead delay-and-load dispatch | B | 以当前绕行、未来45 min期望累计响应损失和日负荷联合评分 | — | 报告4.6 | 不配置备用车 |
| 当前额外响应代价 | incremental current-call cost | $\Delta T_{ea}$ | 相对最近候选车增加的无等待响应时间 | min | 报告4.6 | 准备时间相同，差异来自距离 |
| 最大绕行约束 | maximum detour constraint | $\delta$ | 允许相对最近车增加的最大响应时间 | min | 报告4.6 | 不是备用启用阈值 $\tau$ |
| 假想下一呼叫响应 | predicted next-call response | $\widehat T_r(u\mid S)$ | 给定当前车辆状态，区域$r$在未来时刻$u$出现呼叫的预计最短响应 | min | 报告4.6 | 不把未知未来呼叫当作已知事件 |
| 最早合法等待 | earliest eligible wait | $W_b(u\mid S)$ | 车辆$b$从$u$起到满足忙闲与日12次限制所需的等待 | min | 报告4.6 | 同时考虑已有任务和午夜计数重置 |
| 派车后反事实状态 | post-dispatch counterfactual state | $S^{(-a)}(t)$ | 当前派出车辆$a$、其余已有车辆状态不变的状态 | — | 报告4.6 | 只用于一阶滚动前瞻 |
| 45分钟期望累计响应损失 | 45-minute expected cumulative response loss | $C_a(t)$ | 派出车辆$a$后，未来45 min预期新增的总响应延误 | min | 报告4.6 | 对全部10区连续计量，不是0.75 km二元覆盖 |
| 当日负荷惩罚 | daily workload penalty | $B_a(t)$ | $(n_{a,d}+1)/12$ | — | 报告4.6 | 防止车辆过早耗尽日额度 |
| 负荷权重 | workload weight | $\beta$ | 将 $B_a$ 转换成分钟代价 | min | 报告4.6 | 由调参集网格搜索 |
| B策略评分 | policy-B dispatch score | $J_{ea}$ | $\Delta T_{ea}+C_a+\beta B_a$ | min | 报告4.6 | 仅在 $\Delta T\le\delta$ 候选内比较 |
| 策略C | fixed-reserve dispatch | C | 固定备用身份，达到阈值才解除保护 | — | 报告4.7 | 不叠加B的覆盖评分 |
| 备用向量 | reserve vector | $r=(r_1,\ldots,r_6)$ | 每个站点的固定备用车辆数 | 辆 | 报告4.7 | $0\le r_j\le u_j-1$；S5不能设备用 |
| 常规车 | regular ambulance | — | 策略C中普通就近派车车辆 | — | 报告4.7 | 与固定备用车身份区分 |
| 最早合法接受时刻 | earliest legal dispatch time | $e_a(t)$ | 同时考虑任务完成和日计数重置后的最早接单时刻 | min或h | 报告4.7 | 不是简单的任务完成时刻 |
| 常规车预测响应 | predicted regular response | $\widehat T_e^{\mathrm{reg}}$ | 从呼叫到达起算，等待最快常规车后的预计总响应时间 | min | 报告4.7 | 包含已发生等待、预计剩余等待、准备和行驶 |
| 备用启用阈值 | reserve release threshold | $\tau$ | 常规车预测响应超过该值才允许备用车出动 | min | 报告4.7 | 枚举4、5、6、7、8 min |
| 备用恢复 | reserve-role restoration | — | 备用车任务结束回原站后重新成为备用 | — | 报告4.7 | 备用身份不是一次性取消 |

## 7. 参数选择与统计检验

| 中文术语 | 英文术语 | 符号 | 定义 | 单位 | 首次出现 | 禁止混用或注意事项 |
|---|---|---:|---|---|---|---|
| 调参集 | tuning set | — | 30个独立连续多日复制，用于B参数和C配置选择 | — | 报告4.6 | 不用于主方案入选或最终成绩 |
| 方案选择集 | policy-selection set | — | 30个全新复制，用于C资格验证和A/B/C日常主方案选择 | — | 报告4.8 | 参数进入该集合前必须冻结 |
| 最终测试集 | held-out final test set | — | 100个全新复制，用于冻结方案的一次最终评价 | — | 报告4.8 | 查看结果后不得重新调参或换方案 |
| 日常主方案 | selected routine policy | — | 按预先固定的平均响应时间优先规则从合格A/B/C中选出的方案 | — | 报告4.8 | 是任务三“现有调度方案”的条件输入 |
| 独立复制 | independent replication | $m$ | 一条独立随机呼叫轨迹及其策略对照 | — | 报告4.8 | 同一复制内策略使用共同随机数 |
| 统计日 | measured day | — | 预热后纳入指标的连续日 | 日 | 报告4.8 | 每复制计划100日 |
| 成对差值 | paired performance difference | $\Delta_m$或$D_m$ | 同一呼叫轨迹下两个策略指标之差 | 随指标 | 报告4.7 | 比非配对均值比较方差更小 |
| 95%置信区间 | 95% confidence interval | CI | 基于独立复制均值或成对差值的t区间 | 随指标 | 报告4.9 | 与P95响应时间区分 |
| 零容忍非劣约束 | zero-margin noninferiority constraint | — | C平均响应时间不能高于A | min | 报告4.7 | 零界值非常严格，不能用“差异不显著”替代 |
| 单侧95%上限 | one-sided 95% upper bound | $U_{0.95}$ | $E[\bar T_C-\bar T_A]$ 的单侧上置信限 | min | 报告4.7 | 只有 $U_{0.95}\le0$ 才通过C的检验 |
| 系统稳定性 | simulation stability | — | 队列不持续发散且呼叫最终可服务 | — | 报告4.6 | 仅“最后能排空”不足以证明连续运行稳定 |
| 区域公平性 | regional response equity | — | 各区域平均响应差异和最差区域表现 | min | 报告4.6 | 不以全市均值掩盖弱势区域 |

## 8. 状态说明

第一问的配置、分配矩阵和静态指标已经独立复算。第二问的模型、参数范围和验证流程已经冻结，但预热长度、B的最优参数、C的最优或不可行结论、日常主方案与动态响应指标仍必须由后续真实代码运行得到。任务三以日常主方案为条件输入，具体应急切换规则待任务二结果产生后冻结。
