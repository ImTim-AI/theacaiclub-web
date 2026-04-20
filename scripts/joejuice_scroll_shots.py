from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(
        viewport={'width': 1920, 'height': 1080},
        user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    )
    page = context.new_page()
    page.goto('https://www.joejuice.com', wait_until='networkidle', timeout=60000)

    # Dismiss cookie banner
    try:
        page.click('button:has-text("Accept")', timeout=4000)
        page.wait_for_timeout(1500)
    except:
        pass

    page.wait_for_timeout(2000)

    # Scroll to products section
    page.evaluate("window.scrollTo(0, 1200)")
    page.wait_for_timeout(800)
    page.screenshot(path='/Users/moons/dev/theacaiclub/web/screenshots/joejuice_scroll_products.png', full_page=False)

    # Scroll to app section
    page.evaluate("window.scrollTo(0, 600)")
    page.wait_for_timeout(800)
    page.screenshot(path='/Users/moons/dev/theacaiclub/web/screenshots/joejuice_scroll_app.png', full_page=False)

    # Try to extract product names from the carousel
    # The product name <p> elements appear to be empty in the DOM - check via data attributes or image filenames
    product_data = page.evaluate("""() => {
        const products = [];
        // Check all background-image divs in the products section
        const productSection = document.querySelector('[aria-label="Most popular products"]');
        if (productSection) {
            const slides = productSection.querySelectorAll('[role="tabpanel"]');
            slides.forEach((slide, i) => {
                const nameEl = slide.querySelector('p[role="heading"]');
                const name = nameEl ? (nameEl.innerText || '').trim() : '';

                // Get image URL
                const imgDiv = slide.querySelector('[style*="background-image"]');
                const style = imgDiv ? imgDiv.getAttribute('style') : '';
                const urlMatch = style.match(/url\\(["\']?([^"'\\)]+)["\']?\\)/);
                const url = urlMatch ? urlMatch[1] : '';

                // Extract filename from URL as fallback name
                const filename = url ? url.split('/').pop().split('?')[0].split('.')[0] : '';

                products.push({
                    index: i + 1,
                    name: name || '(empty)',
                    filename: filename,
                    imageUrl: url.substring(0, 100)
                });
            });
        }
        return products;
    }""")

    # Also check if there's a hero subtitle/tagline hidden somewhere
    hero_data = page.evaluate("""() => {
        // Check for the "with" handwriting text / subtitle
        const allText = [];
        document.querySelectorAll('*').forEach(el => {
            if (el.children.length === 0) {
                const t = (el.innerText || el.textContent || '').trim();
                if (t && t.toLowerCase().includes('with') && t.length < 100) {
                    const style = window.getComputedStyle(el);
                    allText.push({text: t, tag: el.tagName, class: el.className.toString().substring(0, 60)});
                }
            }
        });

        // Check data attributes for hidden text
        const heroEl = document.querySelector('section:first-of-type, [class*="hero"], [class*="landing"]');
        const heroData = {};
        if (heroEl) {
            const dataset = {};
            for (const key of Object.keys(heroEl.dataset)) {
                dataset[key] = heroEl.dataset[key];
            }
            heroData.dataset = dataset;
            heroData.outerHTML = heroEl.outerHTML.substring(0, 2000);
        }

        return { withText: allText, heroData };
    }""")

    browser.close()

print("=== PRODUCT CAROUSEL DATA ===")
for prod in product_data:
    print(f"  Slide {prod['index']}: name='{prod['name']}' | filename='{prod['filename']}' | url=...{prod['imageUrl'][-50:]}")

print("\n=== 'WITH' TEXT ELEMENTS ===")
for item in hero_data['withText']:
    print(f"  <{item['tag']} class='{item['class']}'> {item['text']}")

print("\n=== HERO ELEMENT HTML ===")
if hero_data['heroData']:
    print(hero_data['heroData'].get('outerHTML', 'none'))
