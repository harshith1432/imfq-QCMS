import re

with open('frontend/admin/super-admin.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Check total div open vs close tags
div_open = len(re.findall(r'<div\b', content, re.I))
div_close = len(re.findall(r'</div>', content, re.I))

print(f"Total <div open: {div_open}, </div> close: {div_close}")
if div_open != div_close:
    print(f"MISMATCH! Difference: {div_open - div_close}")
