import feedparser
from playwright.sync_api import sync_playwright
from newspaper import Article
import time

BBC_FEED = "http://feeds.bbci.co.uk/news/rss.xml"


def extract_bbc_playwright(url):
    """Use Playwright to render BBC page, then extract article text from content blocks."""
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.goto(url, timeout=15000)
            page.wait_for_timeout(3000)

            # Try targeted selectors first (BBC-specific)
            text = page.evaluate("""
                (() => {
                    // BBC article text blocks
                    let paragraphs = document.querySelectorAll(
                        'article p, [data-component="text-block"] p'
                    );
                    if (paragraphs.length > 0) {
                        return Array.from(paragraphs).map(p => p.innerText.trim()).filter(t => t).join('\\n\\n');
                    }
                    // Fallback: just grab all visible text from body
                    return document.body.innerText;
                })()
            """)

            browser.close()
        return text.strip()
    except Exception as e:
        return f"[PLAYWRIGHT ERROR] {e}"


def extract_newspaper(url):
    """Standard newspaper4k extraction."""
    try:
        article = Article(url, language="en")
        article.download()
        article.parse()
        return article.text.strip()
    except Exception as e:
        return f"[NEWSPAPER ERROR] {e}"


def main():
    print("Fetching BBC RSS feed...")
    feed = feedparser.parse(BBC_FEED)
    entries = [(e.get("title", "?"), e.get("link", "")) for e in feed.entries[:5]]

    print(f"Found {len(entries)} articles (showing first 5)\n")

    for i, (title, link) in enumerate(entries, 1):
        if not link:
            continue

        print(f"{'='*80}")
        print(f"[{i}] {title}")
        print(f"    {link}")
        print(f"{'='*80}")

        # --- newspaper4k attempt ---
        np_text = extract_newspaper(link)
        np_words = len(np_text.split())
        print(f"\n  NEWSPAPER4K ({np_words} words):")
        if np_words < 20:
            print(f"    [POOR RESULT] Only got: {np_text[:200]}")
        else:
            print(f"    {np_text[:500]}...")

        # --- playwright attempt ---
        pw_text = extract_bbc_playwright(link)
        pw_words = len(pw_text.split())
        print(f"\n  PLAYWRIGHT ({pw_words} words):")
        if pw_words < 20:
            print(f"    [POOR RESULT] Only got: {pw_text[:200]}")
        else:
            print(f"    {pw_text[:500]}...")

        print()
        time.sleep(1)


if __name__ == "__main__":
    main()