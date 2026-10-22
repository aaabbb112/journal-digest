# 期刊每周文献汇总（journal-digest）

一个**打开即本周自动更新**的网页，汇总 **Nature Immunology / Nature / Science / Cell / JAAD / JID** 六本期刊近一周的 Article 论文，
展示「题目 / 英文摘要 / 中文翻译 / 中文摘要总结 / 关键突破」，按期刊分区。
不用再挨个点开各官网——每次打开网页就自动拉最新；某刊本周没更新则自动回退到内嵌离线快照。

---

## 🌐 已部署（Live）

**https://aaabbb112.github.io/journal-digest/**

打开即本周实时（站点纯静态，文献由你浏览器实时从 PubMed 抓取）。可分享、可书签。

---

## 工作原理

六本期刊**全部经 PubMed（E-utilities）实时抓取**，按 ISSN + 发布日期（PDAT）过滤近 7 天，并按文献类型（PublicationType）自动只保留
Article / Journal Article / Research Article / Review，剔除 News / Comment / Letter / Editorial / Erratum 等。
PubMed 返回 `Access-Control-Allow-Origin: *`，**浏览器可直连，真·实时且自带摘要**。

整个 `index.html` 是**单文件、零依赖、零后端**：CSS/JS/快照数据全部内联，部署到任意静态托管（GitHub Pages / 任意 http 服务器）即可。

- **通过 https（GitHub Pages 或本地服务器）打开**：页面即实时抓取本周六刊。
- **以本地文件 `file://` 双击打开**：浏览器会拦截跨域 `fetch`，此时页面**自动回退显示内嵌离线快照**（标注"快照"）+ 提示横幅。

> 快照是构建时已内嵌的数据，保证"打开不空白"；实时数据需通过服务器 / Pages 打开获得。

---

## 快速开始（本地）

### 本地服务器打开（真·实时）

在 `journal-digest/` 目录下执行任一条，然后访问 `http://localhost:8080/index.html`：

```bash
python -m http.server 8080        # 访问 http://localhost:8080/index.html
# 或
npx serve -l 8080 .
```

### 直接双击 `index.html`

会显示**内嵌离线快照**（标注"快照"）+ 一条提示横幅（`file://` 不允许跨域 `fetch`，非 bug）。

---

## 部署到 GitHub Pages（已帮你完成）

站点纯静态、自包含，推上去就能用。本仓库已部署为**分支式 Pages**：从 `main` 分支根目录直接发布（根目录的 `index.html` / `demo_translated.html` / `.nojekyll`）。

> 说明：本环境出网走代理，代理会拦截 `.github/workflows/` 路径，因此无法用 GitHub Actions 工作流发布；
> 改用"分支式 Pages"效果完全一致（静态站点本就在浏览器端运行）。若你**在自己的机器**上推送，仍可用工作流方式
> （把 `.github/workflows/deploy-pages.yml` 加回仓库、Settings → Pages → Source 选 "GitHub Actions" 即可）。

**日常更新（在你自己的机器上）**：

```bash
git clone https://github.com/aaabbb112/journal-digest.git
cd journal-digest
# 编辑 index.html 等后：
git add . && git commit -m "update" && git push -u origin main
```

推送后几分钟内，GitHub Pages 自动重新发布（站点内容由访客浏览器实时抓取，无需定时构建）。

---

## 顶部状态与横幅

- 状态条：每本期刊显示「● 实时 / ● 快照 / ● 获取失败」。
- 横幅：当实时被拦截或某刊回退快照时，给出明确提示与解决方式。
- 工具栏：`🔄 立即刷新` 重新抓取；`⚙ 翻译设置` 配置通义 Key；`🌐 全部翻译` 批量翻译。
- 搜索框 + 「仅显示 Article」开关 + 按期刊筛选 chips。

---

## 中文翻译（可选增强）

翻译用**通义千问**。在 **⚙ 翻译设置** 填入 DashScope API Key（仅存本机浏览器，不上传）：

- 点卡片「翻译此篇」逐篇翻译，或顶部「🌐 全部翻译」批量翻译；
- 生成 `题目翻译 / 摘要翻译 / 中文摘要总结 / 关键突破`；
- 结果**按 DOI 长期缓存**，刷新/重开不重复消耗额度；
- 若直连 DashScope 被浏览器 CORS 拦，在「翻译代理 URL」填一个转发 POST 的代理即可。

---

## 增加 / 修改期刊

期刊列表**硬编码在 `index.html` 顶部的 `SOURCES` 数组**，改这里即可：

```js
const SOURCES = [
  { journal: "Nature Immunology", kind: "pubmed", issn: "1529-2908" },
  { journal: "Nature",            kind: "pubmed", issn: "0028-0836" },
  { journal: "Science",           kind: "pubmed", issn: "0036-8075" },
  { journal: "Cell",              kind: "pubmed", issn: "0092-8674" },
  { journal: "JAAD",              kind: "pubmed", issn: "0190-0622" },
  { journal: "JID",               kind: "pubmed", issn: "0022-202X" },
];
```

只要目标期刊被 PubMed 收录（绝大多数生物医学/自然科学期刊都收录），填对 **ISSN** 即可加入，且自动带摘要。

---

## 离线分发（可选）

`demo_translated.html` 是一份**完全翻译好、纯静态**的离线样本，可单独发给他人或放到内网，不依赖在线翻译。

> 注：本项目为基于开源思路（hehuifeng/rss_site、xionglingsong/rss-translation-studies）自搭的**定制精简版**，独立维护。
