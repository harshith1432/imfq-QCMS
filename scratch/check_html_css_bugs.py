import re

with open('frontend/admin/super-admin.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Check style tags count
style_open = len(re.findall(r'<style', content, re.I))
style_close = len(re.findall(r'</style>', content, re.I))
print(f"Style open tags: {style_open}, Close tags: {style_close}")

# Find all style blocks and check curly braces balance
style_blocks = re.findall(r'<style[^>]*>(.*?)</style>', content, re.DOTALL | re.I)
for i, block in enumerate(style_blocks):
    open_braces = block.count('{')
    close_braces = block.count('}')
    if open_braces != close_braces:
        print(f"Style block {i+1} has mismatched braces! Open: {open_braces}, Close: {close_braces}")
    else:
        print(f"Style block {i+1} braces balanced: {open_braces}")
