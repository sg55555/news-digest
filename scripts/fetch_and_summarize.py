#!/usr/bin/env python3
"""
毎朝ニュースダイジェスト生成スクリプト
RSS取得 → Claude APIでフィルタリング・要約・深掘り分析 → news.json 生成
"""

import feedparser
import anthropic
import json
import os
import sys
from datetime import datetime
import email.utils
import pytz

JST = pytz.timezone("Asia/Tokyo")

RSS_FEEDS = [
    # NHK
    {"url": "https://www3.nhk.or.jp/rss/news/cat0.xml",  "source": "NHK",     "label": "NHK主要"},
    {"url": "https://www3.nhk.or.jp/rss/news/cat4.xml",  "source": "NHK",     "label": "NHK経済"},
    {"url": "https://www3.nhk.or.jp/rss/news/cat3.xml",  "source": "NHK",     "label": "NHK政治"},
    {"url": "https://www3.nhk.or.jp/rss/news/cat5.xml",  "source": "NHK",     "label": "NHK国際"},
    # Reuters Japan
    {"url": "https://feeds.reuters.com/reuters/JPTopNews",      "source": "Reuters", "label": "Reuters Top"},
    {"url": "https://feeds.reuters.com/reuters/JPBusinessNews", "source": "Reuters", "label": "Reuters Business"},
    {"url": "https://feeds.reuters.com/reuters/JPTechNews",     "source": "Reuters", "label": "Reuters Tech"},
    # 日経（見出し + リードのみ）
    {"url": "https://www.nikkei.com/rss/",                "source": "Nikkei",  "label": "日経"},
    {"url": "https://www.nikkei.com/news/rss/",           "source": "Nikkei",  "label": "日経2"},
    # Yahoo! Japan ニュース (フォールバック)
    {"url": "https://news.yahoo.co.jp/rss/categories/top-picks.xml",  "source": "Yahoo", "label": "Yahoo Top"},
    {"url": "https://news.yahoo.co.jp/rss/categories/business.xml",   "source": "Yahoo", "label": "Yahoo Business"},
    {"url": "https://news.yahoo.co.jp/rss/categories/it.xml",         "source": "Yahoo", "label": "Yahoo IT"},
]

MAX_PER_FEED = 12
TARGET = 10


def fetch_rss(feed):
    try:
        d = feedparser.parse(feed["url"])
        if d.bozo and not d.entries:
            print(f"  SKIP {feed['label']}: parse error")
            return []
        articles = []
        for e in d.entries[:MAX_PER_FEED]:
            articles.append({
                "title":       e.get("title", "").strip(),
                "description": e.get("summary", e.get("description", ""))[:400].strip(),
                "url":         e.get("link", ""),
                "published":   e.get("published", ""),
                "source":      feed["source"],
            })
        print(f"  {feed['label']}: {len(articles)} 件")
        return articles
    except Exception as ex:
        print(f"  ERROR {feed['label']}: {ex}")
        return []


def deduplicate(articles):
    seen, out = set(), []
    for a in articles:
        key = a["title"][:40]
        if key and key not in seen:
            seen.add(key)
            out.append(a)
    return out


def score_and_select(client, articles):
    lines = []
    for i, a in enumerate(articles):
        lines.append(f"[{i}] ({a['source']}) {a['title']}")
        if a["description"]:
            lines.append(f"    {a['description'][:200]}")
    prompt = (
        "以下のニュース記事一覧を読み、テクノロジー・政治・経済・国際ニュースを\n"
        "高スコア（7〜10）、芸能・スポーツ・地方軽微ニュースを低スコア（0〜3）として\n"
        f"スコアリングし、上位{TARGET}件のインデックスをスコア降順で返してください。\n\n"
        + "\n".join(lines)
        + f"\n\n以下のJSONのみを返してください:\n{{\"selected\": [インデックスのリスト（上位{TARGET}件）]}}"
    )
    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=400,
        messages=[{"role": "user", "content": prompt}],
    )
    text = resp.content[0].text.strip()
    if "```" in text:
        text = text.split("```")[1].lstrip("json").strip()
    try:
        result = json.loads(text)
        indices = result["selected"][:TARGET]
        return [articles[i] for i in indices if i < len(articles)]
    except Exception as ex:
        print(f"  スコアリングパースエラー: {ex}")
        return articles[:TARGET]


