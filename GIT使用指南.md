# Git 版本控制使用指南

本项目已配置 Git 版本控制，帮助你安全地迭代开发。

## 远程仓库

项目已备份到 GitHub：

```
https://github.com/bobjason2020/backtest.git
```

## 日常开发工作流

### 1. 开发新功能前 - 创建分支

```bash
# 创建并切换到新分支
git checkout -b feature/功能名称

# 例如：添加新的回测策略
git checkout -b feature/new-strategy
```

### 2. 开发过程中 - 频繁提交

```bash
# 查看修改了哪些文件
git status

# 查看具体修改内容
git diff

# 添加修改的文件
git add .

# 提交（建议小步提交，每个功能点一次）
git commit -m "添加xxx功能"
```

### 3. 功能完成后 - 合并到主分支

```bash
# 切回主分支
git checkout main

# 合并功能分支
git merge feature/功能名称

# 可选：删除已合并的分支
git branch -d feature/功能名称
```

### 4. 同步到 GitHub

```bash
# 推送到远程
git push

# 从远程拉取最新代码
git pull
```

## 常用命令速查

### 查看状态

| 命令 | 说明 |
|------|------|
| `git status` | 查看当前修改状态 |
| `git log --oneline` | 查看提交历史（简洁） |
| `git log` | 查看完整提交历史 |
| `git diff` | 查看未暂存的修改 |
| `git diff --staged` | 查看已暂存的修改 |
| `git branch` | 查看所有分支 |
| `git remote -v` | 查看远程仓库地址 |

### 撤销操作

| 命令 | 说明 |
|------|------|
| `git checkout -- 文件名` | 撤销工作区修改（未add） |
| `git reset HEAD 文件名` | 取消暂存（已add，未commit） |
| `git reset --soft HEAD~1` | 撤销最近一次提交（保留修改） |
| `git reset --hard HEAD~1` | 撤销最近一次提交（丢弃修改）⚠️ |

### 分支操作

| 命令 | 说明 |
|------|------|
| `git branch 分支名` | 创建新分支 |
| `git checkout 分支名` | 切换分支 |
| `git checkout -b 分支名` | 创建并切换分支 |
| `git merge 分支名` | 合并分支到当前分支 |
| `git branch -d 分支名` | 删除已合并的分支 |

### 远程操作

| 命令 | 说明 |
|------|------|
| `git push` | 推送到远程仓库 |
| `git pull` | 拉取远程更新 |
| `git clone 地址` | 克隆远程仓库 |
| `git remote -v` | 查看远程仓库 |

## 推荐的分支命名规范

| 前缀 | 用途 | 示例 |
|------|------|------|
| `feature/` | 新功能 | `feature/add-export` |
| `fix/` | 修复bug | `fix/date-bug` |
| `refactor/` | 重构代码 | `refactor/optimize-calc` |
| `docs/` | 文档更新 | `docs/update-readme` |

## 推荐的提交信息规范

```
<类型>: <简短描述>

[可选的详细描述]
```

类型：
- `feat`: 新功能
- `fix`: 修复bug
- `refactor`: 重构
- `docs`: 文档
- `style`: 格式调整
- `test`: 测试

示例：
```
feat: 添加定投频率自定义功能
fix: 修复日期选择越界问题
refactor: 优化回测计算性能
```

## 安全开发示例

### 场景：添加一个新功能

```bash
# 1. 确保在主分支上
git checkout main

# 2. 创建功能分支
git checkout -b feature/add-simulation

# 3. 开发... 修改代码...

# 4. 随时可以查看修改
git status
git diff

# 5. 提交到功能分支
git add .
git commit -m "feat: 添加蒙特卡洛模拟功能"

# 6. 继续开发... 如果改坏了
git checkout -- .  # 撤销所有未提交的修改

# 7. 功能完成，测试通过，合并到主分支
git checkout main
git merge feature/add-simulation

# 8. 推送到 GitHub
git push

# 9. 打标签保存版本
git tag -a v1.1 -m "版本1.1: 添加蒙特卡洛模拟"
git push --tags
```

### 场景：想尝试激进改动但怕改坏

```bash
# 方法1：使用分支
git checkout -b experiment/risky-change
# ... 改代码 ...
# 如果成功：合并；如果失败：切回main删除分支

# 方法2：使用stash暂存当前修改
git stash  # 暂存当前修改
# ... 做其他事 ...
git stash pop  # 恢复修改
```

## 版本标签

```bash
# 创建标签
git tag -a v1.0 -m "版本1.0"

# 查看所有标签
git tag

# 查看标签详情
git show v1.0

# 推送标签到远程
git push --tags

# 切换到某个标签
git checkout v1.0
```

## .gitignore 说明

当前配置忽略：
- `.venv/` - 虚拟环境
- `__pycache__/` - Python缓存
- `原始数据/*.xlsx` - 原始数据文件
- `可用数据/*.xlsx` - 生成的数据文件

如需跟踪数据文件，修改 `.gitignore` 文件。

## 紧急情况

### 不小心提交了错误的代码？

```bash
# 撤销最近一次提交（保留修改）
git reset --soft HEAD~1

# 修改后再提交
git add .
git commit -m "正确的提交信息"
```

### 想回到之前的某个版本？

```bash
# 查看历史
git log --oneline

# 回到某个版本（只读模式）
git checkout 提交哈希

# 返回最新
git checkout main
```

### 改坏了想重来？

```bash
# 只要没commit，都可以撤销
git checkout -- .
git clean -fd  # 删除未跟踪的文件（慎用）
```

### 远程推送失败？

如果遇到 `ssh: connect to host github.com port 22: Connection refused`，说明 SSH 端口被阻止。

**解决方案**：使用 HTTPS 代替 SSH

```bash
# 切换到 HTTPS 地址
git remote set-url origin https://github.com/用户名/仓库名.git

# 再次推送
git push
```

## 完整工作流图

```
本地开发 → git add → git commit → git push → GitHub
    ↑                                          ↓
    └──────────── git pull ←───────────────────┘
```
