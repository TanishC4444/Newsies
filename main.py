import feedparser
from playwright.sync_api import sync_playwright
import time
from datetime import datetime

# =============================================================================
# RSS FEEDS ORGANIZED BY CATEGORY
# =============================================================================

FEEDS = {

    # ── US NEWS ──────────────────────────────────────────────────────────────
    "US News": {
        "NPR US":                   "https://feeds.npr.org/1003/rss.xml",
        "ABC US Headlines":         "https://feeds.abcnews.com/abcnews/usheadlines",
        "CBS US":                   "https://www.cbsnews.com/latest/rss/us",
        "CNN US":                   "http://rss.cnn.com/rss/cnn_us.rss",
        "PBS NewsHour":             "https://www.pbs.org/newshour/feeds/rss/headlines",
        "NBC News US":              "https://feeds.nbcnews.com/nbcnews/public/news",
        "AP Top News":              "https://rsshub.app/apnews/topics/apf-topnews",
    },

    # ── US POLITICS ──────────────────────────────────────────────────────────
    "US Politics": {
        "NPR Politics":             "https://feeds.npr.org/1014/rss.xml",
        "ABC Politics":             "https://feeds.abcnews.com/abcnews/politicsheadlines",
        "CNBC Politics":            "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10000113",
        "CNN Politics":             "http://rss.cnn.com/rss/cnn_allpolitics.rss",
        "The Hill":                 "https://thehill.com/feed/",
    },

    # ── TEXAS & LOCAL ────────────────────────────────────────────────────────
    "Texas & Local": {
        "Texas Tribune":            "https://feeds.texastribune.org/feeds/main/",
        "Dallas Morning News":      "https://www.dallasnews.com/arcio/rss/",
        "Houston Chronicle":        "https://www.houstonchronicle.com/rss/feed/Houston-Texas-News-702.php",
    },

    # ── WORLD / GLOBAL ───────────────────────────────────────────────────────
    "World": {
        "BBC World":                "http://feeds.bbci.co.uk/news/world/rss.xml",
        "NPR World":                "https://feeds.npr.org/1004/rss.xml",
        "ABC Intl Headlines":       "https://feeds.abcnews.com/abcnews/internationalheadlines",
        "Al Jazeera":               "https://www.aljazeera.com/xml/rss/all.xml",
        "France 24":                "https://www.france24.com/en/rss",
        "CNN World":                "http://rss.cnn.com/rss/cnn_world.rss",
    },

    # ── EUROPE ───────────────────────────────────────────────────────────────
    "Europe": {
        "BBC Europe":               "https://feeds.bbci.co.uk/news/world/europe/rss.xml",
        "NPR Europe":               "https://feeds.npr.org/1124/rss.xml",
        "CNBC EU News":             "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=19794221",
        "DW News":                  "https://rss.dw.com/rdf/rss-en-all",
    },

    # ── ASIA & PACIFIC ───────────────────────────────────────────────────────
    "Asia & Pacific": {
        "BBC Asia":                 "https://feeds.bbci.co.uk/news/world/asia/rss.xml",
        "CNBC Asia News":           "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=19832390",
        "NPR Asia":                 "https://feeds.npr.org/1125/rss.xml",
    },

    # ── MIDDLE EAST ──────────────────────────────────────────────────────────
    "Middle East": {
        "BBC Middle East":          "https://feeds.bbci.co.uk/news/world/middle_east/rss.xml",
        "NPR Middle East":          "https://feeds.npr.org/1009/rss.xml",
    },

    # ── AFRICA ───────────────────────────────────────────────────────────────
    "Africa": {
        "BBC Africa":               "https://feeds.bbci.co.uk/news/world/africa/rss.xml",
        "NPR Africa":               "https://feeds.npr.org/1126/rss.xml",
    },

    # ── LATIN AMERICA ────────────────────────────────────────────────────────
    "Latin America": {
        "BBC Latin America":        "https://feeds.bbci.co.uk/news/world/latin_america/rss.xml",
        "NPR Latin America":        "https://feeds.npr.org/1127/rss.xml",
    },

    # ── HEALTH & SCIENCE ─────────────────────────────────────────────────────
    "Health & Science": {
        "BBC Health":               "https://feeds.bbci.co.uk/news/health/rss.xml",
        "BBC Science & Environment":"https://feeds.bbci.co.uk/news/science_and_environment/rss.xml",
        "NPR Health":               "https://feeds.npr.org/1128/rss.xml",
        "NPR Science":              "https://feeds.npr.org/1007/rss.xml",
        "ABC Health":               "https://feeds.abcnews.com/abcnews/healthheadlines",
        "CNBC Health":              "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10000108",
        "ScienceDaily Top":         "https://www.sciencedaily.com/rss/top.xml",
        "ScienceDaily Health":      "https://www.sciencedaily.com/rss/health_medicine.xml",
        "New Scientist":            "https://www.newscientist.com/section/news/feed/",
    },

    # ── TECHNOLOGY ───────────────────────────────────────────────────────────
    "Technology": {
        "BBC Technology":           "https://feeds.bbci.co.uk/news/technology/rss.xml",
        "NPR Technology":           "https://feeds.npr.org/1019/rss.xml",
        "ABC Tech":                 "https://feeds.abcnews.com/abcnews/technologyheadlines",
        "CNBC Tech":                "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=19854910",
        "Ars Technica":             "https://feeds.arstechnica.com/arstechnica/index",
        "The Verge":                "https://www.theverge.com/rss/index.xml",
        "Wired":                    "https://www.wired.com/feed/rss",
        "TechCrunch":               "https://techcrunch.com/feed/",
    },

    # ── BUSINESS & ECONOMY ───────────────────────────────────────────────────
    "Business & Economy": {
        "NPR Business":             "https://feeds.npr.org/1006/rss.xml",
        "NPR Economy":              "https://feeds.npr.org/1017/rss.xml",
        "ABC Business":             "https://feeds.abcnews.com/abcnews/businessheadlines",
        "BBC Business":             "https://feeds.bbci.co.uk/news/business/rss.xml",
        "CNBC Top News":            "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100003114",
        "CNBC Business":            "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10001147",
        "CNBC Economy":             "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=20910258",
        "CNN Money":                "http://rss.cnn.com/rss/money_latest.rss",
    },

    # ── ENTERTAINMENT & CULTURE ──────────────────────────────────────────────
    "Entertainment & Culture": {
        "BBC Entertainment":        "https://feeds.bbci.co.uk/news/entertainment_and_arts/rss.xml",
        "ABC Entertainment":        "https://feeds.abcnews.com/abcnews/entertainmentheadlines",
        "NPR Arts":                 "https://feeds.npr.org/1008/rss.xml",
    },
}


