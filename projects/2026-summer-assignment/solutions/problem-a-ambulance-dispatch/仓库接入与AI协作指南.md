# 仓库接入与 AI 协作指南

这份文档用于让协作者及其 AI 快速接入 `Ash-Rise/MCM`。协作者只需完成首次安装、登录 GitHub，并在 AI 修改论文前说明具体校对目标；Git 同步、分支、验证、Commit、Push 和 PR 由能读取本地仓库并操作终端的 AI 完成。

安装总览图：[安装与 Git 使用清单](docs/assets/repository-setup-installation-and-git.png)

## 一、软件准备

### 必须安装

| 软件 | 用途 | Windows 官方入口 | 安装注意事项 |
| --- | --- | --- | --- |
| VS Code | 打开整个仓库、编辑和预览 Markdown、查看 Git 差异 | <https://code.visualstudio.com/Download> | 推荐 `User Installer`；安装时保留“添加到 PATH”和资源管理器右键菜单选项 |
| Git | Clone、同步、记录历史、创建分支、Commit 和 Push | <https://git-scm.com/install/windows> | 默认选项通常即可；安装后重新打开终端和 VS Code |
| GitHub 账号 | 获取仓库写权限、查看 PR、Issues 和历史 | <https://github.com/signup> | 将 GitHub 用户名发给仓库负责人，由负责人添加协作者权限 |

### 推荐安装

| 软件 | 用途 | 官方入口或安装命令 | 说明 |
| --- | --- | --- | --- |
| GitHub CLI（`gh`，强烈推荐） | 让 AI 在终端登录 GitHub、Push 后创建和查看 PR | <https://cli.github.com/>；`winget install --id GitHub.cli` | 安装后执行 `gh auth login --web`；这是 AI 快速完成 GitHub 操作的主要入口 |
| 可操作仓库的 AI 编程工具 | 自动读取规则、运行 Git、修改论文并创建 PR | 由协作者自行选择 | 必须能读取整个本地仓库并操作终端；普通网页聊天不够 |

VS Code 自带的 Markdown 预览已足够用于本仓库的日常阅读与校对，无需另外安装预览扩展或文档转换工具。最终 DOCX 仍由论文负责人统一生成。

## 二、首次安装后的检查

在 PowerShell 或 VS Code 终端中逐条执行：

```powershell
git --version
code --version
gh --version
```

三条命令都能显示版本号，说明 PATH 已生效。若出现“无法识别命令”，先完全关闭并重开 VS Code；仍无效时再检查对应软件是否成功安装，不要重复安装多个副本。

首次使用 Git 还需要设置提交身份。把示例内容换成协作者自己的 GitHub 名称和邮箱：

```powershell
git config --global user.name "GitHub用户名"
git config --global user.email "GitHub账号使用的邮箱"
```

登录 GitHub CLI：

```powershell
gh auth login --web
gh auth status
```

选择 `GitHub.com` 和 `HTTPS`，随后在浏览器中完成授权。不要把访问令牌、密码或验证码发给 AI 或其他人。

## 三、获得仓库权限

推荐路线是仓库负责人给协作者 `Ash-Rise/MCM` 的写权限。协作者把 GitHub 用户名发给负责人，接受 GitHub 邀请后即可使用短期 `review/*` 分支 Push 并提交 PR，不需要 Fork。

如果负责人没有授予写权限，协作者才使用 Fork：先把 `Ash-Rise/MCM` 复制到自己的 GitHub 账号，再从自己的 Fork Clone、Push，最后向 `Ash-Rise/MCM:main` 提交跨仓库 PR。

## 四、Clone 并正确打开仓库

完成 `gh` 登录后，协作者可以让 AI 执行：

```powershell
gh repo clone Ash-Rise/MCM
code MCM
```

也可以使用 Git：

```powershell
git clone https://github.com/Ash-Rise/MCM.git
code MCM
```

必须在 VS Code 和 AI 工具中打开完整的 `MCM` 文件夹，不能只打开某个 `.md` 文件。只有打开完整仓库，图片相对路径、仓库规则、Git 历史和预览配置才能正常工作。

打开后完成以下检查：

1. 左下角应能看到当前 Git 分支，通常为 `main`。
2. 在终端运行 `git status`，确认当前路径属于 `MCM` 仓库。
3. 打开 Markdown 后按 `Ctrl+Shift+V` 使用 VS Code 自带预览；按 `Ctrl+K V` 可在侧边预览。
4. 图片无法显示时，确认打开的是整个 `MCM` 文件夹，而不是只打开单个 Markdown 文件。

## 五、在 VS Code 中使用 Git

点击左侧活动栏的“源代码管理”分支图标，即可使用 VS Code 的 Git 界面：

- `更改`：尚未暂存的本地修改；`U` 表示未跟踪文件，`M` 表示已修改文件。
- 文件右侧的 `+`：把该文件加入“暂存的更改”，表示准备放进下一次 Commit。
- `暂存的更改`：已经选入下一次 Commit，但尚未上传。
- 输入提交说明并点击“提交”：创建本地 Commit。
- 点击“同步更改”或“推送”：把本地 Commit 上传到 GitHub。
- 点击某个文件可查看红色删除、绿色新增的逐行差异。
- 查看历史可使用源代码管理视图中的提交图，或文件资源管理器底部的“时间线”。

协作者不必手工完成整套 Git 操作；AI 可以执行同步、分支、Commit、Push 和 PR，但人工应在提交前通过“更改”与“暂存的更改”确认本次包含哪些文件。

