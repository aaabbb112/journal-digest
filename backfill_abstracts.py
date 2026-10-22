#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
backfill_abstracts.py — 为 papers.json 中缺失英文摘要的文章补回摘要。

策略（全部走 PubMed，免费且稳定，带 CORS）：
  1. 用 DOI 在 PubMed esearch 找到 PMID；
  2. 用 efetch (retmode=xml) 取 <AbstractText>；
  3. 若 PubMed 无摘要（如 JAAD 的 images/letter 类），再尝试 CrossRef 的 abstract 字段；
  4. 仍无则标记为 no_abstract，绝不编造。

输出：
  - 直接更新 papers.json（补齐 abstract / pmid 字段）；
  - 同时写出 backfill_report.json 方便检查覆盖率。
"""
import json
import os
import re
import time
import urllib.request
import urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
PAPERS = os.path.join(HERE, "papers.json")
REPORT = os.path.join(HERE, "backfill_report.json")

UA = {"User-Agent": "journal-digest/1.0 (mailto:example@example.com)"}


def http_get(url, timeout=25):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "ignore")


def pubmed_pmid_by_doi(doi):
    url = ("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed"
           "&retmode=json&term=" + urllib.parse.quote(doi + "[doi]"))
    try:
        data = json.loads(http_get(url))
        return data.get("esearchresult", {}).get("idlist", [])
    except Exception:
        return []


def pubmed_abstract(pmid):
    url = ("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed"
           "&rettype=xml&id=" + str(pmid))
    try:
        xml = http_get(url)
    except Exception:
        return None
    parts = re.findall(r"<AbstractText[^>]*>(.*?)</AbstractText>", xml, re.S)
    if not parts:
        return None
    txt = []
    for p in parts:
        p = re.sub(r"<[^>]+>", "", p)          # 去掉内部标签（如 <b>、<i>）
        p = re.sub(r"\s+", " ", p).strip()
        if p:
            txt.append(p)
    return " ".join(txt).strip() or None


def crossref_abstract(doi):
    url = "https://api.crossref.org/works/" + urllib.parse.quote(doi)
    try:
        data = json.loads(http_get(url, timeout=25))
        msg = data.get("message", {})
        ab = msg.get("abstract")
        if not ab:
            return None
        # Crossref abstract 是 JATS XML，提取文本
        ab = re.sub(r"<[^>]+>", "", ab)
        ab = re.sub(r"\s+", " ", ab).strip()
        return ab or None
    except Exception:
        return None


def main():
    papers = json.load(open(PAPERS, encoding="utf-8"))
    missing = [p for p in papers if not p.get("abstract")]
    print(f"共 {len(papers)} 篇，缺失英文摘要 {len(missing)} 篇")

    report = {"filled": [], "still_missing": []}
    filled_count = 0

    for i, p in enumerate(missing, 1):
        doi = p.get("doi", "")
        journal = p.get("journal", "")
        title = p.get("title", "")[:60]
        print(f"  [{i}/{len(missing)}] {journal}: {title}")

        abstract = None
        pmid = ""
        if doi:
            ids = pubmed_pmid_by_doi(doi)
            if ids:
                pmid = ids[0]
                abstract = pubmed_abstract(pmid)
            if not abstract:
                abstract = crossref_abstract(doi)

        if abstract:
            p["abstract"] = abstract
            if pmid:
                p["pmid"] = pmid
            filled_count += 1
            report["filled"].append({"journal": journal, "doi": doi, "pmid": pmid,
                                     "len": len(abstract)})
            print(f"      ✓ 已补回 ({len(abstract)} 字符)")
        else:
            report["still_missing"].append({"journal": journal, "doi": doi,
                                            "title": p.get("title", "")})
            print(f"      ✗ 无任何来源提供摘要（letter/image 类，已如实标注）")

        time.sleep(0.34)  # 轻微限速，尊重 NCBI 速率限制

    json.dump(papers, open(PAPERS, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    json.dump(report, open(REPORT, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    print(f"\n完成：成功补回 {filled_count}/{len(missing)} 篇英文摘要")
    print(f"仍缺失 {len(report['still_missing'])} 篇（多为 JAAD 的 images/letter 类，本身无摘要）")
    print(f"已写回 {PAPERS}")
    print(f"报告：{REPORT}")


if __name__ == "__main__":
    main()
