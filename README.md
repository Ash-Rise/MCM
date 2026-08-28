# MCM

用于管理数学建模课程作业、练习与竞赛项目的长期仓库。题面、已接受决策、实现、正式结果和论文分别保存在对应项目目录；Git Tag、Release 与提交历史保存发布版本和历史状态。

## 当前项目

- [2026 Summer Assignment](projects/2026-summer-assignment/README.md)：A、B、C 三题的权威题面及三套已完成解答。每题均保留结构化结果、实现、测试、图表和最终论文。

## 核心入口

- [AGENTS.md](AGENTS.md)：AI 进入仓库时使用的 authority 路由和工作边界。
- [MCM_AI_Governance.md](MCM_AI_Governance.md)：Decision ownership、Question Gate、artifact authority、验证与集成边界。
- [2026 暑期作业索引](projects/2026-summer-assignment/README.md)：题面、A/B/C 解答和正式复现入口。
- [建模与论文方法手册](shared/templates/personal-modeling-playbook.md)：按需查阅的建模、实验、证据和写作方法。
- [论文排版配置](shared/templates/personal-paper-profile.yaml)：共享的机器可读 Word 排版参数。
- [共享 DOCX formatter](shared/paper_format.py)：把共享 profile 应用于论文 DOCX。

README 负责导航和复现入口，不替代题面、`decisions.md`、冻结结果或 `paper.md` 的分类权威。已完成项目不以 `state.md`、阶段报告或临时 QA 文件保存历史；需要追溯时使用 Git。

## 顶层结构

```text
MCM/
|-- AGENTS.md
|-- MCM_AI_Governance.md
|-- projects/                  # 各次作业或竞赛、题面及独立题解
`-- shared/
    |-- paper_format.py        # 共享 DOCX 格式实现
    `-- templates/             # 建模手册与论文排版 profile
```

题目和第三方资料仍受其原有权利约束；本仓库默认不授予额外许可。
