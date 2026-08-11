# A题三项任务术语与符号表

> **状态说明（2026-08-11）**：任务一采用3 km名义行驶服务半径，0.75 km仅作严格黄金响应的中心代理诊断。任务二采用“每日固定140次的条件NHPP + 相对4 min总响应的延迟惩罚成本”，固定预热30天；最终策略参数与数值已经由干净重跑结果确定。

> 本表与《题目分析报告》同步；任务三事故情景与应急派车符号已收录。

## 1. 基本集合与空间参数

| 中文术语 | 英文术语 | 符号 | 定义 | 单位 | 首次出现 | 禁止混用或注意事项 |
|---|---|---:|---|---|---|---|
| 需求区集合 | demand-zone set | $I$ | $I=\{1,\ldots,10\}$ | — | 报告1.2 | 下标固定用 $i,r$ |
| 候选站集合 | candidate-site set | $J$ | $J=\{1,\ldots,6\}$ | — | 报告1.2 | 下标固定用 $j$ |
| 车辆集合 | ambulance set | $\mathcal A$ | 任务二中的12辆具体车辆 | — | 报告4.3 | 与站点配车数 $v_j$ 区分 |
| 区域日均需求 | mean daily zone demand | $q_i$ | 区域 $i$ 的日均呼叫量 | 次/日 | 报告1.2 | 是期望量，不是每天固定次数 |
| 全市每日呼叫量 | fixed total daily calls | $Q$ | $Q=\sum_iq_i=N_d=140$ | 次/日 | 报告1.2 | 仿真中每天固定为140 |
| 区域坐标 | zone centroid | $(x_i,y_i)$ | 区域中心代表坐标 | km | 报告2.1 | 不代表区域内每个居民位置 |
| 区域面积 | zone area | $A_i$ | 题面给出的区域面积 | km$^2$ | 报告1.2 | 无边界形状，不能直接生成区内坐标 |
| 需求密度 | demand density | $\eta_i$ | $q_i/A_i$ | 次/(km$^2\cdot$日) | 报告1.2 | 用于空间需求分析，不重复乘入运输权重 |
| 站点坐标 | station coordinate | $(X_j,Y_j)$ | 候选站点坐标 | km | 报告2.2 | 与医院位置无关 |
| 站点—区域距离 | site-to-zone distance | $d_{ij}$ | 区域中心与站点间欧氏距离 | km | 报告2.2 | 不得用“距最近医院距离”替代 |
| 平均行驶速度 | mean travel speed | $v$ | 题面给定45 | km/h | 报告1.2 | 与站点配车变量 $v_j$ 注意区分；正文优先写数值45 |
| 黄金响应时限 | golden response threshold | $T_4$ | 接警至到场的4 min时限 | min | 报告2.2 | 包含等待、准备、行驶 |
| 准备时间 | preparation time | $t_0$ | 车辆出发前准备，题面给定3 | min | 报告2.2 | 不能忽略或重复计入45 min占用 |
| 名义行驶服务半径 | nominal travel-service radius | $R_s$ | $45\times4/60=3$ | km | 报告2.2 | 任务一规划指标；不含等待和准备 |
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
| 规划服务覆盖指示量 | planning service indicator | $g_{ij}^{s}$ | $d_{ij}\le3$时为1 | 0/1 | 报告3.5 | 不表示严格总响应不超过4 min |
| 规划服务覆盖量 | planning covered demand | $C_s$ | $\sum_{ij}g_{ij}^{s}x_{ij}$ | 次/日 | 报告3.5 | 除以140才是覆盖率 |
| 词典序优化 | lexicographic optimization | — | 先最小距离，再在距离最优集中最大覆盖 | — | 报告3.5 | 不把不同单位目标随意加权 |
| 数值容差 | numerical tolerance | $\varepsilon$ | 第二阶段允许的求解器浮点误差 | km·次/日 | 报告3.5 | 不能成为实质性距离让步 |
| 站点负荷 | station workload | $\ell_j$ | $\ell_j=\sum_ix_{ij}$ | 次/日 | 报告3.6 | 必须不超过 $12v_j$ |
| 标准站年成本 | annual standard-station cost | $c_s$ | 题面给定120 | 万元/年 | 报告1.2 | 题面无总预算，当前不构造预算约束 |
| 建设优先级评分 | construction-priority score | — | 原题表2的站点评分 | 分 | 报告3.1 | 不进入当前主模型目标 |

