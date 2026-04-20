from playwright.sync_api import sync_playwright

def capture(url, output_path, viewport_width=1920, viewport_height=1080):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={'width': viewport_width, 'height': viewport_height})
        page.goto(url, wait_until='networkidle')
        page.screenshot(path=output_path, full_page=False)
        browser.close()

viewports = [
    ('desktop', 1920, 1080),
    ('laptop', 1366, 768),
    ('tablet', 768, 1024),
    ('mobile', 375, 812),
]

url = 'https://www.joejuice.com'

for name, w, h in viewports:
    out = f'/Users/moons/dev/theacaiclub/web/screenshots/joejuice_{name}.png'
    print(f'Capturing {name} ({w}x{h}) -> {out}')
    capture(url, out, w, h)
    print(f'  Done.')
