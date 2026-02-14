---
name: cross-worktree-sync
description: Read committed files and recent history from the other side's branch (frontend ↔ backend). Use when you need to check the other agent's SESSION_NOTES.md, CLAUDE.md, code changes, or any committed file. Trigger phrases include "查看对方状态", "sync with backend/frontend", "check other branch".
---

# Cross-Worktree Sync

通用工具型流程：从当前 worktree 读取对方分支已 commit 的文件内容。本 SKILL 只负责"发现分支 + 读取文件"，不做语义分析——解读逻辑由调用方决定。

## 1) Determine current side

从当前分支名推断本方 side：

```bash
git rev-parse --abbrev-ref HEAD
```

- `feat-frontend-*` → side = frontend，other side = backend
- `feat-backend-*` → side = backend，other side = frontend
- 如果无法推断，要求用户或调用方显式指定

## 2) Discover the other side's branch

列出对方的特性分支，找到最近活跃的那个：

```bash
# 列出对方所有本地特性分支
git branch --list 'feat-<other-side>-*'

# 如果有多个候选，取最近 commit 的分支
git log -1 --format='%H %ci' <candidate-branch>
```

确认分支存在后，记录：
- 对方分支名（如 `feat-backend-v1`）
- 对方 HEAD commit（`git rev-parse --short <branch>`）

## 3) Read committed files

根据调用方需要，使用以下命令读取对方已 commit 的内容：

**读取单个文件：**
```bash
git show <branch>:<filepath>
```

常见目标文件：
- `SESSION_NOTES.md` — 对方的 handoff 记录
- `CLAUDE.md` — 项目规范（检查是否有差异）
- 任意代码文件 — 按需指定

**查看最近 commit 摘要：**
```bash
git log --oneline -N <branch>
```

**对比特定文件差异（可选）：**
```bash
git diff <my-branch>...<other-branch> -- <filepath>
```

## 4) Output results

输出以下信息，供调用方或用户进一步分析：

```
对方分支: <branch-name>
对方 HEAD: <short-hash> (<commit-date>)

--- 请求的文件内容 ---
<file content>
```

**本 SKILL 不负责**：
- 语义分析（dep 是否已解决、risk 是否消除）
- 决策建议（是否需要更新本方记录）
- 文件修改（只读操作）

这些职责由调用方（其他 SKILL、Agent、用户）自行完成。
