from playwright.sync_api import sync_playwright

def extract_products(url):
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

        page.wait_for_timeout(2000)

        # Scroll through to trigger lazy loading
        page.evaluate("window.scrollTo(0, 500)")
        page.wait_for_timeout(800)
        page.evaluate("window.scrollTo(0, 1000)")
        page.wait_for_timeout(800)

        # Screenshot hero area (top part)
        page.evaluate("window.scrollTo(0, 0)")
        page.wait_for_timeout(500)
        page.screenshot(
            path='/Users/moons/dev/theacaiclub/web/screenshots/joejuice_hero.png',
            full_page=False
        )

        # Screenshot products section
        page.evaluate("window.scrollTo(0, 800)")
        page.wait_for_timeout(500)
        page.screenshot(
            path='/Users/moons/dev/theacaiclub/web/screenshots/joejuice_products.png',
            full_page=False
        )

        # Get all alt text from images (product names often here)
        alts = page.evaluate("""() => {
            const imgs = [];
            document.querySelectorAll('img').forEach(img => {
                if (img.alt && img.alt.trim()) {
                    imgs.push({alt: img.alt.trim(), src: img.src.substring(0, 100)});
                }
            });
            return imgs;
        }""")

        # Get all aria-labels
        aria = page.evaluate("""() => {
            const items = [];
            document.querySelectorAll('[aria-label]').forEach(el => {
                const t = el.getAttribute('aria-label').trim();
                if (t) items.push({label: t, tag: el.tagName});
            });
            return items;
        }""")

        # Dig into the products section HTML
        products_html = page.evaluate("""() => {
            // Find the Most popular products section
            const all_h2 = Array.from(document.querySelectorAll('h2'));
            const prodHeading = all_h2.find(h => h.textContent.includes('popular'));
            if (prodHeading) {
                const section = prodHeading.closest('section') || prodHeading.parentElement.parentElement;
                return section ? section.innerHTML.substring(0, 5000) : 'no section found';
            }
            return 'no heading found';
        }""")

        # Get ALL text including from shadow DOM and more
        all_inner_text = page.inner_text('body')

        browser.close()
        return alts, aria, products_html, all_inner_text

alts, aria, products_html, all_body_text = extract_products('https://www.joejuice.com')

print("=== IMAGE ALT TEXTS ===")
for img in alts:
    print(f"  alt='{img['alt']}'")

print("\n=== ARIA LABELS ===")
seen_aria = set()
for item in aria:
    t = item['label']
    if t not in seen_aria and len(t) < 200:
        seen_aria.add(t)
        print(f"  [{item['tag']}] {t}")

print("\n=== PRODUCTS SECTION HTML (truncated) ===")
print(products_html[:3000])

print("\n\n=== FULL BODY innerText ===")
# Clean and print
lines = [l.strip() for l in all_body_text.split('\n') if l.strip()]
seen = set()
for line in lines:
    if line not in seen and len(line) > 1:
        seen.add(line)
        print(f"  {line}")