## 3. 覆盖率与响应指标

| 中文术语 | 英文术语 | 符号 | 定义 | 单位 | 首次出现 | 禁止混用或注意事项 |
|---|---|---:|---|---|---|---|
| 3 km规划服务覆盖率 | planning 3-km service coverage | $\rho_s$ | 按实际分配矩阵判断 $d\le3$ 的需求比例 | % | 报告2.3 | 任务一主覆盖指标；本题为86.429% |
| 严格4分钟中心代理覆盖率 | strict center-proxy four-minute coverage | $\rho_4^{\mathrm{center}}$ | 无等待且区域代表点满足 $3+60d/45\le4$ 的需求比例 | % | 报告2.3 | 本题为60.714%；不是真实面积覆盖 |
| 静态潜在3 km覆盖率 | potential 3-km spatial coverage | $\rho_{3\mathrm{km}}^{\mathrm{potential}}$ | 只判断附近是否存在3 km内站点 | % | 报告2.3 | 不考虑容量、分配、忙碌；97.143%属于此口径 |
| 呼叫等待时间 | call waiting time | $T_e^{\mathrm{wait}}$ | 从呼叫到达到车辆接受派车 | min | 报告2.2 | 与3 min准备时间分开 |
| 呼叫响应时间 | call response time | $T_e^{\mathrm{resp}}$ | 等待+准备+派出位置到现场行驶 | min | 报告2.2 | 不含现场处置和送医 |
| 严格4分钟服务率 | realized four-minute compliance | $\rho_4$ | 仿真中 $T_e^{\mathrm{resp}}\le4$ 的呼叫比例 | % | 报告4.9 | 与静态覆盖率区分 |
| P90响应时间 | 90th-percentile response time | P90 | 90%呼叫不超过的响应时间 | min | 报告4.9 | 不是平均值的90% |
| P95响应时间 | 95th-percentile response time | P95 | 95%呼叫不超过的响应时间 | min | 报告4.9 | 与95%置信区间区分 |
| 单次超时分钟 | excess response minutes | $L_e$ | $\max(T_e^{\mathrm{resp}}-4,0)$ | min | 报告4.9 | 只计算超过4 min的部分 |
| 单次延迟惩罚成本 | per-call delay penalty | $C_e$ | $200L_e$ | 元/次 | 报告4.9 | 是辅助评价，不替代平均响应时间主目标 |
| 平均每次惩罚成本 | mean penalty per call | $\bar C$ | $N^{-1}\sum_eC_e$ | 元/次 | 报告4.9 | 统计窗内逐呼叫平均 |
| 日均惩罚总成本 | mean daily penalty cost | $\bar C_{\mathrm{day}}$ | $D^{-1}\sum_eC_e$ | 元/日 | 报告4.9 | $D$为统计天数 |

## 4. 任务二到达过程