## 六、论文文件职责

- `paper/vX.Y/A题论文(vX.Y).md`：唯一正文和预览基准，也是唯一允许人工修改的论文文件。
- `paper/vX.Y/A题论文(vX.Y).docx`：Word 交付物，由论文负责人在 Markdown 内容审核通过后统一生成和排版；协作者不要并行编辑。
- `README.md`：项目入口、当前正式版本、在线预览、Word 下载和版本发行说明。
- `AGENTS.md`：AI 必须遵守的仓库操作规则。根目录和 A 题项目目录各有一份，必须同时读取。

开发中的版本可能尚未写入 README 的正式发行说明。查看协作中的最新版时，以 `main` 上最新 `paper/vX.Y/` 目录及仓库规则为准；下载正式稳定版时看 GitHub `Releases`。

## 七、日常只需两个入口

### 入口 A：查看 main 的最新变化

协作者只需告诉 AI：查看 `main` 上最新版论文相对当前本地分支有哪些新变化。

AI 应当自行完成：

1. 读取根目录和项目目录的 `AGENTS.md`。
2. 检查 `git status`，保留协作者已有的本地修改。
3. 只执行安全的远程信息获取，例如 `git fetch origin`，不先覆盖本地文件。
4. 区分 `origin/main` 的新增变化和协作者本地分支自己的变化。
5. 按论文内容的重要性报告，而不是机械抄录每一行 diff。
6. 单独列出数字、公式、模型、引用和结论是否变化。

查看操作默认只报告，不修改、合并、暂存或提交文件。

### 入口 B：修改论文并提交 PR

协作者只需说明要修改的章节、问题、建议和依据。其 AI 应当自行：

1. 从最新 `origin/main` 创建短期分支，例如 `review/协作者代号-校对主题`。
2. 只修改当前论文的唯一 Markdown 正文源，不修改 DOCX。
3. 用 VS Code 自带预览检查显示效果，并运行与改动风险相称的检查。
4. 输出内容增删报告，说明数字、公式、模型、引用和结论是否变化。
5. 只暂存本次任务文件，Commit 后 Push 当前 `review/*` 分支。
6. 创建目标为 `main` 的 PR，并把 PR 链接交给协作者和仓库负责人。
7. 创建 PR 后停止；AI 不得自动 Merge，也不得删除分支。

## 八、PR 与审核职责

PR（Pull Request）不是上传文件，也不是自动合并。Push 先把协作者分支的 Commit 上传到 GitHub；PR 再请求负责人比较该分支与 `main`，审核后决定是否 Merge。

协作者在 GitHub 顶部 `Pull requests` 中查看自己提交的 PR：

- `Conversation`：修改说明、审核意见和讨论。
- `Commits`：该 PR 包含的提交。
- `Checks`：自动验证是否通过。
- `Files changed`：逐行查看新增、删除和修改，是完整差异的权威入口。

只有仓库负责人可以确认 Merge。遇到同一段文字冲突，或数字、参数、公式、模型口径、引用和结论冲突时，AI 必须停止并报告，不得自行选择一边。

## 九、给协作 AI 的直接执行规范

把本文件交给 AI 后，AI 应直接读取仓库内规则并行动，不得要求协作者背 Git 命令或反复复制提示词。

```text
仓库：Ash-Rise/MCM
协作目标：协作者负责人工校对和内容建议，仓库负责人负责最终审核与 Merge。

开始任何操作前：
1. 读取仓库根目录 AGENTS.md。
2. 读取 projects/2026-summer-assignment/solutions/problem-a-ambulance-dispatch/AGENTS.md。
3. 读取项目 README.md 和本协作指南。
4. 检查 git status，不得覆盖、暂存或回退无关修改。

查看任务：fetch 后比较 origin/main 与本地分支，只报告，不修改。
修改任务：基于最新 origin/main 创建 review/* 短期分支，只改唯一 Markdown 正文源；预览并验证、输出增删报告、Commit、Push、创建指向 main 的 PR，然后停止等待负责人审核。

禁止：未经授权修改 DOCX；使用 git reset --hard 或批量清理；全量暂存无关文件；自动 Merge PR；替人决定数字、公式、模型、引用或结论冲突。
```

## 十、常见误区

- `Commit` 只是在本地保存修改快照；`Push` 才把提交上传到 GitHub。
- 本地创建分支后，只有 Push 之后 GitHub 才能看到对应远程分支。
- `PR` 是审核与合并申请；`Merge` 才真正把改动并入 `main`。
- `Pull` 用于把远程变化同步到本地；它与 Pull Request 不是同一件事。
- `Star` 只是收藏或支持仓库，不提供写权限，也不等于接收更新通知。
- `Issues` 用于记录问题、建议和待办；不会直接修改论文。
- `Releases` 是正式稳定版；`main` 可能包含尚未发布的协作中版本。
- 预览图片不显示时，先确认 VS Code 打开的是整个仓库，而不是单个文件。

## 十一、负责人发出指南前的检查

- 已邀请协作者成为仓库协作者，或明确告知使用 Fork 路线。
- 协作者能访问 `Ash-Rise/MCM`，并已接受邀请。
- 根目录和项目目录 `AGENTS.md` 已提交到 GitHub。
- README 中的当前正式版本链接可用。
- 协作者首次只做一个很小的校对 PR，用于验证权限、预览、Push 和审核流程。