# =============================================================================
# SITE-SPECIFIC CSS SELECTORS FOR ARTICLE BODY
# =============================================================================

SELECTORS = {
    "bbc":              'article p, [data-component="text-block"] p',
    "npr":              'article p, .storytext p, #storytext p',
    "cnn":              'article p, .article__content p, .zn-body__paragraph',
    "pbs":              'article p, .body-text p',
    "abcnews":          'article p, .Article__Content p, [data-testid="prism-article-body"] p',
    "cbsnews":          'article p, .content__body p',
    "nbcnews":          'article p, .article-body__content p',
    "cnbc":             'article p, .ArticleBody-articleBody p, .RenderKeyPoints-list li',
    "thehill":          'article p, .field-items p',
    "texastribune":     'article p, .article-body p, .story-body p',
    "dallasnews":       'article p, .body-copy p',
    "houstonchronicle": 'article p',
    "aljazeera":        'article p, .wysiwyg p',
    "france24":         'article p, .t-content__body p',
    "dw.com":           'article p, .longText p',
    "sciencedaily":     'article p, #text p, .lead, #first p',
    "newscientist":     'article p, .article-body p',
    "arstechnica":      'article p, .article-content p',
    "theverge":         'article p, .duet--article--article-body-component p',
    "wired":            'article p, .body__inner-container p',
    "techcrunch":       'article p, .article-content p',
    "apnews":           'article p, .RichTextStoryBody p',
    "nytimes":          'article p, section[name="articleBody"] p',
    "washingtonpost":   'article p, .article-body p',
}


def match_selector(url):
    """Pick the best CSS selector based on the article URL."""
    url_lower = url.lower()
    for key, selector in SELECTORS.items():
        if key in url_lower:
            return selector
    return "article p, main p, .content p, p"


