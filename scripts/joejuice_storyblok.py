import urllib.request
import json

# Fetch the full homepage story from Storyblok
url = 'https://api.storyblok.com/v2/cdn/stories/custompages/homepage?version=draft&token=HFLIl3f6QuUdJuzxAYKTCgtt'

req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req) as resp:
    data = json.loads(resp.read().decode())

story = data['story']
content = story['content']

print(f"Story: {story['name']}")
print(f"Published: {story['published_at']}")
print()

def extract_text_from_block(block, depth=0):
    indent = "  " * depth
    component = block.get('component', 'unknown')
    print(f"{indent}[{component}]")

    # Common text fields
    for field in ['title', 'subtitle', 'description', 'text', 'label', 'heading', 'subheading',
                  'body', 'copy', 'cta_label', 'cta_text', 'button_label', 'buttonLabel',
                  'buttonCTAlabel', 'inputLabel', 'inputPlaceholder', 'stat', 'number',
                  'name', 'tagline', 'eyebrow', 'headline', 'subtext', 'caption']:
        if field in block and block[field]:
            val = block[field]
            if isinstance(val, str) and val.strip():
                print(f"{indent}  {field}: {val}")
            elif isinstance(val, dict) and 'content' in val:
                # Richtext field
                rt = extract_richtext(val)
                if rt:
                    print(f"{indent}  {field} (richtext): {rt}")

    # Recurse into arrays
    for key, val in block.items():
        if isinstance(val, list) and val and isinstance(val[0], dict) and 'component' in val[0]:
            print(f"{indent}  -> {key}:")
            for sub_block in val:
                extract_text_from_block(sub_block, depth + 2)

def extract_richtext(rt_node):
    """Recursively extract text from Storyblok richtext"""
    if isinstance(rt_node, str):
        return rt_node
    if isinstance(rt_node, dict):
        if rt_node.get('type') == 'text':
            return rt_node.get('text', '')
        texts = []
        for child in rt_node.get('content', []):
            t = extract_richtext(child)
            if t:
                texts.append(t)
        return ' '.join(texts)
    return ''

print("=== HOMEPAGE BODY BLOCKS ===\n")
for block in content.get('body', []):
    extract_text_from_block(block)
    print()

# Also dump the raw JSON for inspection
with open('/Users/moons/dev/theacaiclub/web/screenshots/joejuice_storyblok.json', 'w') as f:
    json.dump(data, f, indent=2)
print("\n\nFull Storyblok JSON saved.")