| 中文术语 | 英文术语 | 符号 | 定义 | 单位 | 首次出现 | 禁止混用或注意事项 |
|---|---|---:|---|---|---|---|
| 条件非齐次Poisson过程 | conditional nonhomogeneous Poisson process | conditional NHPP | 给定每日事件总数140后，按NHPP归一化强度生成到达时刻 | — | 报告4.2 | 条件化后每日总数不再是Poisson随机变量 |
| 区域参考到达率 | reference zone arrival rate | $\lambda_i(t)$ | $q_if(t\bmod24)$ | 次/h | 报告4.2 | 用于定义日内形状；区域日计数由多项分布产生 |
| 全市参考到达率 | reference total arrival rate | $\lambda_\Sigma(t)$ | $140f(t)$ | 次/h | 报告4.2 | 日积分为140，用于条件NHPP构造 |
| 归一化日内强度 | normalized intraday intensity | $f(t)$ | 24 h周期且一日积分为1的强度形状 | $\mathrm h^{-1}$ | 报告4.2 | 不是概率密度以外的随意乘子 |
| 周期高斯核 | periodic Gaussian kernel | $G(t;\mu,\sigma)$ | 普通高斯在24 h周期上的延拓 | — | 报告4.2 | 用于保证0时与24时连续 |
| 双高斯未归一化强度 | unnormalized double-Gaussian intensity | $g(t)$ | 基线加上午峰与傍晚峰 | — | 报告4.2 | 归一化后才得到 $f(t)$ |
| 小时到达概率 | hourly arrival share | $p_h$ | $\int_h^{h+1}f(t)dt$ | — | 报告4.2 | 24项和为1；不是历史频率 |
| 每日固定呼叫总数 | fixed daily call count | $N_d$ | $N_d=140$ | 次/日 | 报告4.2 | 每个日历日严格生成140次 |
| 条件到达时刻 | conditional arrival time | $T_{d,k}$ | 给定 $N_d=140$ 后独立服从密度 $f(t)$ | h | 报告4.2 | 每日生成后按时刻排序 |
| 区域标记概率 | zone-marking probability | $\pi_i$ | $q_i/140$ | — | 报告4.2 | 区域日计数随机，但期望为 $q_i$ |
| 峰值幅度 | peak amplitude | $a_1,a_2$ | 上午峰和傍晚峰相对幅度 | — | 报告4.2 | 做±10%、±20%情景扰动并重新归一化 |
| 峰值位置 | peak center | $\mu_1,\mu_2$ | 基准为9 h和18 h | h | 报告4.2 | 是合成情景参数 |
| 峰宽 | peak width | $\sigma_1,\sigma_2$ | 基准为2 h和2.5 h | h | 报告4.2 | 是合成情景参数 |
| 接受—拒绝采样 | acceptance-rejection sampling | — | 从日内均匀候选时刻按 $f(t)$ 比例接受，直至140个 | — | 报告4.2 | 实现给定总数后的条件到达时刻 |
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
| 固定预热期 | fixed warm-up period | $W$ | 统一固定为30天，用于削弱初始全空闲偏差 | 日 | 报告4.8 | 只舍弃前30天指标，不重置状态或队列 |
| 最近医院距离 | nearest-hospital distance | $h_i$ | 区域中心至最近医院的题给距离 | km | 报告4.9 | 不进入派车距离；用于理想行驶链条补充指标 |
| 理想行驶链条时间 | ideal travel-chain time | $T_e^{\mathrm{chain}}$ | 响应时间加按45 km/h直达最近医院的理想行驶时间 | min | 报告4.9 | 不含现场处置、交接和院内时间，不等于真实到院时间 |

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
| 45分钟期望累计响应损失 | 45-minute expected cumulative response loss | $C_a(t)$ | 派出车辆$a$后，未来45 min预期新增的总响应延误 | min | 报告4.6 | 对全部10区连续计量，不是二元覆盖指标 |
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
| 参数筛选集 | tuning set | — | 3个独立复制，每个预热30天后统计7天，用于B参数和C配置选择 | — | 报告4.8 | 不用于最终数值结论 |
| 样本外最终评价集 | out-of-sample final evaluation set | — | 30个未参与筛选的新复制，每个预热30天后统计30天 | — | 报告4.8 | B、C参数进入该集合前冻结；不是另一套程序 |
| 日常主方案 | selected routine policy | — | 按平均响应时间优先规则在A、B之间选出的方案 | — | 报告4.8 | C作为备用配置单独报告 |
| 独立复制 | independent replication | $m$ | 一条独立随机呼叫轨迹及其策略对照 | — | 报告4.8 | 同一复制内策略使用共同随机数 |
| 统计日 | measured day | — | 预热后纳入指标的连续日 | 日 | 报告4.8 | 筛选7天，最终评价30天 |
| 成对差值 | paired performance difference | $\Delta_m$或$D_m$ | 同一呼叫轨迹下两个策略指标之差 | 随指标 | 报告4.7 | 比非配对均值比较方差更小 |
| 95%置信区间 | 95% confidence interval | CI | 基于独立复制均值或成对差值的t区间 | 随指标 | 报告4.9 | 与P95响应时间区分 |
| 单侧95%上限 | one-sided 95% upper bound | $U_{0.95}$ | $E[\bar T_C-\bar T_A]$ 的单侧上置信限 | min | 报告4.7 | 用于说明备用配置是否不劣及其响应代价 |
| 系统稳定性 | simulation stability | — | 队列不持续发散且呼叫最终可服务 | — | 报告4.6 | 仅“最后能排空”不足以证明连续运行稳定 |
| 区域公平性 | regional response equity | — | 各区域平均响应差异和最差区域表现 | min | 报告4.6 | 不以全市均值掩盖弱势区域 |

