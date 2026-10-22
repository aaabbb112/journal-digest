#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fetch_papers.py — 抓取各期刊近一周的论文（抓取阶段，未翻译）。

数据源：
  - RSS：Nature / Nature Immunology / Science / Cell（自带标题+摘要，最稳）
  - PubMed(E-utilities)：JAAD(0190-9622) / JID(0022-202X)
        （Elsevier 系期刊无干净 RSS、Crossref 又缺摘要，PubMed 稳定返回标题+摘要且免 Key）

类型识别：尽量只保留 Article / Research 类，过滤 News / Comment / Editorial / Correction 等；
          前端另提供"仅看 Article"开关。

输出：papers_raw.json（供 translate.py 使用）
"""
import json
import os
import re
import datetime
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET

import feedparser

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
UA = {"User-Agent": "journal-digest/1.0 (mailto:you@example.com)"}
ETOOL = "journal-digest"
EMAIL = "you@example.com"

# 研究型文献类型（用于"仅看 Article"判定）
RESEARCH_TYPES = {"Article", "Research", "Letter", "Resource", "Report"}
NON_RESEARCH_HINTS = ("news", "comment", "editorial", "correction", "books",
                      "career", "obituary", "podcast", "corrigendum", "retraction")


def load_config():
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return json.load(f)


def clean_html(s):
    if not s:
        return ""
    s = re.sub(r"<\s*(jats:)?[^>]+>", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _entry_doi(entry):
    doi = entry.get("prism_doi") or ""        # Nature(RDF) 等用 prism:doi
    if doi:
        return doi
    for lk in entry.get("links", []):
        if "doi" in (lk.get("href") or ""):
            doi = lk["href"]
    if not doi:
        m = re.search(r"10\.\d{4,9}/[^\s\"'<>)]+", entry.get("link", ""))
        if m:
            doi = m.group(0)
    return doi


def classify_rss_type(source_name, entry):
    # ---- Nature 系：DOI 前缀 + 标题前缀 双重判断 ----
    # dXXXXX = 新闻/评论/书评/职业；sXXXXX 多为研究，但勘误/Matters Arising 也用 s 前缀，需用标题排除
    if source_name.startswith("Nature"):
        if re.search(r"/d\d{5}-", _entry_doi(entry)):
            return "Other"          # 新闻 / 评论 / 书评 / 职业类
        title = (entry.get("title") or "").lower()
        NON = ("author correction", "correction", "matters arising", "comment", "news",
               "perspective", "review", "editorial", "correspondence", "book review",
               "technology feature", "career feature", "retraction", "amendment",
               "obituary", "world view", "corrigendum")
        if any(title.startswith(n) for n in NON):
            return "Other"
        return "Article"
    # ---- Science 等：用 dc:type 显式黑白名单 ----
    dc = (entry.get("dc_type") or "").lower()
    if dc:
        NON = ("news", "comment", "editorial", "letter", "books", "career",
               "obituary", "perspective", "in depth", "highlight", "feature",
               "working life", "policy forum", "expert voices", "errata",
               "correction", "corrigendum", "retraction", "analysis",
               "review", "podcast")
        RES = ("research article", "research", "original article", "article",
               "report", "resource", "brief communication")
        if any(h in dc for h in NON):
            return "Other"
        if any(r in dc for r in RES):
            return "Article"
        return ""
    return ""  # 未知，前端默认保留


def parse_rss_date(entry):
    for key in ("published_parsed", "updated_parsed"):
        v = entry.get(key)
        if v:
            try:
                return datetime.datetime(*v[:6])
            except Exception:
                pass
    for key in ("published", "updated"):
        v = entry.get(key)
        if v:
            try:
                t = feedparser._parse_date(v)
                if t:
                    return datetime.datetime(*t[:6])
            except Exception:
                pass
    return None


def fetch_rss(source, since):
    name, url = source["name"], source["url"]
    print(f"[RSS] {name}: {url}")
    try:
        d = feedparser.parse(url)
    except Exception as ex:
        print(f"  ! 解析失败: {ex}")
        return []
    out = []
    for e in d.entries:
        dt = parse_rss_date(e)
        if dt is None or dt < since:
            continue
        title = clean_html(e.get("title", ""))
        abstract = clean_html(e.get("summary", ""))
        link = e.get("link", "")
        doi = ""
        for lk in e.get("links", []):
            if "doi" in (lk.get("href") or ""):
                doi = lk["href"]
        if not doi:
            m = re.search(r"10\.\d{4,9}/[^\s\"'<>)]+", link)
            if m:
                doi = m.group(0)
        out.append({
            "journal": name,
            "title": title,
            "abstract": abstract,
            "doi": doi,
            "url": link,
            "date": dt.strftime("%Y-%m-%d") if dt else "",
            "type": classify_rss_type(name, e),
        })
    print(f"  -> 窗口内 {len(out)} 篇（Article 类 {sum(1 for x in out if x['type']=='Article')} 篇）")
    return out


def _local_iter(elem, local):
    for e in elem.iter():
        if e.tag.endswith(local):
            yield e


def fetch_pubmed(source, since):
    issn = source["issn"]
    name = source["name"]
    since_s = since.strftime("%Y/%m/%d")
    today_s = datetime.datetime.now(datetime.timezone.utc).strftime("%Y/%m/%d")
    term = f'{issn}[ISSN] AND {since_s}:{today_s}[dp]'
    esearch = ("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
               f"?db=pubmed&term={urllib.parse.quote(term)}&datetype=dp"
               f"&retmax=200&retmode=json&tool={ETOOL}&email={EMAIL}")
    print(f"[PubMed] {name} (ISSN {issn}): {term}")
    try:
        with urllib.request.urlopen(urllib.request.Request(esearch, headers=UA), timeout=40) as r:
            ids = json.load(r).get("esearchresult", {}).get("idlist", [])
    except Exception as ex:
        print(f"  ! esearch 失败: {ex}")
        return []
    if not ids:
        print("  -> 窗口内 0 篇")
        return []
    efetch = ("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
              f"?db=pubmed&id={','.join(ids)}&rettype=xml&tool={ETOOL}&email={EMAIL}")
    try:
        with urllib.request.urlopen(urllib.request.Request(efetch, headers=UA), timeout=60) as r:
            xml_text = r.read().decode("utf-8", "replace")
    except Exception as ex:
        print(f"  ! efetch 失败: {ex}")
        return []

    out = []
    try:
        root = ET.fromstring(xml_text)
    except Exception as ex:
        print(f"  ! XML 解析失败: {ex}")
        return []
    for art in _local_iter(root, "PubmedArticle"):
        # 题目
        tnode = next(_local_iter(art, "ArticleTitle"), None)
        title = clean_html(tnode.text) if tnode is not None and tnode.text else ""
        # 摘要
        abs_parts = []
        for a in _local_iter(art, "AbstractText"):
            if a.text:
                abs_parts.append(a.text)
        abstract = clean_html(" ".join(abs_parts))
        # DOI
        doi = ""
        for e in _local_iter(art, "ELocationID"):
            if e.get("EIdType") == "doi" and e.text:
                doi = e.text
        if not doi:
            for e in _local_iter(art, "ArticleId"):
                if e.get("IdType") == "doi" and e.text:
                    doi = e.text
        # 日期
        date_str = ""
        pd = next(_local_iter(art, "PubDate"), None)
        if pd is not None:
            y = next(_local_iter(pd, "Year"), None)
            m = next(_local_iter(pd, "Month"), None)
            d = next(_local_iter(pd, "Day"), None)
            if y is not None and y.text:
                ms = m.text if (m is not None and m.text) else "1"
                ds = d.text if (d is not None and d.text) else "1"
                mm = {"jan":1,"feb":2,"mar":3,"apr":4,"may":5,"jun":6,"jul":7,
                      "aug":8,"sep":9,"oct":10,"nov":11,"dec":12}.get(ms.lower(), None)
                if mm is None:
                    try: mm = int(ms)
                    except Exception: mm = 1
                try:
                    date_str = datetime.datetime(int(y.text), int(mm), int(ds)).strftime("%Y-%m-%d")
                except Exception:
                    date_str = f"{y.text}-{ms}-{ds}"
        # 类型
        pts = [e.text for e in _local_iter(art, "PublicationType") if e.text]
        ptype = ""
        if "Journal Article" in pts:
            ptype = "Article"
        elif "Review" in pts:
            ptype = "Review"
        elif "Letter" in pts:
            ptype = "Letter"
        elif "Editorial" in pts:
            ptype = "Editorial"
        elif pts:
            ptype = pts[0]
        if ptype not in RESEARCH_TYPES and ptype not in ("Review", "Letter", "Editorial"):
            ptype = ""  # 未知保留
        out.append({
            "journal": name,
            "title": title,
            "abstract": abstract,
            "doi": doi,
            "url": (f"https://doi.org/{doi}" if doi else f"https://pubmed.ncbi.nlm.nih.gov/{ids[0]}/"),
            "date": date_str,
            "type": ptype,
        })
    print(f"  -> 窗口内 {len(out)} 篇（Article 类 {sum(1 for x in out if x['type']=='Article')} 篇，无摘要 {sum(1 for x in out if not x['abstract'])} 篇）")
    return out


def main():
    cfg = load_config()
    weeks = int(cfg.get("weeks_back", 1))
    since = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None) - datetime.timedelta(days=weeks * 7)
    print(f"抓取窗口：近 {weeks} 周（自 {since.strftime('%Y-%m-%d')} 起，UTC）\n")

    papers = []
    for s in cfg.get("sources", []):
        if s.get("type") == "rss":
            papers += fetch_rss(s, since)
        elif s.get("type") == "pubmed":
            papers += fetch_pubmed(s, since)

    best = {}
    for p in papers:
        key = (p["doi"] or p["title"].lower().strip())
        if not key:
            continue
        if key not in best or (not best[key]["abstract"] and p["abstract"]):
            best[key] = p
    uniq = list(best.values())
    uniq.sort(key=lambda x: x["date"], reverse=True)

    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "papers_raw.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(uniq, f, ensure_ascii=False, indent=2)
    print(f"\n共抓取唯一论文 {len(uniq)} 篇 -> {out_path}")


if __name__ == "__main__":
    main()
