这是一份为你量身定制的 README.md 文档。它清晰地解释了这个项目的功能、如何使用以及如何管理订阅。

你可以直接在你的 GitHub 仓库根目录下创建一个名为 README.md 的文件，然后将下面的内容复制粘贴进去。

📚 PubMed Daily DeepReader (自动化医学文献日报)
这是一个基于 GitHub Actions 和 Python 的自动化文献追踪工具。它每天自动抓取指定的 PubMed RSS 订阅源，利用自然语言处理技术提取文章结构（背景、方法、结果、结论），调用翻译接口生成中文摘要，并构建一个现代化的交互式网页供科研人员快速阅读。

无需服务器，零成本，全自动运行。

✨ 核心功能
多源订阅：通过 feeds.txt 轻松管理多个 PubMed RSS 链接。

智能结构化：自动识别并分离摘要中的 Background, Methods, Results, Conclusion，解决长文本阅读困难。

中英对照：左侧文章列表，右侧详情页。支持点击展开英文原文，关键术语和标题自动加粗。

全自动更新：

📅 每日定时：北京时间每天早上 8:00 自动抓取更新。

🚀 即时触发：修改订阅列表 (feeds.txt) 后立即自动重新生成。

历史存档：自动保存每日生成的 HTML 文件，方便回溯。

现代化 UI：基于 Tailwind CSS 和 Alpine.js 构建，支持关键词高亮、作者显示及源链接跳转。

📖 使用指南
1. 如何查看日报？
访问项目的 GitHub Pages 链接（在仓库 Settings -> Pages 中查看）：

https://[你的用户名].github.io/[仓库名称]/

2. 如何添加/修改订阅？
不需要懂代码，只需修改文本文件：

在仓库中找到 feeds.txt 文件。

点击右上角的 ✏️ (编辑) 图标。

粘贴你的 PubMed RSS 链接（一行一个）。

如何获取链接：在 PubMed 搜索关键词 -> 点击 "Create RSS" -> 设置数量 -> 复制橘黄色 XML 链接。

点击 Commit changes 保存。

等待 1-2 分钟，GitHub Actions 会自动运行并更新网页。

⚙️ 部署教程 (如果你想自己搭建)
如果你是 Fork 本项目或是重新搭建，请确保完成以下设置：

1. 环境准备
无需本地安装 Python，所有依赖由 GitHub Actions 云端环境自动安装（详见 .github/workflows/daily_run.yml）。

2. 开启 GitHub Pages
为了让生成的 HTML 能被访问：

进入仓库 Settings (设置)。

点击左侧栏 Pages。

在 Build and deployment 下：

Source: 选择 Deploy from a branch

Branch: 选择 main 分支，文件夹选择 /docs (⚠️ 注意：一定要选 docs，因为网页生成在那里)。

点击 Save。

3. 配置权限 (如果报错)
如果 Actions 运行失败提示权限不足：

进入仓库 Settings -> Actions -> General。

找到 Workflow permissions。

勾选 Read and write permissions。

点击 Save。

🛠️ 技术栈
后端逻辑: Python 3.9

RSS 解析: feedparser

自动翻译: deep-translator (Google Translate API)

文本处理: 正则表达式 (Regex) + markdown

前端界面: HTML5 + Tailwind CSS (CDN) + Alpine.js (CDN) + Marked.js

CI/CD: GitHub Actions

⚠️ 免责声明
翻译准确性：本项目使用的是机器翻译服务，翻译结果仅供参考，准确性无法与人工翻译相比。专业术语请务必对照英文原文。

API 限制：频繁触发可能会受到翻译接口的速率限制，建议合理设置 RSS 抓取数量（建议单个源不超过 20 篇）。

📂 目录结构说明
Plaintext

.
├── .github/workflows/
│   └── daily_run.yml    # 自动化流程配置 (定时任务 + 触发器)
├── docs/                # [自动生成] 存放生成的 HTML 网页
│   ├── index.html       # 最新日报
│   └── archive_...html  # 历史归档
├── main.py              # 核心 Python 脚本 (爬取、解析、翻译、生成)
├── feeds.txt            # 配置文件 (订阅链接列表)
└── README.md            # 项目说明文档
