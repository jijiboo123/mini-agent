# 把 mini-agent 推到 GitHub（10 分钟）

简历上写了「Github 个人项目」，**推上去之后这句话才成立**。没有仓库链接，面试官点不开，就等于没有。

## 1. 先在 GitHub 建仓库

1. 打开 https://github.com/new
2. Repository name 填 `mini-agent`
3. **不要**勾 "Add a README file"、"Add .gitignore"、"Choose a license"（本地已经有了，勾了会冲突）
4. 点 Create repository，页面会显示仓库地址 `https://github.com/<你的用户名>/mini-agent.git`

## 2. 在本地推送

打开 PowerShell，逐行执行：

```powershell
cd "D:\deepseek harness工作台\实习求职\mini-agent"

git log --oneline          # 应该能看到 1 个提交：feat: 最小 Agent 运行时…
git branch -M main
git remote add origin https://github.com/<你的用户名>/mini-agent.git
git push -u origin main
```

- 第一次推送会弹窗要求登录：选 **Sign in with your browser**（浏览器授权）最省事；
- 如果弹出用户名/密码，密码要填 **Personal Access Token**（GitHub 设置 → Developer settings → Personal access tokens → Fine-grained token，勾 `Contents: Read and write`），不是登录密码。

## 3. 验证

浏览器打开 `https://github.com/<你的用户名>/mini-agent`，应该能看到：
- README 正常渲染（不是乱码）
- 目录里有 `agent/`、`tests/`、`docs/`
- 提交记录里有你那条 commit

## 4. 把链接填回简历

打开 `桌面\2407030220 刘佳吉 职业发展大作业\刘佳吉-软件研发实习生-简历-含照片-v2.docx`，
把项目标题那一行的 `Github 个人项目` 改成：

```
github.com/<你的用户名>/mini-agent
```

（右键超链接或直接改文字都行。）

## 5. 推完之后必须做的两件事

1. **把 `docs/面试问答.md` 从头读一遍**，12 个问题都能用自己的话答出来。答不出来说明这个项目还不算你的。
2. **自己跑一遍**，确认你看到的现象和 README 一致：

```powershell
cd "D:\deepseek harness工作台\实习求职\mini-agent"
$env:PYTHONPATH = "D:\deepseek harness工作台\实习求职\.pylibs"
python -m agent.cli "帮我算 12*(3+4)" --backend mock
python -m agent.cli --tools
```

看到 `value: 84` 和 4 个工具就对了。

## 常见问题

| 现象 | 原因 / 处理 |
|---|---|
| `git: 无法将"git"项识别…` | 关掉 PowerShell 重开（安装后 PATH 要重载） |
| `remote origin already exists` | `git remote set-url origin <新地址>` |
| `error: failed to push, non-fast-forward` | 建仓库时勾了 README，先 `git pull --rebase origin main` 再推 |
| 弹窗登录失败 | 改用 PAT：`git remote set-url origin https://<用户名>:<token>@github.com/<用户名>/mini-agent.git`（推完记得改回不带 token 的地址） |
