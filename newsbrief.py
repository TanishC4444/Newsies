"""
newsbrief.py - RSS scraper + local Mistral-7B NLP summaries in one file.

Usage:
    python newsbrief.py                                          # default BBC ME feed
    python newsbrief.py "https://feeds.bbci.co.uk/news/world/rss.xml"
    python newsbrief.py "https://some-feed.xml" --max 5 --no-long --no-nlp

Requires: feedparser, playwright, llama-cpp-python
"""

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timezone


# =============================================================================
# SITE-SPECIFIC CSS SELECTORS
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
    "reuters":          'article p, [class*="article-body"] p',
    "guardian":         'article p, .article-body-commercial-selector p',
    "politico":         'article p, .story-text p',
    "foreignpolicy":    'article p, .post-content-main p',
    "economist":        'article p, .article__body p',
}

FALLBACK_SELECTOR = "article p, main p, .content p, p"


def match_selector(url):
    url_lower = url.lower()
    for key, sel in SELECTORS.items():
        if key in url_lower:
            return sel
    return FALLBACK_SELECTOR


# =============================================================================
# JS SNIPPETS FOR PAGE EXTRACTION
# =============================================================================

EXTRACT_TEXT_JS = """
(selector) => {
    let els = document.querySelectorAll(selector);
    if (els.length > 0) {
        return Array.from(els)
            .map(el => el.innerText.trim())
            .filter(t => t.length > 20)
            .join('\\n\\n');
    }
    let allP = document.querySelectorAll('p');
    return Array.from(allP)
        .map(p => p.innerText.trim())
        .filter(t => t.length > 20)
        .join('\\n\\n');
}
"""

EXTRACT_META_JS = """
() => {
    const meta = (name) => {
        const el = document.querySelector(
            `meta[name="${name}"], meta[property="${name}"], meta[itemprop="${name}"]`
        );
        return el ? el.content || '' : '';
    };
    return {
        author: meta('author') || meta('article:author') || meta('og:author') || '',
        published: meta('article:published_time') || meta('datePublished')
                   || meta('pubdate') || meta('date') || '',
    };
}
"""

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


# =============================================================================
# SCRAPER
# =============================================================================

def scrape_feed(feed_url, source_name="", category="", max_articles=0,
                delay=0.5, verbose=False):
    """
    Parse RSS feed and scrape full article text from each entry.

    Returns list of dicts with keys:
        title, url, source, category, author, published, retrieved_at,
        word_count, char_count, full_text, error
    """
    import feedparser
    from playwright.sync_api import sync_playwright

    feed = feedparser.parse(feed_url)
    entries = feed.entries
    if max_articles > 0:
        entries = entries[:max_articles]

    if not entries:
        print("  No entries found in feed")
        return []

    articles = []

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(user_agent=UA)
        page = context.new_page()

        for i, entry in enumerate(entries, 1):
            title = entry.get("title", "Untitled")
            link = entry.get("link", "")
            if not link:
                continue

            rss_author = entry.get("author", "")
            rss_pub = entry.get("published", entry.get("updated", ""))

            if verbose:
                print(f"  [{i}/{len(entries)}] {title[:60]}...", end=" ", flush=True)

            art = {
                "title": title,
                "url": link,
                "source": source_name or feed_url,
                "category": category,
                "author": rss_author,
                "published": rss_pub,
                "retrieved_at": datetime.now(timezone.utc).isoformat(),
                "word_count": 0,
                "char_count": 0,
                "full_text": "",
                "error": None,
                "short_summary": None,
                "long_summary": None,
            }

            try:
                page.goto(link, timeout=20_000, wait_until="domcontentloaded")
                page.wait_for_timeout(3000)

                selector = match_selector(link)
                text = (page.evaluate(EXTRACT_TEXT_JS, selector) or "").strip()

                page_meta = page.evaluate(EXTRACT_META_JS) or {}
                if not art["author"]:
                    art["author"] = page_meta.get("author", "Unknown")
                if not art["published"]:
                    art["published"] = page_meta.get("published", "")

                art["full_text"] = text
                art["word_count"] = len(text.split())
                art["char_count"] = len(text)

                if art["word_count"] < 10:
                    art["error"] = "extraction_too_short"

                if verbose:
                    tag = "OK" if not art["error"] else "FAIL"
                    print(f"{tag} ({art['word_count']} words)")

            except Exception as exc:
                art["error"] = str(exc)
                if verbose:
                    print(f"ERROR: {exc}")

            articles.append(art)
            time.sleep(delay)

        context.close()
        browser.close()

    return articles


# =============================================================================
# NLP - MISTRAL 7B PROMPTS + INFERENCE
# =============================================================================

DEFAULT_MODEL_PATH = os.environ.get(
    "NEWSBRIEF_MODEL_PATH",
    "models/mistral-7b-instruct-v0.3.Q5_K_M.gguf",
)

