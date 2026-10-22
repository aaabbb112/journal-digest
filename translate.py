#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
translate.py — 调用通义千问（阿里云 DashScope，OpenAI 兼容接口）对论文做翻译与总结。

对每篇论文，一次调用返回 4 个字段：
  title_zh    题目中文翻译
  abstract_zh 摘要中文翻译（忠实原文）
  summary_zh  中文摘要总结（用自己的话精简重述核心发现）
  highlight   关键突破（一句话概括本文的新突破或意义）

若未配置 API Key（或 Key 仍是占位符），则 zh 字段留空，仍生成 papers.json，方便先看结构。
输入：papers_raw.json  输出：papers.json
"""
import json
import os
import time
import urllib.request

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
RAW_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "papers_raw.json")
OUT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "papers.json")


def load_config():
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return json.load(f)


PROMPT_TMPL = """你是文献翻译与总结助手。请处理以下英文学术论文信息。

英文题目:
{title}

英文摘要:
{abstract}

请严格只输出一个 JSON 对象，包含四个字段：
- "title_zh": 题目的中文翻译
- "abstract_zh": 摘要的中文翻译（忠实原文，不要增删结论）
- "summary_zh": 中文摘要总结（用你自己的话精简重述本文核心发现，区别于逐字翻译，2-4 句）
- "highlight": 关键突破（一句话概括本文实现了什么新的突破或意义）

仅输出 JSON，不要任何额外文字或代码块标记。"""


def call_tongyi(api_key, base_url, model, title, abstract):
    if not api_key or api_key.startswith("${"):
        return None
    prompt = PROMPT_TMPL.format(title=title or "(无题目)", abstract=abstract or "(无摘要)")
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "response_format": {"type": "json_object"},
        "temperature": 0.3,
    }
    req = urllib.request.Request(
        base_url.rstrip("/") + "/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            resp = json.load(r)
        content = resp["choices"][0]["message"]["content"]
        return json.loads(content)
    except Exception as ex:
        print(f"  ! 翻译调用失败: {ex}")
        return None


def main():
    cfg = load_config()
    llm = cfg.get("llm", {})
    api_key = os.environ.get("TONGYI_API_KEY", llm.get("api_key", ""))
    base_url = llm.get("base_url", "https://dashscope.aliyuncs.com/compatible-mode/v1")
    model = llm.get("model", "qwen-plus")

    papers = json.load(open(RAW_PATH, encoding="utf-8"))
    print(f"待翻译 {len(papers)} 篇，模型={model}，Key={'已配置' if (api_key and not api_key.startswith('${')) else '未配置(留空)'}")

    out = []
    for i, p in enumerate(papers, 1):
        print(f"  [{i}/{len(papers)}] {p['journal']}: {p['title'][:50]}")
        res = call_tongyi(api_key, base_url, model, p["title"], p["abstract"])
        if res:
            p.update({
                "title_zh": res.get("title_zh", "") or "",
                "abstract_zh": res.get("abstract_zh", "") or "",
                "summary_zh": res.get("summary_zh", "") or "",
                "highlight": res.get("highlight", "") or "",
            })
        else:
            p.setdefault("title_zh", "")
            p.setdefault("abstract_zh", "")
            p.setdefault("summary_zh", "")
            p.setdefault("highlight", "")
        out.append(p)
        time.sleep(0.25)  # 轻微限速，避免触发限流

    json.dump(out, open(OUT_PATH, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"\n已保存 -> {OUT_PATH}")


if __name__ == "__main__":
    main()
