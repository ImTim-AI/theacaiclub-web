from playwright.sync_api import sync_playwright
import json

# Intercept network requests to capture product API data
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(
        viewport={'width': 1920, 'height': 1080},
        user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    )

    api_responses = []

    def handle_response(response):
        url = response.url
        if any(x in url for x in ['storyblok', 'api', 'product', 'menu', 'popular']):
            try:
                body = response.json()
                api_responses.append({'url': url[:150], 'data': body})
            except:
                pass

    page = context.new_page()
    page.on('response', handle_response)

    page.goto('https://www.joejuice.com', wait_until='networkidle', timeout=60000)

    # Dismiss cookie
    try:
        page.click('button:has-text("Accept")', timeout=4000)
        page.wait_for_timeout(1500)
    except:
        pass

    page.wait_for_timeout(3000)
    browser.close()

print(f"Captured {len(api_responses)} API responses\n")
for resp in api_responses:
    print(f"URL: {resp['url']}")
    # Print a snippet of the data
    data_str = json.dumps(resp['data'])[:1000]
    print(f"Data: {data_str}")
    print("---")
