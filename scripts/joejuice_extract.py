from playwright.sync_api import sync_playwright
import json

def extract_all_text(url):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        page = context.new_page()
        page.goto(url, wait_until='networkidle', timeout=60000)

        # Dismiss any cookie/consent banners
        try:
            page.click('button:has-text("Accept")', timeout=3000)
        except:
            pass
        try:
            page.click('button:has-text("accept")', timeout=2000)
        except:
            pass
        try:
            page.click('[id*="cookie"] button', timeout=2000)
        except:
            pass
        try:
            page.click('[class*="cookie"] button', timeout=2000)
        except:
            pass

        page.wait_for_timeout(2000)

        # Full page screenshot
        page.screenshot(
            path='/Users/moons/dev/theacaiclub/web/screenshots/joejuice_fullpage.png',
            full_page=True
        )
        print("Full-page screenshot saved.")

        # Also above-the-fold
        page.screenshot(
            path='/Users/moons/dev/theacaiclub/web/screenshots/joejuice_atf.png',
            full_page=False
        )

        # Extract structured text
        result = page.evaluate("""() => {
            function getTextContent(el) {
                return (el.innerText || el.textContent || '').trim();
            }

            function cleanText(t) {
                return t.replace(/\\s+/g, ' ').trim();
            }

            const data = {
                title: document.title,
                nav: [],
                hero: {},
                sections: [],
                buttons: [],
                stats: [],
                all_headings: [],
                all_paragraphs: [],
                all_links: [],
                raw_body_text: []
            };

            // Nav links
            document.querySelectorAll('nav a, header a').forEach(a => {
                const t = cleanText(getTextContent(a));
                if (t) data.nav.push(t);
            });

            // All headings
            document.querySelectorAll('h1, h2, h3, h4, h5, h6').forEach(h => {
                const t = cleanText(getTextContent(h));
                if (t) data.all_headings.push({ tag: h.tagName, text: t });
            });

            // All paragraphs
            document.querySelectorAll('p').forEach(p => {
                const t = cleanText(getTextContent(p));
                if (t && t.length > 2) data.all_paragraphs.push(t);
            });

            // All buttons
            document.querySelectorAll('button, [role="button"], a.btn, a[class*="button"], a[class*="btn"]').forEach(b => {
                const t = cleanText(getTextContent(b));
                if (t && t.length > 0 && t.length < 100) data.buttons.push(t);
            });

            // All links text
            document.querySelectorAll('a').forEach(a => {
                const t = cleanText(getTextContent(a));
                if (t && t.length > 1 && t.length < 80) data.all_links.push(t);
            });

            // Stats: look for numbers in big text
            document.querySelectorAll('[class*="stat"], [class*="number"], [class*="count"], [class*="metric"]').forEach(el => {
                const t = cleanText(getTextContent(el));
                if (t) data.stats.push(t);
            });

            // Spans and divs with short prominent text (likely slogans/stats)
            document.querySelectorAll('span, div').forEach(el => {
                if (el.children.length === 0) {
                    const t = cleanText(getTextContent(el));
                    if (t && t.length > 3 && t.length < 200) {
                        // Only include if it has meaningful content
                        const style = window.getComputedStyle(el);
                        const fontSize = parseFloat(style.fontSize);
                        if (fontSize >= 20) {
                            data.raw_body_text.push({ text: t, fontSize: style.fontSize, tag: el.tagName });
                        }
                    }
                }
            });

            // Section-level extraction: walk top-level sections/main children
            const sectionEls = document.querySelectorAll('section, main > div, article');
            sectionEls.forEach((sec, i) => {
                const heading = sec.querySelector('h1, h2, h3, h4');
                const headingText = heading ? cleanText(getTextContent(heading)) : null;
                const fullText = cleanText(getTextContent(sec));
                if (fullText && fullText.length > 5) {
                    data.sections.push({
                        index: i,
                        heading: headingText,
                        full_text: fullText.substring(0, 2000)
                    });
                }
            });

            return data;
        }""")

        browser.close()
        return result

data = extract_all_text('https://www.joejuice.com')

print("\n=== PAGE TITLE ===")
print(data['title'])

print("\n=== NAVIGATION ===")
for item in dict.fromkeys(data['nav']):  # deduplicate
    print(f"  - {item}")

print("\n=== ALL HEADINGS ===")
for h in data['all_headings']:
    print(f"  [{h['tag']}] {h['text']}")

print("\n=== ALL PARAGRAPHS ===")
for p in dict.fromkeys(data['all_paragraphs']):
    print(f"  - {p}")

print("\n=== BUTTONS ===")
for b in dict.fromkeys(data['buttons']):
    print(f"  - {b}")

print("\n=== STATS / LARGE TEXT ELEMENTS ===")
for s in data['stats']:
    print(f"  - {s}")

print("\n=== PROMINENT TEXT (font >= 20px) ===")
seen = set()
for item in data['raw_body_text']:
    t = item['text']
    if t not in seen:
        seen.add(t)
        print(f"  [{item['fontSize']}] {t}")

print("\n=== SECTIONS (structured) ===")
for sec in data['sections']:
    print(f"\n  --- Section {sec['index']} ---")
    if sec['heading']:
        print(f"  Heading: {sec['heading']}")
    print(f"  Text: {sec['full_text'][:500]}")

print("\n=== ALL LINK TEXT (unique) ===")
for link in dict.fromkeys(data['all_links']):
    print(f"  - {link}")

# Save full JSON
with open('/Users/moons/dev/theacaiclub/web/screenshots/joejuice_text_data.json', 'w') as f:
    json.dump(data, f, indent=2)
print("\n\nFull JSON saved to screenshots/joejuice_text_data.json")
