# MCM 仓库 AI 自动接入入口（Windows）

本文件是尚未 Clone 仓库时提供给本地 AI 编程工具的唯一入口。AI 必须能够操作 Windows 终端；普通网页聊天只能解释，不能代替安装。

## 给人的最短操作

1. 把本页链接交给本地 AI：`https://github.com/Ash-Rise/MCM/blob/main/GET_STARTED_AI.md`。
2. 允许 AI 检查并安装缺失软件；Windows 权限弹窗由本人确认。
3. 在浏览器中完成 GitHub 登录，并接受仓库负责人发出的协作者邀请。

密码、访问令牌、验证码不得发送给 AI 或其他人。

## AI 必须执行

### 1. 确认环境与权限边界

- 仅支持 Windows 10/11。
- 先说明将检查 VS Code、Git 和 GitHub CLI；只安装缺失项。
- 使用 Windows 官方包管理器 `winget`，不得从第三方下载站下载安装包。
- GitHub 登录、协作者邀请和系统权限弹窗必须由本人确认。
- 不得使用 `irm ... | iex` 或把未经检查的网络脚本直接通过管道执行。

### 2. 下载并检查引导脚本

在 PowerShell 中执行以下操作。先保存为本地临时文件，读取内容确认后再运行：

```powershell
$bootstrapFile = Join-Path ([System.IO.Path]::GetTempPath()) 'mcm-bootstrap-windows.ps1'
Invoke-WebRequest `
  -Uri 'https://raw.githubusercontent.com/Ash-Rise/MCM/main/tools/bootstrap-windows.ps1' `
  -OutFile $bootstrapFile
Get-Content -LiteralPath $bootstrapFile
```

### 3. 先做只读检查

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File $bootstrapFile -CheckOnly
```

### 4. 经本人确认后安装并接入

默认 Clone 到“文档”目录下的 `MCM` 文件夹：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File $bootstrapFile
```

需要指定目录时：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File $bootstrapFile `
  -Destination 'D:\MCM'
```

脚本会：

1. 检查 `winget`。
2. 检查并安装缺失的 VS Code、Git、GitHub CLI。
3. 刷新当前 PowerShell 进程的 PATH 并验证版本。
4. 运行 `gh auth login --web`，由本人在浏览器中授权。
5. Clone `Ash-Rise/MCM`，或安全复用已经存在的 Git 仓库目录。
6. 用 VS Code 打开整个 `MCM` 文件夹。

### 5. Clone 后继续执行仓库规则

进入仓库后，AI 必须依次读取：

1. 根目录 `AGENTS.md`。
2. `projects/2026-summer-assignment/solutions/problem-a-ambulance-dispatch/AGENTS.md`。
3. `projects/2026-summer-assignment/solutions/problem-a-ambulance-dispatch/仓库接入与AI协作指南.md`。

论文协作只使用 `main` 和临时 `review/*` 分支；项目内的 `paper/paper.md` 是唯一正文基准。AI 可以同步、建分支、验证、Commit、Push 和创建 PR，但不得自动 Merge。

## 故障处理

- 找不到 `winget`：停止，提示本人从 Microsoft Store 更新“应用安装程序”。
- 安装后仍找不到命令：关闭并重新打开终端，再运行脚本。
- 目标目录已存在但不是 Git 仓库：停止，不覆盖、不删除目录。
- GitHub 尚未接受协作者邀请：可以 Clone 公共仓库，但 Push 前必须先接受邀请。
- 权限、登录或网络失败：报告原始错误，不改用第三方镜像或索要令牌。
