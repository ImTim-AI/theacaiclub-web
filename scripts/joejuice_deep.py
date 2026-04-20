from playwright.sync_api import sync_playwright
import json

url = 'https://www.joejuice.com'

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={'width': 1920, 'height': 1080})
    page.goto(url, wait_until='networkidle')

    # Try to dismiss cookie banner
    try:
        page.click('button:has-text("ACCEPT")', timeout=3000)
    except:
        pass
    try:
        page.click('button:has-text("Accept")', timeout=3000)
    except:
        pass
    try:
        page.click('button:has-text("ALLOW ALL")', timeout=3000)
    except:
        pass

    page.wait_for_timeout(1000)

    # Take a fresh screenshot after dismissal
    page.screenshot(path='/Users/moons/dev/theacaiclub/web/screenshots/joejuice_desktop_nocookie.png', full_page=False)

    # Also take full page
    page.screenshot(path='/Users/moons/dev/theacaiclub/web/screenshots/joejuice_desktop_full.png', full_page=True)

    data = page.evaluate("""() => {
        function styleOf(el, label) {
            if (!el) return { label, error: 'not found' };
            const cs = window.getComputedStyle(el);
            return {
                label,
                tag: el.tagName,
                className: el.className?.slice(0, 120),
                text: el.innerText?.slice(0, 100),
                fontSize: cs.fontSize,
                fontWeight: cs.fontWeight,
                letterSpacing: cs.letterSpacing,
                lineHeight: cs.lineHeight,
                fontFamily: cs.fontFamily,
                textTransform: cs.textTransform,
                color: cs.color,
                background: cs.background?.slice(0, 200),
                backgroundColor: cs.backgroundColor,
                backgroundImage: cs.backgroundImage?.slice(0, 300),
                position: cs.position,
                zIndex: cs.zIndex,
                opacity: cs.opacity,
            };
        }

        // All sections on page
        const sections = Array.from(document.querySelectorAll('section')).map((el, i) => {
            const cs = window.getComputedStyle(el);
            const firstH = el.querySelector('h1,h2,h3,h4');
            return {
                index: i,
                className: el.className?.slice(0, 120),
                backgroundColor: cs.backgroundColor,
                backgroundImage: cs.backgroundImage?.slice(0, 200),
                firstHeadingText: firstH?.innerText?.slice(0, 80),
                firstHeadingTag: firstH?.tagName,
            };
        });

        // Nav
        const nav = document.querySelector('nav, header');
        let navInfo = null;
        let navLinks = [];
        if (nav) {
            const cs = window.getComputedStyle(nav);
            navInfo = {
                tag: nav.tagName,
                className: nav.className?.slice(0, 120),
                backgroundColor: cs.backgroundColor,
                position: cs.position,
            };
            navLinks = Array.from(nav.querySelectorAll('a')).slice(0, 6).map(a => {
                const cs = window.getComputedStyle(a);
                return {
                    text: a.innerText?.slice(0, 40),
                    fontSize: cs.fontSize,
                    fontWeight: cs.fontWeight,
                    letterSpacing: cs.letterSpacing,
                    fontFamily: cs.fontFamily,
                    textTransform: cs.textTransform,
                    color: cs.color,
                };
            });
        }

        // All h1s
        const h1s = Array.from(document.querySelectorAll('h1')).map((el, i) => {
            const cs = window.getComputedStyle(el);
            return {
                index: i,
                text: el.innerText?.slice(0, 80),
                fontSize: cs.fontSize,
                fontWeight: cs.fontWeight,
                letterSpacing: cs.letterSpacing,
                lineHeight: cs.lineHeight,
                fontFamily: cs.fontFamily,
                textTransform: cs.textTransform,
                color: cs.color,
            };
        });

        // All h2s visible (not in cookie modal)
        const h2s = Array.from(document.querySelectorAll('h2')).filter(el => {
            // skip if inside dialog/modal
            return !el.closest('[role="dialog"], [class*="cookie"], [class*="Cookie"], [class*="modal"]');
        }).slice(0, 6).map((el, i) => {
            const cs = window.getComputedStyle(el);
            return {
                index: i,
                text: el.innerText?.slice(0, 80),
                fontSize: cs.fontSize,
                fontWeight: cs.fontWeight,
                letterSpacing: cs.letterSpacing,
                lineHeight: cs.lineHeight,
                fontFamily: cs.fontFamily,
                textTransform: cs.textTransform,
                color: cs.color,
            };
        });

        // All h3s
        const h3s = Array.from(document.querySelectorAll('h3')).slice(0, 4).map((el, i) => {
            const cs = window.getComputedStyle(el);
            return {
                index: i,
                text: el.innerText?.slice(0, 60),
                fontSize: cs.fontSize,
                fontWeight: cs.fontWeight,
                letterSpacing: cs.letterSpacing,
                lineHeight: cs.lineHeight,
                fontFamily: cs.fontFamily,
                textTransform: cs.textTransform,
                color: cs.color,
            };
        });

        // Small label / eyebrow text — look for small uppercase text
        const allSmall = Array.from(document.querySelectorAll('span, p, div')).filter(el => {
            const cs = window.getComputedStyle(el);
            const fs = parseFloat(cs.fontSize);
            const tt = cs.textTransform;
            const ls = cs.letterSpacing;
            const fw = cs.fontWeight;
            return fs <= 14 && fs >= 10 && (tt === 'uppercase' || parseFloat(ls) > 0.5) && el.innerText?.trim().length > 2;
        }).slice(0, 8).map(el => {
            const cs = window.getComputedStyle(el);
            return {
                tag: el.tagName,
                text: el.innerText?.slice(0, 60),
                fontSize: cs.fontSize,
                fontWeight: cs.fontWeight,
                letterSpacing: cs.letterSpacing,
                fontFamily: cs.fontFamily,
                textTransform: cs.textTransform,
                color: cs.color,
            };
        });

        // Hero section — deep dive
        // The hero is likely the first big section. Let's grab image elements too
        const heroImages = Array.from(document.querySelectorAll('img')).slice(0, 3).map(img => ({
            src: img.src?.slice(0, 100),
            alt: img.alt,
            width: img.width,
            height: img.height,
        }));

        // Look for any element with a linear-gradient background
        const gradientEls = Array.from(document.querySelectorAll('*')).filter(el => {
            const cs = window.getComputedStyle(el);
            return cs.backgroundImage?.includes('linear-gradient') || cs.background?.includes('linear-gradient');
        }).slice(0, 10).map(el => {
            const cs = window.getComputedStyle(el);
            return {
                tag: el.tagName,
                className: el.className?.slice(0, 100),
                backgroundImage: cs.backgroundImage?.slice(0, 300),
                background: cs.background?.slice(0, 300),
                position: cs.position,
                zIndex: cs.zIndex,
            };
        });

        // Look for elements with rgba black backgrounds (overlays)
        const rgbaEls = Array.from(document.querySelectorAll('*')).filter(el => {
            const cs = window.getComputedStyle(el);
            return cs.backgroundColor?.includes('rgba') && cs.backgroundColor !== 'rgba(0, 0, 0, 0)';
        }).slice(0, 10).map(el => {
            const cs = window.getComputedStyle(el);
            return {
                tag: el.tagName,
                className: el.className?.slice(0, 100),
                backgroundColor: cs.backgroundColor,
                position: cs.position,
                zIndex: cs.zIndex,
                width: cs.width,
                height: cs.height,
            };
        });

        // Buttons
        const buttons = Array.from(document.querySelectorAll('button, a[class*="btn"], a[class*="cta"]')).filter(el => {
            return !el.closest('[role="dialog"], [class*="cookie"]');
        }).slice(0, 5).map(el => {
            const cs = window.getComputedStyle(el);
            return {
                tag: el.tagName,
                text: el.innerText?.slice(0, 50),
                fontSize: cs.fontSize,
                fontWeight: cs.fontWeight,
                letterSpacing: cs.letterSpacing,
                fontFamily: cs.fontFamily,
                textTransform: cs.textTransform,
                color: cs.color,
                backgroundColor: cs.backgroundColor,
                border: cs.border,
                padding: cs.padding,
            };
        });

        return { sections, navInfo, navLinks, h1s, h2s, h3s, allSmall, heroImages, gradientEls, rgbaEls, buttons };
    }""")

    print(json.dumps(data, indent=2))
    browser.close()