# ---------------------------------------------------------------------------
# SHORT SUMMARY: 3 sentences, pure specifics
# ---------------------------------------------------------------------------
SHORT_PROMPT = """\
<s>[INST] You are a senior news analyst. You produce razor-sharp 3-sentence \
briefings used by policymakers. Every sentence must contain specifics: \
names, numbers, dates, places. Never be vague.

ARTICLE METADATA:
- Title: {title}
- Source: {source}
- Author: {author}
- Published: {published}
- Category: {category}

FULL ARTICLE TEXT:
{full_text}

TASK: Write exactly 3 sentences in a JSON object. Use ALL the context above.

Sentence 1 "headline_idea": State the core event/development from the headline. \
Include WHO did WHAT, with specific names and numbers.
Sentence 2 "importance": Explain WHY this matters RIGHT NOW. Reference specific \
policies, precedents, data points, or stakeholder positions from the article.
Sentence 3 "impact": State the concrete downstream effects, who is affected, \
and what happens next. Use numbers/stats from the article if available.

Respond with ONLY this JSON, no markdown fences, no extra text:
{{"headline_idea": "...", "importance": "...", "impact": "..."}}
[/INST]"""

# ---------------------------------------------------------------------------
# LONG SUMMARY: deep analytical, structured
# ---------------------------------------------------------------------------
LONG_PROMPT = """\
<s>[INST] You are an expert geopolitical and policy analyst writing deep-dive \
briefings. You are analytical, never vague, always cite specifics from the \
source material: names, titles, exact figures, dates, locations, and direct \
policy language. Your analysis connects cause to effect.

ARTICLE METADATA:
- Title: {title}
- Source: {source}
- Author: {author}
- Published: {published}
- Category: {category}

FULL ARTICLE TEXT:
{full_text}

TASK: Produce a structured analytical summary using ALL available context. \
Be exhaustive with names, numbers, dates, and causal reasoning. Write in \
full paragraphs (3-5 sentences each).

Return ONLY this JSON, no markdown fences:
{{
  "chronology": "Narrate the events in chronological order. Include exact dates, \
sequence of actions, and who initiated each step. Reference specific meetings, \
votes, announcements, or incidents mentioned in the article.",
  "who_what_when_where_why": "Identify every key actor by full name and title. \
State exactly what each actor did or said, when and where. Explain their stated \
and underlying motivations using evidence from the article.",
  "key_changes": "What has shifted or is new? Identify specific policy changes, \
numerical shifts (percentages, dollar amounts, troop counts, vote tallies), new \
agreements, or broken precedents. Compare before vs. after using the article data.",
  "continuities": "What remains unchanged or is a continuation of prior trends? \
Reference historical context, ongoing policies, or recurring patterns the article \
mentions or implies.",
  "significance": "Analyze the broader consequences. Who benefits, who loses, and \
by how much? What are the second-order effects? Connect to larger regional/global/sector \
trends. Use conditional reasoning: if X continues, then Y. Ground every claim in \
article evidence."
}}
[/INST]"""


def parse_json_safe(raw):
    """Best-effort JSON extraction from model output."""
    raw = re.sub(r"```json\s*", "", raw)
    raw = re.sub(r"```\s*$", "", raw)
    raw = raw.strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return {}


def truncate_text(text, n_ctx=8192, reserve_tokens=1500):
    """Truncate article to fit context window. ~4 chars per token."""
    max_chars = (n_ctx - reserve_tokens) * 4
    if len(text) > max_chars:
        return text[:max_chars] + "\n\n[...truncated to fit context...]"
    return text


def run_nlp(articles, model_path=DEFAULT_MODEL_PATH, n_ctx=8192,
            do_long=True, verbose=False):
    """Load Mistral 7B and run short + long summaries on all articles."""
    from llama_cpp import Llama

    if verbose:
        print(f"\nLoading model: {model_path}")

    llm = Llama(
        model_path=model_path,
        n_ctx=n_ctx,
        n_threads=os.cpu_count() or 4,
        n_gpu_layers=0,       # CPU only for GitHub Actions
        verbose=False,
    )

    def generate(prompt, max_tokens=1200):
        result = llm(
            prompt,
            max_tokens=max_tokens,
            temperature=0.15,
            top_p=0.9,
            repeat_penalty=1.15,
            stop=["</s>", "[INST]"],
        )
        return result["choices"][0]["text"].strip()

    for i, art in enumerate(articles, 1):
        if art["error"] or not art["full_text"]:
            continue

        if verbose:
            print(f"  [NLP {i}/{len(articles)}] {art['title'][:55]}...")

        m = art
        text_short = truncate_text(m["full_text"], n_ctx, 1500)
        text_long = truncate_text(m["full_text"], n_ctx, 2000)

        # --- short summary ---
        prompt = SHORT_PROMPT.format(
            title=m["title"], source=m["source"], author=m["author"],
            published=m["published"], category=m["category"],
            full_text=text_short,
        )
        raw = generate(prompt, max_tokens=500)
        art["short_summary"] = parse_json_safe(raw)
        art["short_summary"]["_raw"] = raw

        # --- long summary ---
        if do_long:
            prompt = LONG_PROMPT.format(
                title=m["title"], source=m["source"], author=m["author"],
                published=m["published"], category=m["category"],
                full_text=text_long,
            )
            raw = generate(prompt, max_tokens=1200)
            art["long_summary"] = parse_json_safe(raw)
            art["long_summary"]["_raw"] = raw

    return articles