def extract_article(page, url):
    """Navigate to URL and extract article text using targeted selectors."""
    try:
        page.goto(url, timeout=20000, wait_until="domcontentloaded")
        page.wait_for_timeout(3000)

        selector = match_selector(url)

        text = page.evaluate("""
            (selector) => {
                let els = document.querySelectorAll(selector);
                if (els.length > 0) {
                    return Array.from(els)
                        .map(el => el.innerText.trim())
                        .filter(t => t.length > 20)
                        .join('\\n\\n');
                }
                // fallback: grab all paragraph text
                let allP = document.querySelectorAll('p');
                return Array.from(allP)
                    .map(p => p.innerText.trim())
                    .filter(t => t.length > 20)
                    .join('\\n\\n');
            }
        """, selector)

        return text.strip() if text else "[EMPTY] No text extracted"
    except Exception as e:
        return f"[ERROR] {e}"


def main():
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    output_file = f"news_{timestamp}.txt"

    total_articles = 0
    total_words = 0
    failed = 0

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(f"NEWS SCRAPE - {timestamp}\n")
            f.write(f"{'='*100}\n\n")

            for category, feeds in FEEDS.items():

                f.write(f"\n{'#'*100}\n")
                f.write(f"# CATEGORY: {category.upper()}\n")
                f.write(f"{'#'*100}\n\n")

                print(f"\n{'='*60}")
                print(f"CATEGORY: {category}")
                print(f"{'='*60}")

                for feed_name, feed_url in feeds.items():
                    print(f"\n  [FEED] {feed_name}...")
                    feed = feedparser.parse(feed_url)

                    if not feed.entries:
                        print(f"    SKIPPED - no entries found")
                        continue

                    entries = [
                        (e.get("title", "?"), e.get("link", ""))
                        for e in feed.entries
                    ]
                    print(f"    Found {len(entries)} articles")

                    f.write(f"\n{'- '*40}\n")
                    f.write(f"SOURCE:   {feed_name}\n")
                    f.write(f"CATEGORY: {category}\n")
                    f.write(f"FEED:     {feed_url}\n")
                    f.write(f"COUNT:    {len(entries)} articles\n")
                    f.write(f"{'- '*40}\n\n")

                    for i, (title, link) in enumerate(entries, 1):
                        if not link:
                            continue

                        print(f"    [{i}/{len(entries)}] {title[:55]}...",
                              end=" ", flush=True)

                        text = extract_article(page, link)
                        word_count = len(text.split())
                        char_count = len(text)

                        if word_count < 10 or text.startswith("["):
                            print(f"FAIL ({word_count} words)")
                            failed += 1
                        else:
                            print(f"OK ({word_count} words)")

                        f.write(f"{'~'*80}\n")
                        f.write(f"TITLE:    {title}\n")
                        f.write(f"SOURCE:   {feed_name}\n")
                        f.write(f"CATEGORY: {category}\n")
                        f.write(f"URL:      {link}\n")
                        f.write(f"LENGTH:   {char_count:,} chars | "
                                f"{word_count:,} words\n")
                        f.write(f"{'~'*80}\n\n")
                        f.write(text)
                        f.write(f"\n\n")

                        total_articles += 1
                        total_words += word_count

                        time.sleep(0.5)

            # summary
            f.write(f"\n{'='*100}\n")
            f.write(f"SUMMARY\n")
            f.write(f"  Total articles:  {total_articles}\n")
            f.write(f"  Total words:     {total_words:,}\n")
            f.write(f"  Failed:          {failed}\n")
            f.write(f"  Categories:      {len(FEEDS)}\n")
            f.write(f"  Feed sources:    "
                    f"{sum(len(v) for v in FEEDS.values())}\n")
            f.write(f"  Timestamp:       {timestamp}\n")
            f.write(f"{'='*100}\n")

        browser.close()

    print(f"\n{'='*60}")
    print(f"DONE!")
    print(f"  Articles:   {total_articles}")
    print(f"  Words:      {total_words:,}")
    print(f"  Failed:     {failed}")
    print(f"  Categories: {len(FEEDS)}")
    print(f"  Feeds:      {sum(len(v) for v in FEEDS.values())}")
    print(f"  Saved to:   {output_file}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()