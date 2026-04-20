from playwright.sync_api import sync_playwright
import json

url = 'https://www.joejuice.com'

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={'width': 1920, 'height': 1080})
    page.goto(url, wait_until='networkidle')

    styles = page.evaluate("""() => {
        function getStyles(selector, label) {
            const el = document.querySelector(selector);
            if (!el) return { label, error: 'not found' };
            const cs = window.getComputedStyle(el);
            return {
                label,
                selector,
                text: el.innerText?.slice(0, 80),
                fontSize: cs.fontSize,
                fontWeight: cs.fontWeight,
                letterSpacing: cs.letterSpacing,
                lineHeight: cs.lineHeight,
                fontFamily: cs.fontFamily,
                textTransform: cs.textTransform,
                color: cs.color,
                tagName: el.tagName,
            };
        }

        // Try several selectors for hero headline
        const heroSelectors = [
            'h1', '.hero h1', '[class*="hero"] h1', '[class*="Hero"] h1',
            'section:first-of-type h1', 'header h1',
        ];
        let hero = null;
        for (const s of heroSelectors) {
            const el = document.querySelector(s);
            if (el) { hero = getStyles(s, 'hero h1'); break; }
        }

        // h2 headings
        const h2s = Array.from(document.querySelectorAll('h2')).slice(0, 4).map((el, i) => {
            const cs = window.getComputedStyle(el);
            return {
                label: `h2[${i}]`,
                text: el.innerText?.slice(0, 60),
                fontSize: cs.fontSize,
                fontWeight: cs.fontWeight,
                letterSpacing: cs.letterSpacing,
                lineHeight: cs.lineHeight,
                fontFamily: cs.fontFamily,
                textTransform: cs.textTransform,
            };
        });

        // nav links
        const navLink = getStyles('nav a, header nav a, [class*="nav"] a', 'nav link');

        // body paragraph
        const bodyP = getStyles('p, main p, article p', 'body p');

        // buttons
        const btn = getStyles('button, a[class*="btn"], a[class*="button"], [class*="Button"]', 'button');

        // eyebrow / label text — small caps / overline style
        const eyebrowSelectors = [
            '[class*="eyebrow"]', '[class*="label"]', '[class*="overline"]',
            '[class*="tag"]', '[class*="category"]', '[class*="kicker"]',
            'span[class*="small"]', 'p[class*="small"]',
        ];
        let eyebrow = null;
        for (const s of eyebrowSelectors) {
            const el = document.querySelector(s);
            if (el) { eyebrow = getStyles(s, 'eyebrow/label'); break; }
        }

        // overlay analysis — look for pseudo-element or overlay divs
        const overlaySelectors = [
            '[class*="overlay"]', '[class*="Overlay"]',
            '[class*="hero"] [class*="bg"]', '[class*="hero-bg"]',
            '[class*="hero"] > div:first-child',
        ];
        let overlayInfo = [];
        for (const s of overlaySelectors) {
            const el = document.querySelector(s);
            if (el) {
                const cs = window.getComputedStyle(el);
                overlayInfo.push({
                    selector: s,
                    background: cs.background,
                    backgroundColor: cs.backgroundColor,
                    backgroundImage: cs.backgroundImage,
                    opacity: cs.opacity,
                    position: cs.position,
                    width: cs.width,
                    height: cs.height,
                    zIndex: cs.zIndex,
                });
            }
        }

        // Also check hero section itself
        const heroSection = document.querySelector('section, [class*="hero"], [class*="Hero"]');
        let heroSectionInfo = null;
        if (heroSection) {
            const cs = window.getComputedStyle(heroSection);
            heroSectionInfo = {
                tagName: heroSection.tagName,
                className: heroSection.className?.slice(0, 100),
                background: cs.background,
                backgroundColor: cs.backgroundColor,
                backgroundImage: cs.backgroundImage?.slice(0, 200),
            };
        }

        // Get first few elements inside the hero for deeper inspection
        const heroEl = document.querySelector('[class*="hero"], [class*="Hero"], section');
        let heroChildren = [];
        if (heroEl) {
            heroChildren = Array.from(heroEl.querySelectorAll('*')).slice(0, 15).map(el => {
                const cs = window.getComputedStyle(el);
                return {
                    tag: el.tagName,
                    class: el.className?.slice(0, 80),
                    backgroundColor: cs.backgroundColor,
                    backgroundImage: cs.backgroundImage?.slice(0, 150),
                    opacity: cs.opacity,
                    position: cs.position,
                    zIndex: cs.zIndex,
                };
            });
        }

        return { hero, h2s, navLink, bodyP, btn, eyebrow, overlayInfo, heroSectionInfo, heroChildren };
    }""")

    print(json.dumps(styles, indent=2))
    browser.close()
