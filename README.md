
---

# 🧬 PubMed Daily DeepReader

> **零成本、全自动的医学文献情报站**
> 🚀 **核心优势**：利用 PubMed API 抓取完整的结构化摘要（背景/方法/结果/结论），告别 RSS 的“残缺”信息，提供精准的中英对照阅读体验。

## 📖 简介 (Introduction)

**PubMed Daily DeepReader** 是一个为医学科研人员打造的自动化文献追踪工具。

传统的 RSS 订阅往往只提供被截断的纯文本摘要，阅读体验极差。本项目通过 **Biopython** 直接调用 **PubMed Entrez API**，下载论文的原始 XML 数据，精准提取并分离 `Background`、`Methods`、`Results`、`Conclusion` 等段落，结合机器翻译生成排版精美的中文日报。

整个系统运行在 **GitHub Actions** 上，无需服务器，完全免费。

---

## ✨ 核心功能 (Key Features)

* **🔍 API 深度抓取**：不仅仅是 RSS 搬运工。系统利用 PMID 调用 API 获取官方结构化数据，确保摘要完整、分段清晰。
* **🇨🇳 智能中英对照**：
* 左侧目录快速筛选，右侧详情深度阅读。
* **结构化翻译**：自动识别段落标签（如 **RESULTS**），强制加粗换行，避免翻译引擎混淆结构。
* **关键词提取**：自动获取并翻译 MeSH 关键词。


* **📂 便捷订阅管理**：无需修改代码，只需编辑 `feeds.txt` 文本文件即可增删订阅源。
* **⚡ 全自动运行**：
* 📅 每天北京时间 **08:00** 定时抓取。
* 🔄 修改订阅列表后 **立即触发** 更新。


* **📱 现代化阅读界面**：基于 Tailwind CSS 打造，适配手机与桌面端，提供类原生 App 的阅读体验。

---

## 🚀 快速开始 (Getting Started)

### 1. 如何阅读日报？

直接访问本仓库的 GitHub Pages 页面：

> **[点击这里查看生成的日报网页]**
> *(请在你的仓库 Settings -> Pages 中获取具体链接，通常是 `https://你的用户名.github.io/仓库名/`)*

### 2. 如何管理订阅？

你不需要懂编程，只需要像写记事本一样操作：

1. 在仓库中打开 **`feeds.txt`** 文件。
2. 点击右上角的 **✏️ (Edit)** 按钮。
3. 粘贴你的 PubMed RSS 链接（一行一个）。
* *提示：在 PubMed 搜索关键词 -> Create RSS -> 复制 XML 链接。*


4. 点击下方的 **Commit changes** 保存。
5. **等喝口水的时间（约 1-2 分钟）**，页面就会自动刷新。

---

## 🛠️ 部署指南 (Deployment)

如果你想 Fork 本项目搭建属于自己的阅读器，请按照以下步骤操作：

### 第一步：Fork 仓库

点击右上角的 **Fork** 按钮，将项目复制到你的账号下。

### 第二步：配置权限 (至关重要)

GitHub Actions 需要有写入仓库的权限才能更新网页：

1. 进入仓库 **Settings** -> **Actions** -> **General**。
2. 滚动到 **Workflow permissions** 区域。
3. 勾选 **Read and write permissions**。
4. 点击 **Save**。

### 第三步：开启 GitHub Pages

让生成的 HTML 能被公网访问：

1. 进入仓库 **Settings** -> **Pages**。
2. 在 **Build and deployment** 下：
* **Source**: 选择 `Deploy from a branch`。
* **Branch**: 选择 `main` 分支，文件夹选择 `/docs` (**⚠️ 注意：必须选 /docs**)。


3. 点击 **Save**。

### 第四步：设置 API 邮箱 (可选但推荐)

为了防止被 PubMed 限制访问，建议在 `main.py` 中填入你的真实邮箱：
打开 `main.py`，找到第 13 行：

```python
Entrez.email = "你的邮箱@example.com"

```

---

## 🤖 自动化原理 (Technical Details)

本系统的工作流如下：

1. **Trigger**: 每天定时 (Cron) 或 检测到 `feeds.txt` 变动 (Push)。
2. **Fetch RSS**: Python 读取订阅列表，获取最新文章的 ID (PMID)。
3. **Fetch API**: 使用 `Biopython` 向 NCBI Entrez API 批量请求 XML 数据。
4. **Parse & Translate**:
* 解析 XML 中的 `Label` 属性 (如 `Label="METHODS"`)。
* 调用 `Google Translator` 进行分段翻译。
* 组装 Markdown 格式文本。


5. **Generate HTML**: 渲染带有 Alpine.js 交互逻辑的静态网页。
6. **Deploy**: 自动将生成的网页推送到 `docs/` 目录，GitHub Pages 自动展示。

---

## ❓ 常见问题 (FAQ)

#### Q: 为什么有时候自动运行会报错？

**A:** 如果你手动修改了代码，而 Actions 正在运行时，可能会发生“冲突”。

* **解决方法**：无需担心。我们在工作流中添加了 `git pull --rebase` 机制，机器人会自动尝试修复冲突。如果依然失败，手动在本地 `git pull` 一下即可。

#### Q: 可以订阅多少个链接？

**A:** 理论上无限，但建议不要过多（例如超过 50 个），以免 API 请求时间过长导致 GitHub Actions 超时（限时 6 小时）。

#### Q: 为什么有些老文章没有结构化摘要？

**A:** 结构化摘要（Background/Results 等）依赖于 PubMed 数据库的收录质量。部分年代久远的论文或非标准格式的论文可能没有这些标签，系统会自动回退到全文翻译模式。

---

## ⚠️ 免责声明

* 本项目仅供科研学术交流使用。
* 中文翻译由机器生成，准确性仅供参考，临床决策请务必以英文原文为准。
* 请遵守 NCBI/PubMed 的 [使用条款](https://www.ncbi.nlm.nih.gov/home/about/policies/)，不要进行恶意的超高频请求。

---

*Made with ❤️ by [你的名字]*