# =============================================================================
# OUTPUT
# =============================================================================

def write_json(articles, path):
    data = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "article_count": len(articles),
        "articles": articles,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def write_text(articles, path):
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [f"NEWSBRIEF REPORT  {ts}", f"{'='*90}\n"]

    for i, art in enumerate(articles, 1):
        lines.append(f"{'~'*90}")
        lines.append(f"[{i}] {art['title']}")
        lines.append(f"    Source:    {art['source']} ({art['category']})")
        lines.append(f"    Author:   {art['author']}")
        lines.append(f"    Date:     {art['published']}")
        lines.append(f"    URL:      {art['url']}")
        lines.append(f"    Words:    {art['word_count']:,}")

        if art["error"]:
            lines.append(f"    ERROR:    {art['error']}")

        ss = art.get("short_summary")
        if ss:
            lines.append(f"\n    --- SHORT SUMMARY ---")
            lines.append(f"    {ss.get('headline_idea', '')}")
            lines.append(f"    {ss.get('importance', '')}")
            lines.append(f"    {ss.get('impact', '')}")

        ls = art.get("long_summary")
        if ls:
            lines.append(f"\n    --- LONG SUMMARY ---")
            for label, key in [
                ("CHRONOLOGY", "chronology"),
                ("WHO/WHAT/WHEN/WHERE/WHY", "who_what_when_where_why"),
                ("KEY CHANGES", "key_changes"),
                ("CONTINUITIES", "continuities"),
                ("SIGNIFICANCE", "significance"),
            ]:
                val = ls.get(key, "")
                if val:
                    lines.append(f"\n    [{label}]")
                    lines.append(f"    {val}")

        lines.append("")

    ok = sum(1 for a in articles if not a["error"])
    fail = sum(1 for a in articles if a["error"])
    lines.append(f"{'='*90}")
    lines.append(f"TOTAL: {len(articles)} articles | {ok} OK | {fail} failed")
    lines.append(f"{'='*90}")

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="RSS scraper + Mistral-7B NLP")
    parser.add_argument("feed_url", nargs="?",
                        default="https://feeds.bbci.co.uk/news/world/middle_east/rss.xml",
                        help="RSS feed URL")
    parser.add_argument("--max", "-m", type=int, default=0,
                        help="Max articles (0 = all)")
    parser.add_argument("--model", type=str, default=DEFAULT_MODEL_PATH,
                        help="Path to GGUF model")
    parser.add_argument("--ctx", type=int, default=8192,
                        help="Context window tokens")
    parser.add_argument("--no-long", action="store_true",
                        help="Skip long summaries")
    parser.add_argument("--no-nlp", action="store_true",
                        help="Scrape only, no NLP")
    parser.add_argument("--source", "-s", type=str, default="",
                        help="Source label")
    parser.add_argument("--category", "-c", type=str, default="General",
                        help="Category label")
    parser.add_argument("--json", "-j", type=str, default="",
                        help="JSON output path")
    parser.add_argument("--text", "-t", type=str, default="",
                        help="Text output path")
    parser.add_argument("--verbose", "-v", action="store_true")

    args = parser.parse_args()

    # ── SCRAPE ───────────────────────────────────────────────────────────
    print(f"Scraping: {args.feed_url}")
    articles = scrape_feed(
        feed_url=args.feed_url,
        source_name=args.source or args.feed_url,
        category=args.category,
        max_articles=args.max,
        verbose=args.verbose,
    )
    print(f"Scraped {len(articles)} articles")

    # ── NLP ──────────────────────────────────────────────────────────────
    if not args.no_nlp:
        run_nlp(
            articles,
            model_path=args.model,
            n_ctx=args.ctx,
            do_long=not args.no_long,
            verbose=args.verbose,
        )
        print("NLP complete")

    # ── OUTPUT ───────────────────────────────────────────────────────────
    ts = datetime.now().strftime("%Y-%m-%d_%H%M%S")

    json_path = args.json or f"newsbrief_{ts}.json"
    write_json(articles, json_path)
    print(f"JSON: {json_path}")

    text_path = args.text or f"newsbrief_{ts}.txt"
    write_text(articles, text_path)
    print(f"Text: {text_path}")

    print("Done.")


if __name__ == "__main__":
    main()