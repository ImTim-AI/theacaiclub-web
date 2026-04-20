from playwright.sync_api import sync_playwright

def extract_deep(url):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        page = context.new_page()
        page.goto(url, wait_until='networkidle', timeout=60000)

        # Dismiss cookie banner
        try:
            page.click('button:has-text("Accept")', timeout=4000)
            page.wait_for_timeout(1500)
        except:
            pass
        try:
            page.click('button:has-text("Only Required")', timeout=2000)
            page.wait_for_timeout(1000)
        except:
            pass

        page.wait_for_timeout(2000)

        # Scroll through page to trigger lazy loading
        page.evaluate("window.scrollTo(0, document.body.scrollHeight / 4)")
        page.wait_for_timeout(800)
        page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
        page.wait_for_timeout(800)
        page.evaluate("window.scrollTo(0, document.body.scrollHeight * 3 / 4)")
        page.wait_for_timeout(800)
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(1000)
        page.evaluate("window.scrollTo(0, 0)")
        page.wait_for_timeout(500)

        # Full page screenshot after scrolling
        page.screenshot(
            path='/Users/moons/dev/theacaiclub/web/screenshots/joejuice_fullpage.png',
            full_page=True
        )

        # Get ALL text nodes with context
        result = page.evaluate("""() => {
            function cleanText(t) {
                return t.replace(/\\s+/g, ' ').trim();
            }

            // Get every text-bearing element with its computed font size and tag
            const items = [];
            const walker = document.createTreeWalker(
                document.body,
                NodeFilter.SHOW_TEXT,
                null,
                false
            );

            let node;
            while (node = walker.nextNode()) {
                const text = cleanText(node.textContent);
                if (!text || text.length < 2) continue;

                const parent = node.parentElement;
                if (!parent) continue;

                // Skip script/style content
                const tag = parent.tagName;
                if (['SCRIPT', 'STYLE', 'NOSCRIPT'].includes(tag)) continue;

                const style = window.getComputedStyle(parent);

                // Skip hidden elements
                if (style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0') continue;

                const fontSize = parseFloat(style.fontSize);
                const fontWeight = style.fontWeight;

                items.push({
                    text,
                    tag,
                    fontSize,
                    fontWeight,
                    className: parent.className ? parent.className.toString().substring(0, 80) : ''
                });
            }

            return items;
        }""")

        # Also get product names specifically
        products = page.evaluate("""() => {
            const prods = [];
            // Look for product cards
            document.querySelectorAll('[class*="product"], [class*="item"], [class*="card"]').forEach(el => {
                const heading = el.querySelector('h1,h2,h3,h4,h5,span[class*="name"],span[class*="title"],p[class*="name"]');
                if (heading) {
                    const t = (heading.innerText || '').trim();
                    if (t) prods.push(t);
                }
            });
            return prods;
        }""")

        # Get hero section specifically
        hero = page.evaluate("""() => {
            // Try various hero selectors
            const heroSelectors = [
                '[class*="hero"]',
                '[class*="banner"]',
                '[class*="landing"]',
                'main > section:first-child',
                'main > div:first-child',
                '#hero',
                '.hero'
            ];

            for (const sel of heroSelectors) {
                const el = document.querySelector(sel);
                if (el) {
                    return {
                        selector: sel,
                        text: (el.innerText || el.textContent || '').replace(/\\s+/g, ' ').trim().substring(0, 500),
                        html: el.innerHTML.substring(0, 1000)
                    };
                }
            }
            return null;
        }""")

        browser.close()
        return result, products, hero

items, products, hero = extract_deep('https://www.joejuice.com')

print("=== HERO SECTION ===")
if hero:
    print(f"Selector: {hero['selector']}")
    print(f"Text: {hero['text']}")
else:
    print("No hero found with standard selectors")

print("\n=== PRODUCT NAMES ===")
seen = set()
for p in products:
    if p not in seen:
        seen.add(p)
        print(f"  - {p}")

print("\n=== ALL TEXT BY FONT SIZE (sorted largest first, no duplicates) ===")
# Group by text, keep largest font
text_map = {}
for item in items:
    t = item['text']
    if t not in text_map or item['fontSize'] > text_map[t]['fontSize']:
        text_map[t] = item

sorted_items = sorted(text_map.values(), key=lambda x: -x['fontSize'])

print("\n-- Large / Headline text (>= 24px) --")
for item in sorted_items:
    if item['fontSize'] >= 24:
        print(f"  [{item['fontSize']}px {item['fontWeight']}w] <{item['tag']}> {item['text']}")

print("\n-- Medium text (16px-23px) --")
for item in sorted_items:
    if 16 <= item['fontSize'] < 24:
        print(f"  [{item['fontSize']}px] <{item['tag']}> {item['text']}")

print("\n-- Smaller text (< 16px) --")
for item in sorted_items:
    if item['fontSize'] < 16:
        print(f"  [{item['fontSize']}px] <{item['tag']}> {item['text']}")