def summarize(client, articles):
    items = []
    for i, a in enumerate(articles):
        items.append(
            f"[{i}] ソース:{a['source']}\nタイトル:{a['title']}\n"
            f"内容:{a['description'][:500]}"
        )
    prompt = (
        "以下のニュース記事それぞれについて、日本語で要約と解説を生成してください。\n\n"
        + "\n\n".join(items)
        + """

各記事について次のJSONを返してください（配列）:
{
  "articles": [
    {
      "index": 0,
      "category": "経済|テック|政治|国際|社会 のどれか",
      "summary": "専門用語を噛み砕いた200字程度の要約。背景・意味も説明する。",
      "key_points": ["重要ポイント1", "重要ポイント2", "重要ポイント3"],
      "importance": 1〜10の整数
    }
  ]
}

JSONのみを返してください。"""
    )
    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )
    text = resp.content[0].text.strip()
    if "```" in text:
        text = text.split("```")[1].lstrip("json").strip()
    try:
        return json.loads(text)["articles"]
    except Exception as ex:
        print(f"  要約パースエラー: {ex}")
        return []


def deep_analyze(client, articles):
    """選定された記事の深掘り分析を生成"""
    items = []
    for i, a in enumerate(articles):
        items.append(
            f"[{i}] ソース:{a['source']}\nタイトル:{a['title']}\n"
            f"内容:{a['description'][:500]}"
        )
    prompt = (
        "以下のニュース記事それぞれについて、日本語で詳細な深掘り分析を生成してください。\n\n"
        + "\n\n".join(items)
        + """

各記事について次のJSONを返してください（配列）:
{
  "articles": [
    {
      "index": 0,
      "context": "この出来事の背景・歴史的文脈。なぜこれが起きたか、どのような経緯があるか、関係する国・組織・人物の役割を具体的に説明する。300〜400字。",
      "terms": [
        { "word": "用語名", "explanation": "一般読者向けの分かりやすい解説。専門知識がなくても理解できるように。60〜100字。" }
      ],
      "insights": "この記事を通じて得られる知見・示唆。業界・社会への影響、今後起こりうることの展望、読者が持つべき視点を含む。300〜400字。",
      "related_topics": ["関連トピック1", "関連トピック2", "関連トピック3"]
    }
  ]
}

termsは記事に登場する専門用語・重要な固有名詞・概念を2〜4個選んで解説してください。
JSONのみを返してください。"""
    )
    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=8192,
        messages=[{"role": "user", "content": prompt}],
    )
    text = resp.content[0].text.strip()
    if "```" in text:
        text = text.split("```")[1].lstrip("json").strip()
    try:
        return json.loads(text)["articles"]
    except Exception as ex:
        print(f"  深掘り分析パースエラー: {ex}")
        return []


def parse_date(s):
    if not s:
        return datetime.now(JST).isoformat()
    try:
        dt = email.utils.parsedate_to_datetime(s)
        return dt.astimezone(JST).isoformat()
    except Exception:
        return datetime.now(JST).isoformat()


def main():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: ANTHROPIC_API_KEY が設定されていません")
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)
    now = datetime.now(JST)

    print("=== Morning Brief 生成開始 ===")
    print(f"日時: {now.strftime('%Y-%m-%d %H:%M JST')}\n")

    print("[1/4] RSSフィード取得中...")
    all_articles = []
    for feed in RSS_FEEDS:
        all_articles.extend(fetch_rss(feed))
    all_articles = deduplicate(all_articles)
    print(f"  重複除去後: {len(all_articles)} 件\n")

    if not all_articles:
        print("ERROR: 記事を取得できませんでした")
        sys.exit(1)

    print("[2/4] Claude API でスコアリング中...")
    selected = score_and_select(client, all_articles)
    print(f"  選定: {len(selected)} 件\n")

    print("[3/4] Claude API で要約生成中...")
    summaries = summarize(client, selected)

    print("[4/4] Claude API で深掘り分析生成中...")
    deep_analyses = deep_analyze(client, selected)

    output_articles = []
    for i, article in enumerate(selected):
        meta  = next((s for s in summaries      if s.get("index") == i), {})
        deep  = next((d for d in deep_analyses  if d.get("index") == i), {})
        output_articles.append({
            "id":          i + 1,
            "title":       article["title"],
            "source":      article["source"],
            "category":    meta.get("category", "社会"),
            "url":         article["url"],
            "published":   parse_date(article.get("published", "")),
            "summary":     meta.get("summary", ""),
            "key_points":  meta.get("key_points", []),
            "importance":  meta.get("importance", 5),
            "deep_analysis": {
                "context":        deep.get("context", ""),
                "terms":          deep.get("terms", []),
                "insights":       deep.get("insights", ""),
                "related_topics": deep.get("related_topics", []),
            },
        })

    output = {
        "generated_at": now.isoformat(),
        "date_label":   now.strftime("%-m月%-d日"),
        "articles":     output_articles,
    }

    out_path = os.path.join(os.path.dirname(__file__), "../public/news.json")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n✅ news.json 更新完了 — {len(output_articles)} 記事")


if __name__ == "__main__":
    main()
