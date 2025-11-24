import feedparser


def get_news_with_article(query="AI", max_results=1):
    """
    現在は ResearchAgent のツールとしては提供しない補助関数。

    【利用想定】
    - 「最新ニュース教えて」「最近のトレンドは？」など、
      ニュース具体テーマが曖昧な一般的な依頼が来た時に、
      ResearchAgent が news_search や WebSearch を呼ぶ前の
      “導入トピック作成” に使用することを想定。
    - Google News RSS からタイトル・概要リンクを軽量取得し、
      「最近だと ○○ の話題が出ていますよ」などの
      会話のフックとして役立てる。

    ※ 将来的に ResearchAgent のプレプロンプト処理に統合予定。
    """
    feed = feedparser.parse(
        f"https://news.google.com/rss/search?q={query}&hl=ja&gl=JP&ceid=JP:ja"
    )

    results = []
    for entry in feed.entries[:max_results]:
        results.append(
            {
                "rss_title": entry.title,
                "rss_published": entry.published,
                "rss_link": entry.link,
            }
        )

    return results