## 8. 任务三事故情景

| 中文术语 | 英文术语 | 符号 | 定义 | 单位 | 首次出现 | 禁止混用或注意事项 |
|---|---|---:|---|---|---|---|
| 事故区域 | incident zone | $k$ | 呼叫强度临时升至正常5倍的区域 | — | 报告7.1 | 遍历全部10区 |
| 事故持续时间 | incident duration | $H$ | $[0.5,12]$ 上的连续变量 | h | 报告7.1 | 任何有限节点集都只是数值采样设计，不是定义域 |
| 事故额外强度 | incident extra intensity | $\lambda_k^{\mathrm{extra}}(t)$ | 事故区叠加的 $4q_kf(t)$ | 次/h | 报告7.1 | 与日常强度合计才是5倍 |
| 高峰事故起点 | worst-window start | $t^*(H)$ | 使持续时间窗内日内强度积分最大的周期起点 | h | 报告7.1 | 可用网格数值求解；透明压力情景，不是真实历史时刻 |
| 常态预测模式 | normal-forecast mode | $B_N$ | 事故中继续按日常强度计算B的前瞻损失 | — | 报告7.2 | 与事故感知模式使用同一呼叫流 |
| 事故感知模式 | emergency-aware mode | $B_E$ | 事故区间按5倍强度计算B的前瞻损失 | — | 报告7.2 | 不改变车辆数、FCFS、45 min或日12次上限 |
| 事故期呼叫 | incident-arrival call | — | 到达时刻位于 $[t_0,t_0+H)$ 的呼叫 | 次 | 报告7.3 | 事故结束时未派出仍继续观察 |
| 事故结束积压 | incident-end backlog | $Q_H^{\mathrm{end}}$ | 事故结束时尚未派出的既有呼叫数 | 次 | 报告7.3 | 不等于事故后恢复时间 |
| 成对应急效应 | paired emergency effect | — | 同一呼叫流下 $B_E-B_N$ 的指标差 | 随指标 | 报告7.3 | 负响应时间差表示事故感知方案改善 |
| 自适应持续时间节点 | adaptive duration nodes | $\mathcal H_n$ | 从六个初始节点出发，在高曲率或高不确定区间追加的仿真时长 | h | 报告7.1 | $\mathcal H_n$ 不是 $H$ 的定义域；插值不得冒充精确连续结果 |
| 连续性能曲线 | continuous performance curve | $\bar T_k(H),P95_k(H),C_{4,k}(H),Q_{\max,k}(H)$ | 区域 $k$ 的事故期指标随连续时长变化的响应面及置信带 | 随指标 | 报告7.3 | 题面未给事故时长分布，不作跨时长等权总体汇总 |

## 9. 状态说明

第一问的配置、分配矩阵和静态指标已经独立复算。第二问最终取B的 $(\beta,\delta)=(4,2)$ 作为日常主方案；推荐固定备用方案C取 $r=(0,0,1,0,0,0)$、$\tau=7$ min。任务三目前只冻结连续持续时间、5倍强度、最不利窗口、$B_N/B_E$ 对照和事故期评价边界；正式响应面与数值结论待重新计算，应急模式不与C机械叠加。
