#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
generate_site.py — 读取 papers.json，生成单文件静态站点 site/index.html。

特点：
  - 数据内嵌到 HTML（JSON in <script>），无需后端、无 CORS，双击即可看，也能直接部署 GitHub Pages。
  - 按期刊分区，支持：关键词搜索、期刊筛选、中英对照、摘要折叠、关键突破徽标、DOI 一键复制。
"""
import json
import os
import sys
import datetime

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
PAPERS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "papers.json")


def load_config():
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return json.load(f)


HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>期刊每周文献汇总</title>
<style>
  :root{
    --bg:#f5f6f8; --card:#ffffff; --text:#1f2329; --muted:#6b7280;
    --line:#e5e7eb; --accent:#2563eb; --accent2:#dc2626; --hl:#fff7e6; --hl-bd:#f5c542;
    --chip:#eef2ff; --chip-on:#2563eb;
  }
  @media (prefers-color-scheme: dark){
    :root{ --bg:#0f1115; --card:#1a1d23; --text:#e6e8eb; --muted:#9aa3ad;
      --line:#2a2f37; --accent:#60a5fa; --accent2:#f87171; --hl:#2a2410; --hl-bd:#a87f1a;
      --chip:#1e2530; --chip-on:#3b82f6; }
  }
  *{box-sizing:border-box}
  body{margin:0;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"PingFang SC","Microsoft YaHei",sans-serif;
       background:var(--bg);color:var(--text);line-height:1.6}
  header{padding:24px 20px 8px;max-width:980px;margin:0 auto}
  h1{margin:0 0 4px;font-size:24px}
  .sub{color:var(--muted);font-size:13px;margin-bottom:6px}
  .tstatus{font-size:13px;margin-bottom:14px;padding:8px 12px;border-radius:10px}
  .tstatus.on{background:rgba(22,163,74,.12);color:#16a34a;border:1px solid rgba(22,163,74,.3)}
  .tstatus.off{background:rgba(217,119,6,.1);color:#d97706;border:1px solid rgba(217,119,6,.3)}
  .controls{max-width:980px;margin:0 auto;padding:0 20px 12px;position:sticky;top:0;background:var(--bg);z-index:10;padding-top:10px}
  .search{width:100%;padding:10px 12px;border:1px solid var(--line);border-radius:10px;background:var(--card);color:var(--text);font-size:14px}
  .opt{display:flex;align-items:center;gap:6px;margin-top:10px;font-size:13px;color:var(--muted)}
  .opt input{accent-color:var(--accent)}
  .chips{display:flex;flex-wrap:wrap;gap:8px;margin-top:10px}
  .chip{padding:5px 12px;border:1px solid var(--line);border-radius:999px;background:var(--chip);color:var(--text);
        font-size:13px;cursor:pointer;user-select:none;transition:.15s}
  .chip.active{background:var(--chip-on);color:#fff;border-color:var(--chip-on)}
  .chip .n{opacity:.7;font-size:12px;margin-left:4px}
  main{max-width:980px;margin:0 auto;padding:8px 20px 60px}
  .journal-h{margin:26px 0 12px;font-size:19px;border-left:4px solid var(--accent);padding-left:10px}
  .journal-h .cnt{color:var(--muted);font-size:14px;font-weight:400;margin-left:8px}
  .card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:16px 18px;margin-bottom:14px;
        box-shadow:0 1px 2px rgba(0,0,0,.04)}
  .meta{display:flex;flex-wrap:wrap;gap:8px;align-items:center;font-size:12px;color:var(--muted);margin-bottom:6px}
  .badge{background:var(--chip);padding:2px 8px;border-radius:6px}
  .badge.date{background:transparent;border:1px solid var(--line)}
  .title-en{font-size:16px;font-weight:600;margin:2px 0}
  .title-zh{font-size:15px;color:var(--text);margin:2px 0 8px}
  .title-zh::before{content:"中译 ";color:var(--accent);font-size:12px;font-weight:600;margin-right:4px}
  .hl{display:inline-block;margin:6px 0 10px;padding:6px 10px;border-radius:8px;background:var(--hl);
      border:1px solid var(--hl-bd);font-size:13.5px}
  .hl b{color:var(--accent2)}
  details{margin:6px 0;border-top:1px dashed var(--line);padding-top:8px}
  summary{cursor:pointer;color:var(--accent);font-size:13px;outline:none}
  .abs-block{margin:10px 0 0;border-top:1px dashed var(--line);padding-top:10px}
  .ab{font-size:13.5px;margin:8px 0 0;color:var(--text)}
  .ab .lbl{color:var(--muted);font-size:12px;display:block;margin-bottom:2px}
  .ab.noabs{color:var(--muted);font-style:italic;font-size:13px}
  .row{display:flex;gap:8px;flex-wrap:wrap;margin-top:10px}
  .btn{font-size:12.5px;padding:5px 10px;border:1px solid var(--line);border-radius:8px;background:var(--card);
       color:var(--accent);cursor:pointer;text-decoration:none}
  .btn:hover{background:var(--chip)}
  .empty{color:var(--muted);text-align:center;padding:40px}
  footer{max-width:980px;margin:0 auto;padding:0 20px 40px;color:var(--muted);font-size:12px}
  .ok{color:#16a34a}.warn{color:#d97706}
</style>
</head>
<body>
<header>
  <h1>📚 期刊每周文献汇总</h1>
  <div class="sub" id="subline"></div>
  <div class="tstatus" id="tstatus"></div>
</header>
<div class="controls">
  <input id="search" class="search" placeholder="搜索题目 / 摘要 / 关键词…">
  <label class="opt"><input type="checkbox" id="onlyArticle" checked> 仅显示 Article / Research（过滤 News / Comment / Editorial 等）</label>
  <div class="chips" id="chips"></div>
</div>
<main id="main"></main>
<footer>
  数据来源：各期刊官方 RSS 与 Crossref API；题目/摘要/总结/关键突破由通义千问自动生成。每周自动更新。
</footer>

<script>
const META = __META__;
const PAPERS = __DATA__;

const main = document.getElementById('main');
const chipsEl = document.getElementById('chips');
const searchEl = document.getElementById('search');
const onlyArticleEl = document.getElementById('onlyArticle');
const RESEARCH = new Set(['Article','Research','Resource','Report']);
let activeJournal = 'ALL';

// 子标题
const weekLabel = META.weeks_back === 1 ? '近 1 周' : `近 ${META.weeks_back} 周`;
document.getElementById('subline').textContent =
  `更新时间 ${META.generated_at} · ${weekLabel} · 共 ${PAPERS.length} 篇 · 期刊 ${META.journals.length} 本`;

// 翻译状态
const tsEl = document.getElementById('tstatus');
if (META.translation === 'enabled') {
  tsEl.className = 'tstatus on';
  tsEl.textContent = '🔤 翻译：已启用 —— 题目 / 摘要 / 中文总结 / 关键突破已由通义千问生成';
} else {
  tsEl.className = 'tstatus off';
  tsEl.innerHTML = '🔤 翻译：未配置通义 Key —— 在 <b>config.json</b> 填入 TONGYI_API_KEY（或部署时设为 Secrets）后运行 <b>python translate.py</b>，即自动生成中文翻译 / 总结 / 关键突破';
}

// 构建期刊筛选
const journals = META.journals;
function countFor(j){ return j==='ALL' ? PAPERS.length : PAPERS.filter(p=>p.journal===j).length; }
function buildChips(){
  const all = [{name:'ALL',label:'全部'}].concat(journals.map(j=>({name:j,label:j})));
  chipsEl.innerHTML='';
  all.forEach(j=>{
    const c=document.createElement('span');
    c.className='chip'+(j.name===activeJournal?' active':'');
    c.innerHTML = (j.name==='ALL'?'全部':j.label) + '<span class="n">'+countFor(j.name)+'</span>';
    c.onclick=()=>{activeJournal=j.name;buildChips();render();};
    chipsEl.appendChild(c);
  });
}

function esc(s){ return (s||'').replace(/[&<>"]/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[m])); }

function card(p){
  const hasZh = p.title_zh || p.abstract_zh || p.summary_zh || p.highlight;
  const hl = p.highlight ? `<div class="hl">🔑 <b>关键突破：</b>${esc(p.highlight)}</div>` : '';
  const zhTitle = p.title_zh ? `<div class="title-zh">${esc(p.title_zh)}</div>` : '';
  const zhAbs = p.abstract_zh ? `<div class="ab"><span class="lbl">摘要·中译</span>${esc(p.abstract_zh)}</div>` : '';
  const sum = p.summary_zh ? `<div class="ab"><span class="lbl">中文摘要总结</span>${esc(p.summary_zh)}</div>` : '';
  const enAbs = p.abstract
    ? `<div class="ab"><span class="lbl">Abstract（英文摘要原文）</span>${esc(p.abstract)}</div>`
    : `<div class="ab noabs">（该期刊 RSS / 文献类型未提供摘要，无法提取）</div>`;
  const doiBtn = p.doi ? `<button class="btn" data-doi="${esc(p.doi)}">复制 DOI</button>` : '';
  const linkBtn = p.url ? `<a class="btn" href="${esc(p.url)}" target="_blank" rel="noopener">原文链接</a>` : '';
  const zhHint = hasZh ? '' : `<div class="ab" style="color:var(--muted);font-size:12.5px">🔤 配置通义 Key 后自动生成中文翻译 / 总结 / 关键突破</div>`;
  return `<div class="card">
    <div class="meta">
      <span class="badge">${esc(p.journal)}</span>
      <span class="badge date">${esc(p.date)}</span>
      <span class="badge">${esc(p.type||'Article')}</span>
      ${hasZh?'<span class="badge ok">已翻译</span>':'<span class="badge warn">待翻译</span>'}
    </div>
    <div class="title-en">${esc(p.title)||'(无题目)'}</div>
    ${zhTitle}
    ${hl}
    <div class="abs-block">
      ${zhAbs}
      ${enAbs}
      ${sum}
    </div>
    ${zhHint}
    <div class="row">${doiBtn}${linkBtn}</div>
  </div>`;
}

function render(){
  const q = searchEl.value.trim().toLowerCase();
  const onlyArt = onlyArticleEl.checked;
  const groups = {};
  PAPERS.forEach(p=>{
    if(activeJournal!=='ALL' && p.journal!==activeJournal) return;
    if(onlyArt && p.type && !RESEARCH.has(p.type)) return;
    if(q){
      const hay = (p.title+' '+p.title_zh+' '+p.abstract+' '+p.abstract_zh+' '+p.summary_zh+' '+p.highlight).toLowerCase();
      if(!hay.includes(q)) return;
    }
    (groups[p.journal] = groups[p.journal]||[]).push(p);
  });
  let html='';
  const order = META.journals.filter(j=>groups[j]);
  if(!order.length){ html = '<div class="empty">没有匹配的文献。</div>'; }
  order.forEach(j=>{
    html += `<div class="journal-h">${esc(j)}<span class="cnt">${groups[j].length} 篇</span></div>`;
    groups[j].forEach(p=> html += card(p));
  });
  main.innerHTML = html;
  main.querySelectorAll('button[data-doi]').forEach(b=>{
    b.onclick=()=>{ navigator.clipboard.writeText(b.dataset.doi).then(()=>{ b.textContent='已复制 ✓'; setTimeout(()=>b.textContent='复制 DOI',1500);}); };
  });
}

searchEl.addEventListener('input', render);
onlyArticleEl.addEventListener('change', render);
buildChips();
render();
</script>
</body>
</html>"""


def main():
    cfg = load_config()
    papers = json.load(open(PAPERS_PATH, encoding="utf-8"))
    journals_order = []
    for p in papers:
        if p["journal"] not in journals_order:
            journals_order.append(p["journal"])

    meta = {
        "generated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "weeks_back": int(cfg.get("weeks_back", 1)),
        "journals": journals_order,
        "translation": "enabled" if any(p.get("title_zh") for p in papers) else "disabled",
    }

    data_json = json.dumps(papers, ensure_ascii=False)
    data_json = data_json.replace("</", "<\\/")  # 防止 </script> 截断
    meta_json = json.dumps(meta, ensure_ascii=False).replace("</", "<\\/")

    html = HTML_TEMPLATE.replace("__META__", meta_json).replace("__DATA__", data_json)

    if len(sys.argv) > 1:
        out_path = sys.argv[1]
    else:
        out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), cfg.get("output", "site/index.html"))
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"站点已生成 -> {out_path}（{len(papers)} 篇，{len(journals_order)} 本期刊）")


if __name__ == "__main__":
    main()
