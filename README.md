# MCM

用于管理数学建模课程作业、练习与竞赛项目的长期仓库。各题的题面、模型决策、实现、结果和论文保存在对应项目目录；Git Tag、Release 与提交历史负责保存版本历史。

## 当前项目

- [2026 Summer Assignment](projects/2026-summer-assignment/README.md)：包含 A、B、C 三道题的原题，以及当前已有的 A、B 题解答。

## 主要入口

- [AGENTS.md](AGENTS.md)：AI 进入仓库时使用的权威路由与边界。
- [MCM_AI_Governance.md](MCM_AI_Governance.md)：Decision ownership、Question Gate、authority 和集成边界。
- [建模与论文方法手册](shared/templates/personal-modeling-playbook.md)：按需查阅的建模、实验和写作方法。
- [论文排版配置](shared/templates/personal-paper-profile.yaml)：仓库默认的机器可读排版参数。
- [Workflow handoff](shared/MCM_WORKFLOW_HANDOFF.md)：非权威的历史设计背景。

## 顶层结构

```text
MCM/
|-- AGENTS.md
|-- MCM_AI_Governance.md
|-- projects/                  # 各次作业或竞赛及其独立题解
`-- shared/
    |-- MCM_WORKFLOW_HANDOFF.md
    `-- templates/             # 建模手册、排版配置与 Word 参考模板
```

题目和第三方资料仍受其原有权利约束；本仓库默认不授予额外许可。
